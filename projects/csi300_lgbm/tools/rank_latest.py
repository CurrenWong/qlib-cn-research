"""最终选股：用选定超参在"标签已知"的全部数据上重训 → 预测最新交易日 → top10 + 理由。

诚实边界（写进报告）：
- 最终模型用到了 2023-2026 的历史标签（现在都已是过去数据），报告里的**回测**才是样本外证据；
- 模型输出是"未来 5 日收益的回归估计"，不是目标价，更不是保证；
- top10 是**观察名单**，不是买入指令（测试期组合层面没跑赢等权池）。
"""

import json
import sys
import time
import urllib.request

import lightgbm as lgb
import numpy as np
import pandas as pd

import model_core as mc

TENCENT = "https://qt.gtimg.cn/q="


def log(*a):
    print(*a, flush=True)


def fetch_names(symbols):
    """腾讯行情接口取中文名（失败就返回空，不影响主流程）。返回 {SH600000: '浦发银行'}。"""
    out = {}
    qs = ",".join(("sh" if s.startswith("SH") else "sz") + s[2:] for s in symbols)
    try:
        req = urllib.request.Request(TENCENT + qs, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=20).read().decode("gbk", errors="replace")
        for line in raw.strip().split("\n"):
            if "=" not in line:
                continue
            body = line.split("=", 1)[1].strip().strip('";')
            parts = body.split("~")
            if len(parts) > 3:
                key = parts[2]                       # 6 位数字代码
                for s in symbols:                   # 映射回 SH/SZ 全称
                    if s[2:] == key:
                        out[s] = parts[1]
                        break
    except Exception as e:                                   # noqa: BLE001
        log(f"  名称接口失败（不影响主流程）: {e}")
    return out


def topk_forward_stats(ctx, oos, period, K=10, freq=20):
    """样本外"直接看排名"的统计：每 20 个交易日取 top-K，看未来 5 日收益 vs 池内均值。"""
    start, end = period
    o = oos[(oos["datetime"] >= start) & (oos["datetime"] <= end)].copy()
    dates = sorted(o["datetime"].unique())
    picks, pool, bench = [], [], []
    idx = ctx["index"]
    for i in range(0, len(dates), freq):
        d = dates[i]
        g = o[o["datetime"] == d].dropna(subset=["pred", "y"])
        if len(g) < 50:
            continue
        top = g.nlargest(K, "pred")
        picks.append(top["y"].mean())
        pool.append(g["y"].mean())
        j = idx.index.searchsorted(pd.Timestamp(d))
        if 0 <= j + 5 < len(idx):
            bench.append(idx.iloc[j + 5] / idx.iloc[j] - 1)
    picks, pool, bench = map(np.array, (picks, pool, bench))
    out = {"n_rebalances": int(len(picks)),
           "topK_mean_fwd5": float(picks.mean()),
           "pool_mean_fwd5": float(pool.mean()),
           "bench_mean_fwd5": float(bench.mean()) if len(bench) else 0.0,
           "topK_win_rate": float((picks > 0).mean()),
           "pool_win_rate": float((pool > 0).mean()),
           "excess_vs_pool": float(picks.mean() - pool.mean()),
           "excess_vs_bench": float(picks.mean() - bench.mean()) if len(bench) else 0.0}
    return out


def main():
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    t0 = time.time()
    ctx = mc.load_all()
    cfg = json.loads((mc.RESULTS / "config.json").read_text(encoding="utf-8"))
    hp = cfg["model_hp"]
    dates = ctx["dates"]
    y = ctx["y"]
    rd = ctx["rows_date"]

    # --- 最后有标签的样本日 & 最新交易日 ---
    lab_known = ~np.isnan(y)
    last_lab_date_idx = int(rd[lab_known].max())
    last_idx = len(dates) - 1
    log(f"最新交易日 {dates[last_idx].date()}；最后一个标签已知样本日 {dates[last_lab_date_idx].date()}")

    # --- 最终模型：所有标签已知的样本 ---
    tr = np.where((rd <= last_lab_date_idx) & lab_known)[0]
    inner0 = max(0, last_lab_date_idx - 120)
    va = np.where((rd >= inner0) & (rd <= last_lab_date_idx) & lab_known)[0]
    params = {"n_estimators": 800, "max_depth": -1, "lambda_l2": 1.0, "verbosity": -1,
              "seed": 42, "n_jobs": -1, "deterministic": True, "force_col_wise": True}
    params.update(hp)
    model = lgb.LGBMRegressor(**params)
    model.fit(ctx["X"][tr], y[tr], eval_set=[(ctx["X"][va], y[va])], eval_metric="l2",
              callbacks=[lgb.early_stopping(80, verbose=False)])
    log(f"最终模型训练完成：{len(tr)} 样本，best_iter={model.best_iteration_}，"
        f"耗时 {time.time()-t0:.0f}s")

    # --- 最新交易日的候选池（成分股用最近有成分数据的日期） ---
    mask = ctx["mask"]
    last_member_idx = int(np.max([i for i in range(len(dates)) if mask[i].any()]))
    pool_idx = np.where(mask[last_member_idx])[0]
    log(f"成分池日期 {dates[last_member_idx].date()}，{len(pool_idx)} 只；"
        f"预测日 {dates[last_idx].date()}")

    rows = np.where(rd == last_idx)[0]
    rows = rows[np.isin(ctx["rows_sym"][rows], pool_idx)]
    Xf = ctx["X"][rows]
    pred = model.predict(Xf)
    contrib = model.predict(Xf, pred_contrib=True)     # (n, n_feat+1)

    syms = [ctx["symbols"][s] for s in ctx["rows_sym"][rows]]
    df = pd.DataFrame({"symbol": syms, "pred": pred})
    df["rank"] = df["pred"].rank(ascending=False).astype(int)
    df["pct"] = (df["pred"].rank(pct=True) * 100).round(1)
    df = df.sort_values("pred", ascending=False).reset_index(drop=True)

    # --- 理由：SHAP 贡献 top3 + 可读化指标 ---
    close = ctx["close"]
    i_last = last_idx
    ctxm = ctx["mats"]
    names = fetch_names(df["symbol"].head(K).tolist())
    feat_cn = {
        "mom_1": "1日涨跌", "mom_5": "5日动量", "mom_10": "10日动量", "mom_20": "20日动量",
        "mom_60": "60日动量", "mom_120": "120日动量", "mom_5_ex": "5日动量(剔除末日)",
        "mom_20_ex": "20日动量(剔除末日)", "rev_3": "3日反转", "rev_10": "10日反转",
        "vol_20": "20日波动率", "vol_60": "60日波动率", "vol_ratio": "波动率变化(20/60)",
        "hl_range_20": "20日振幅", "ma_dist_5": "距5日均线", "ma_dist_20": "距20日均线",
        "ma_slope_20": "20日均线斜率", "ma_dist_60": "距60日均线", "ma_slope_60": "60日均线斜率",
        "ma_dist_120": "距120日均线", "ma_cross_5_20": "5日/20日均线差",
        "rsi_14": "RSI(14)", "price_pos_250": "250日价格位置", "dd_60": "距60日高点",
        "vol_ratio_5_20": "量能比(5/20)", "vol_z_20": "量能Z值", "liq_change": "流动性变化",
        "beta_60": "60日Beta", "alpha_20": "20日超额收益", "rel_str_60": "60日相对强度",
    }

    def col(mat, s):
        return float(mat[i_last, ctx["symbols"].index(s)])

    picks = []
    topk_df = df.head(K)
    raw = {f: ctxm[f] for f in mc.FEATURES}
    sym_arr = np.array([ctx["symbols"][x] for x in ctx["rows_sym"][rows]])
    for _, r in topk_df.iterrows():
        s = r["symbol"]
        j = ctx["symbols"].index(s)
        idx_in_rows = int(np.where(sym_arr == s)[0][0])
        shap = contrib[idx_in_rows][:-1]
        order = np.argsort(-np.abs(shap))[:3]
        reasons = []
        for k in order:
            f = mc.FEATURES[k]
            val = float(raw[f][i_last, j])
            reasons.append({"feature": f, "feature_cn": feat_cn[f],
                            "value": val, "shap": float(shap[k]),
                            "dir": "正向" if shap[k] > 0 else "负向"})
        c = float(close[i_last, j])

        def ret(n):
            if i_last - n < 0:
                return None
            p0 = close[i_last - n, j]
            return float(c / p0 - 1) if np.isfinite(p0) and p0 else None

        ma20 = float(pd.Series(close[:, j]).rolling(20).mean().iloc[i_last])
        ma60 = float(pd.Series(close[:, j]).rolling(60).mean().iloc[i_last])
        vol20 = float(pd.Series(close[:, j]).pct_change().rolling(20).std().iloc[i_last])
        amount = c * float(ctx["volume"][i_last, j]) * 100     # volume 单位是手
        hi60 = float(pd.Series(close[:, j]).rolling(60).max().iloc[i_last])
        dd60 = float(c / hi60 - 1) if np.isfinite(hi60) and hi60 else None
        code = s[2:]
        if code.startswith("688"):
            board, limit = "科创板", 0.20
        elif code.startswith("300") or code.startswith("301"):
            board, limit = "创业板", 0.20
        else:
            board, limit = "主板", 0.10
        picks.append({
            "rank": int(r["rank"]), "symbol": s, "name": names.get(s, ""),
            "pred": float(r["pred"]), "pct": float(r["pct"]),
            "close_adj": c,
            "ret_5": ret(5), "ret_20": ret(20), "ret_60": ret(60),
            "ma20": ma20, "ma60": ma60, "dist_ma20": float(c / ma20 - 1) if ma20 else None,
            "dist_ma60": float(c / ma60 - 1) if ma60 else None,
            "vol20": vol20, "amount_yuan": amount, "dd_60": dd60,
            "board": board, "limit_pct": limit,
            "reasons": reasons,
        })

    # --- 样本外"排名本身"的统计 ---
    oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
    stats = {
        "test_2023_2026": topk_forward_stats(ctx, oos, (mc.TEST_START, "2026-10-30")),
        "valid_2020_2022": topk_forward_stats(ctx, oos, (mc.VALID_START, mc.VALID_END)),
    }
    log("\n样本外 top10 前瞻收益（每 20 日调仓）:")
    for k, v in stats.items():
        log(f"  {k}: top10 均值 {v['topK_mean_fwd5']*100:+.3f}%  池内 {v['pool_mean_fwd5']*100:+.3f}%  "
            f"指数 {v['bench_mean_fwd5']*100:+.3f}%  胜率 {v['topK_win_rate']*100:.1f}%  "
            f"({v['n_rebalances']} 次)")

    imp = sorted(zip(mc.FEATURES, model.feature_importances_), key=lambda x: -x[1])
    out = {
        "as_of": str(dates[last_idx].date()),
        "pool_date": str(dates[last_member_idx].date()),
        "pool_size": int(len(pool_idx)),
        "model_hp": hp,
        "n_train": int(len(tr)),
        "best_iter": int(model.best_iteration_ or 800),
        "picks": picks,
        "topk_forward_stats": stats,
        "feature_importance": [{"feature": f, "cn": feat_cn[f], "imp": int(v)} for f, v in imp],
        "caveats": [
            "模型输出是未来5日收益的回归估计，不是目标价",
            f"top{K} 是模型观察名单，不是买入指令",
            "测试期组合层面未跑赢等权池，成本是主要拖累",
        ],
    }
    fname = "picks.json" if K == 10 else f"picks_K{K}.json"
    (mc.RESULTS / fname).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    log(f"\n已写出 results/{fname}（{len(picks)} 只）")
    for p in picks:
        log(f"  {p['rank']:2d}. {p['symbol']} {p['name']:8s} pred {p['pred']*100:+6.2f}%  "
            f"{p['ret_20']*100:+6.2f}%/20日  " +
            " | ".join(f"{r['feature_cn']}({r['value']:+.3f},{r['dir']})" for r in p["reasons"]))


if __name__ == "__main__":
    main()
