"""把混合分变成完整策略：选股 → 调仓 → 成本 → 净值 → 与基线对照。

口径与本仓库其他项目一致：
  股票池   沪深300 时点成分（csi300_lgbm/data/membership.csv）
  信号     score = w_price×价量 + w_fund×基本面 + w_event×事件（缺失基本面按 0 中性填补）
  选股     池内按分数取 top-K 等权；可选行业上限（东财 BOARD_NAME，每行业最多 N 只）
  成交     信号 T 日收盘出信号 → T+1 日收盘成交（与 csi300_lgbm / jac_600418 同口径）
  成本     买入 0.05% / 卖出 0.15% / 单笔最低 5 元，账户 100 万
  不可交易 停牌不可买卖；收盘涨停买不进

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\strategy.py
产出：results\\backtest.json / results\\nav_curves.parquet / results\\backtest_yearly.csv
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
DATA = PROJ / "data"
RESULTS = PROJ / "results"
LGBM = Path(_ROOT + r"/projects/csi300_lgbm")
sys.path.insert(0, str(LGBM / "tools"))

from model_core import membership_matrix, perf_stats   # noqa: E402

TEST_START, TEST_END = "2023-01-01", "2026-10-30"
FULL_START = "2016-01-01"
RECS = {  # 收盘价矩阵等
    "close": "close", "volume": "volume", "high": "high", "low": "low",
}

COST_BUY, COST_SELL, MIN_FEE, ACCOUNT = 0.0005, 0.0015, 5.0, 1e6


# ------------------------------------------------------------------ 数据
def load_ctx():
    px = pd.read_parquet(LGBM / "data" / "features.parquet")
    px["datetime"] = pd.to_datetime(px["datetime"])
    px = px.set_index(["datetime", "symbol"]).sort_index()
    wide = px[["close", "volume", "high", "low"]].unstack("symbol")
    dates = pd.DatetimeIndex(wide.index)
    symbols = list(wide.columns.get_level_values(1).unique())
    mats = {c: wide[c].reindex(columns=symbols).astype(np.float64).to_numpy()
            for c in RECS.values()}
    mask = membership_matrix(dates, symbols)
    for i in range(1, len(dates)):
        if not mask[i].any():
            mask[i] = mask[i - 1]
    idx = pd.read_parquet(LGBM / "data" / "index_close.parquet")["close"]
    idx.index = pd.to_datetime(idx.index)
    ctx = {"dates": dates, "symbols": symbols, "mask": mask, "index": idx.reindex(dates)}
    ctx.update(mats)
    return ctx


def load_scores(ctx):
    """我的分域分数 → (T×N) 矩阵，与 ctx 对齐。"""
    need = ["datetime", "symbol", "price_score", "fund_score", "event_score", "board_name"]
    sc = pd.read_parquet(DATA / "scores.parquet", columns=need)
    sc["datetime"] = pd.to_datetime(sc["datetime"])
    d_idx = {d: i for i, d in enumerate(ctx["dates"])}
    s_idx = {s: i for i, s in enumerate(ctx["symbols"])}
    T, N = len(ctx["dates"]), len(ctx["symbols"])
    out = {}
    for c in ("price_score", "fund_score", "event_score"):
        m = np.full((T, N), np.nan)
        ri = sc["datetime"].map(d_idx).to_numpy()
        ci = sc["symbol"].map(s_idx).to_numpy()
        m[ri, ci] = sc[c].to_numpy(dtype=float)
        out[c] = m
    bm = np.full((T, N), None, dtype=object)
    bm[ri, ci] = sc["board_name"].to_numpy(dtype=object)
    out["board"] = bm
    # 每只股票的行业（取出现最多的）
    sym2board = {}
    for j, s in enumerate(ctx["symbols"]):
        col = bm[:, j]
        vals = pd.Series(col[~pd.isna(col)]).value_counts()
        if len(vals):
            sym2board[s] = vals.index[0]
    out["sym2board"] = sym2board
    return out


def make_score_matrix(ctx, sc, w_price, w_fund, w_event, impute_fund=True):
    price, fund, event = sc["price_score"], sc["fund_score"], sc["event_score"]
    n_missing = int(np.isnan(fund).sum())
    n_rows_any = int(np.isnan(price).sum())
    if impute_fund:
        fund = np.nan_to_num(fund, nan=0.0)
        event = np.nan_to_num(event, nan=0.0)
    s = w_price * price + w_fund * fund + w_event * event
    return s, {"fund_missing_cells": n_missing, "price_missing_cells": n_rows_any}


# ------------------------------------------------------------------ 选股
def select(sig_row, pool_mask, board_row, sym2board, K, ind_cap=None, weights=None):
    """按分数选 top-K；weights=None 等权，否则按分数权重（正数，裁到 [0.05, 3] 倍等权）。"""
    idx = np.where(pool_mask & np.isfinite(sig_row))[0]
    if len(idx) == 0:
        return []
    order = idx[np.argsort(-sig_row[idx], kind="stable")]
    if not ind_cap:
        return list(order[:K])
    picked, cnt = [], {}
    for j in order:
        b = board_row[j]
        if b is None or (isinstance(b, float) and np.isnan(b)):
            picked.append(j)
            continue
        if cnt.get(b, 0) >= ind_cap:
            continue
        cnt[b] = cnt.get(b, 0) + 1
        picked.append(j)
        if len(picked) >= K:
            break
    return picked


def pick_weights(sig_row, picks, mode):
    """等权 or 分数加权（分数转正后归一，裁到不超过 3 倍等权，避免单票主导）。"""
    n = len(picks)
    if mode == "equal" or n == 0:
        return {j: 1.0 / n for j in picks}
    v = np.array([max(sig_row[j], 0.0) + 0.05 for j in picks])
    v = np.clip(v / v.mean(), 0.2, 3.0)
    v = v / v.sum()
    return {j: float(v[i]) for i, j in enumerate(picks)}


# ------------------------------------------------------------------ 仿真
def simulate(ctx, score, K=20, freq=20, ind_cap=None, start=TEST_START, end=TEST_END,
             cost_buy=COST_BUY, cost_sell=COST_SELL, min_fee=MIN_FEE,
             account=ACCOUNT, mode="mix", w=None, weight_mode="equal",
             ma_filter=None):
    """返回 (nav, log, stats)。mode: mix / price / fund / zero_cost。
    ma_filter: (dates, matrix) 时只买「收盘价 > MA60」的票（趋势过滤）。"""
    dates = ctx["dates"]
    price = pd.DataFrame(ctx["close"]).ffill().to_numpy()
    ret = pd.DataFrame(price).pct_change().fillna(0.0).to_numpy()
    volume = ctx["volume"]
    mask = ctx["mask"]
    board = ctx["board"]
    sym2board = ctx["sym2board"]

    if mode == "price":
        sig = ctx["score_price"]
    elif mode == "fund":
        sig = ctx["score_fund"]
    elif mode == "mix":
        sig = ctx["score_mix"]
    else:
        sig = ctx["score_mix"]

    i0 = dates.searchsorted(pd.Timestamp(start))
    i1 = min(dates.searchsorted(pd.Timestamp(end)), len(dates) - 1)
    exec_days = set(range(i0 + 1, i1 + 1, freq))

    nav = account
    weights = np.zeros(len(ctx["symbols"]))
    navs = {}
    log = []
    for d in range(i0, i1 + 1):
        r = ret[d]
        nav *= (1.0 + float(np.dot(weights, r)))
        navs[d] = nav
        weights = weights * (1.0 + r)
        if d in exec_days:
            s = d - 1                                   # 信号日 = 成交日前一日收盘
            sig_s = sig[s]
            if ma_filter is not None:
                mf_dates, mf_mat = ma_filter
                mi = mf_dates.searchsorted(dates[s])
                if mi < len(mf_dates):
                    ok = np.isfinite(mf_mat[mi]) & (mf_mat[mi] > 0)
                    sig_s = np.where(ok, sig_s, np.nan)
            picks = select(sig_s, mask[s], board[s], sym2board, K, ind_cap)
            tradeable = np.isfinite(price[d]) & (volume[d] > 0)
            limit_up = ret[d] >= 0.098                  # 收盘涨停：买不进
            tgt = pick_weights(sig_s, picks, weight_mode)
            target = {j: ww for j, ww in tgt.items()
                      if tradeable[j] and not limit_up[j]}
            held = {int(j): float(weights[j]) for j in np.where(weights > 0)[0]}
            keep = {j: w for j, w in held.items() if not tradeable[j]}
            free = max(1.0 - sum(keep.values()), 0.0)
            sell_amt = sum(w for j, w in held.items()
                           if j not in target and tradeable[j])
            buy_names = [j for j in target if j not in held]
            buy_amt = sum(target[j] for j in buy_names)
            n_trades = len(buy_names) + sum(1 for j, w in held.items()
                                            if j not in target and tradeable[j])
            cost = 0.0 if mode == "zero_cost" else (
                buy_amt * nav * cost_buy + sell_amt * nav * cost_sell + n_trades * min_fee)
            new_w = np.zeros(len(weights))
            scale = free / max(sum(target.values()), 1e-12)
            for j, w in target.items():
                new_w[j] = w * scale
            for j, w in keep.items():
                new_w[j] = w
            turnover = 0.5 * float(np.abs(new_w - weights).sum())
            nav -= cost
            weights = new_w
            log.append({"date": str(dates[d].date()), "n_picks": len(picks),
                        "n_trades": n_trades, "cost": cost, "turnover": turnover,
                        "nav": nav})
    s = pd.Series(navs)
    s.index = dates[i0:i1 + 1]
    lg = pd.DataFrame(log)
    years = (s.index[-1] - s.index[0]).days / 365.25
    stats = {
        "K": K, "freq": freq, "ind_cap": ind_cap, "mode": mode,
        "start": str(s.index[0].date()), "end": str(s.index[-1].date()),
        "total_cost": float(lg["cost"].sum()) if len(lg) else 0.0,
        "n_rebalances": int(len(lg)),
        "avg_turnover_per_rebalance": float(lg["turnover"].mean()) if len(lg) else 0.0,
        "ann_turnover": float(lg["turnover"].mean() * len(lg) / years) if len(lg) else 0.0,
        "avg_n_picks": float(lg["n_picks"].mean()) if len(lg) else 0.0,
    }
    return s, lg, stats


def pool_equal_nav(ctx, start, end):
    """池内等权（每天按当日成分等权，不算成本）：基线。"""
    dates = ctx["dates"]
    price = pd.DataFrame(ctx["close"]).ffill().to_numpy()
    ret = pd.DataFrame(price).pct_change().fillna(0.0).to_numpy()
    mask = ctx["mask"]
    i0 = dates.searchsorted(pd.Timestamp(start))
    i1 = min(dates.searchsorted(pd.Timestamp(end)), len(dates) - 1)
    nav, out = 1.0, {}
    for d in range(i0, i1 + 1):
        m = mask[d]
        if m.any():
            w = m / m.sum()
            nav *= (1.0 + float(np.dot(w, ret[d])))
        out[d] = nav
    s = pd.Series(out)
    s.index = dates[i0:i1 + 1]
    return s


def main():
    print("① 装载上下文 …")
    ctx = load_ctx()
    print(f"   {len(ctx['dates'])} 个交易日 × {len(ctx['symbols'])} 只")
    sc = load_scores(ctx)
    ctx["board"] = sc["board"]
    ctx["sym2board"] = sc["sym2board"]

    rec = json.loads((RESULTS / "ic_results.json").read_text(encoding="utf-8"))
    sel = rec["selected"]
    W_MIX = (0.65, 0.30, 0.05)                      # 推荐权重（见 PLAN §6）
    W_SEL = (sel["wp"], sel["wf"], sel["we"])        # 验证期选中的权重

    s_mix, miss = make_score_matrix(ctx, sc, *W_MIX)
    s_mix_sel, _ = make_score_matrix(ctx, sc, *W_SEL)
    s_price, _ = make_score_matrix(ctx, sc, 1.0, 0.0, 0.0)
    s_fund, _ = make_score_matrix(ctx, sc, 0.0, 1.0, 0.0)
    ctx["score_mix"], ctx["score_price"], ctx["score_fund"] = s_mix, s_price, s_fund

    print(f"   基本面缺失格子 {miss['fund_missing_cells']} / {s_mix.size}")

    # ---------------- 验证期网格搜索（协议：只在验证期选参数）-----------------
    VALID = ("2020-01-01", "2022-12-31")
    print("② 验证期网格搜索（2020-2022，这段是唯一可用来选参数的区间）…")
    bch_v = ctx["index"].dropna()
    bch_v = bch_v[(bch_v.index >= pd.Timestamp(VALID[0])) &
                  (bch_v.index <= pd.Timestamp(VALID[1]))]
    bch_v = bch_v / bch_v.iloc[0]
    grid = []
    for K in (10, 20, 30, 50):
        for freq in (5, 10, 20, 40):
            for cap in (None, 3, 5):
                for wm in ("equal", "score"):
                    nav_g, lg_g, st_g = simulate(ctx, s_mix, K=K, freq=freq, ind_cap=cap,
                                                 start=VALID[0], end=VALID[1],
                                                 weight_mode=wm)
                    p = perf_stats(nav_g, bch_v)
                    grid.append({"K": K, "freq": freq, "ind_cap": cap, "weight_mode": wm,
                                 "valid_ann": p["ann_return"], "valid_ir": p.get("ir", 0),
                                 "valid_mdd": p["max_drawdown"],
                                 "valid_excess_ann": p.get("excess_ann", 0),
                                 "ann_turnover": st_g["ann_turnover"]})
    gdf = pd.DataFrame(grid).sort_values("valid_ir", ascending=False)
    gdf.to_csv(RESULTS / "strategy_grid_valid.csv", index=False, encoding="utf-8-sig")
    best = gdf.iloc[0].to_dict()
    print(f"   验证期最优: K={int(best['K'])} freq={int(best['freq'])} "
          f"cap={best['ind_cap']} 权重={best['weight_mode']}  "
          f"valid IR {best['valid_ir']:+.2f}  年化 {best['valid_ann']*100:+.2f}%")
    print("   验证期 Top6:")
    print(gdf.head(6).to_string(index=False, float_format=lambda v: f"{v:+.4f}"))

    CFG = {"K": int(best["K"]), "freq": int(best["freq"]),
           "ind_cap": (None if pd.isna(best["ind_cap"]) else int(best["ind_cap"])),
           "weight_mode": best["weight_mode"]}
    print(f"   采纳配置 {CFG}（后面测试期只跑这一套）")

    # ---------------- 测试期主回测 ----------------
    print("③ 测试期回测（2023-01-01 ~ 2026-10-30）…")
    bench = ctx["index"].dropna()
    bench = bench[(bench.index >= pd.Timestamp(TEST_START)) &
                  (bench.index <= pd.Timestamp(TEST_END))]
    bench = bench / bench.iloc[0]

    runs = {}
    navs = {}

    def add(name, nav, log, stats, bench_nav=bench):
        p = perf_stats(nav, bench_nav)
        p.update(stats)
        p["cost_per_year_pct"] = (p["total_cost"] / ACCOUNT /
                                   max(p.get("years", 1), 1e-9) * 100)
        runs[name] = p
        navs[name] = nav
        print(f"   {name:<26} 年化 {p.get('ann_return', 0)*100:+6.2f}%  "
              f"IR {p.get('ir', 0):+.2f}  MDD {p.get('max_drawdown', 0)*100:6.2f}%  "
              f"换手/年 {p.get('ann_turnover', 0):.2f}  成本/年 {p['cost_per_year_pct']:.2f}pct")
        return p

    nav, lg, st = simulate(ctx, s_mix, start=TEST_START, end=TEST_END, **CFG)
    add(f"策略(验证期选参) top{CFG['K']}", nav, lg, st)

    nav0, lg0, st0 = simulate(ctx, s_mix, start=TEST_START, end=TEST_END,
                              mode="zero_cost", **CFG)
    add("同上(零成本对照)", nav0, lg0, st0)

    navd, lgd, std = simulate(ctx, s_mix, K=20, freq=20, start=TEST_START, end=TEST_END)
    add("默认 top20 月调(参照)", navd, lgd, std)

    navp, lgp, stp = simulate(ctx, s_price, K=20, freq=20, start=TEST_START,
                              end=TEST_END, mode="price")
    add("纯价量分 top20 月调", navp, lgp, stp)

    navf, lgf, stf = simulate(ctx, s_fund, K=20, freq=20, start=TEST_START,
                              end=TEST_END, mode="fund")
    add("纯基本面分 top20 月调", navf, lgf, stf)

    navs2, lg2, st2 = simulate(ctx, s_mix_sel, K=20, freq=20, start=TEST_START,
                                end=TEST_END)
    add("混合分(验证期权重) top20 月调", navs2, lg2, st2)

    navic, lgic, stic = simulate(ctx, s_mix, K=20, freq=20, ind_cap=3,
                                 start=TEST_START, end=TEST_END)
    add("混合分 top20 月调(行业≤3)", navic, lgic, stic)

    # 基线
    eq = pool_equal_nav(ctx, TEST_START, TEST_END)
    p = perf_stats(eq, bench)
    p.update({"K": 0, "freq": 0, "ind_cap": None, "mode": "pool_equal",
              "total_cost": 0.0, "ann_turnover": 0.0, "n_rebalances": 0})
    runs["池内等权300只"] = p
    navs["池内等权300只"] = eq
    p = perf_stats(bench, bench)
    p.update({"K": 0, "freq": 0, "ind_cap": None, "mode": "index",
              "total_cost": 0.0, "ann_turnover": 0.0, "n_rebalances": 0})
    runs["沪深300买入持有"] = p
    navs["沪深300买入持有"] = bench
    print(f"   {'池内等权300只':<26} 年化 {p.get('ann_return',0)*100:+6.2f}%")

    # ---------------- 参数敏感性（事后观察，测试期）-----------------
    print("④ 参数敏感性（K × 调仓频率，测试期事后观察）…")
    sens = []
    for K in (10, 20, 30):
        for freq in (5, 10, 20):
            nav_k, lg_k, st_k = simulate(ctx, s_mix, K=K, freq=freq,
                                         start=TEST_START, end=TEST_END)
            pk = perf_stats(nav_k, bench)
            sens.append({"K": K, "freq": freq, "ann_return": pk["ann_return"],
                         "ir": pk.get("ir", 0), "mdd": pk["max_drawdown"],
                         "ann_turnover": st_k["ann_turnover"],
                         "cost_per_year_pct": st_k["total_cost"] / ACCOUNT /
                         max(pk.get("years", 1), 1e-9) * 100,
                         "total_return": pk["total_return"]})
    sdf = pd.DataFrame(sens)
    print(sdf.to_string(index=False, float_format=lambda v: f"{v:+.4f}"))

    # ---------------- 全区间（参考）-----------------
    print("⑤ 全区间 2016-2026 参考 …")
    nav_full, lg_full, st_full = simulate(ctx, s_mix, start=FULL_START,
                                          end=TEST_END, **CFG)
    bench_full = ctx["index"].dropna()
    bench_full = bench_full[(bench_full.index >= pd.Timestamp(FULL_START)) &
                             (bench_full.index <= pd.Timestamp(TEST_END))]
    bench_full = bench_full / bench_full.iloc[0]
    pfull = perf_stats(nav_full, bench_full)
    pfull.update(st_full)
    navs["策略(选参)@全区间"] = nav_full
    navs["沪深300@全区间"] = bench_full
    print(f"   全区间年化 {pfull['ann_return']*100:+.2f}%  IR {pfull.get('ir', 0):+.2f}  "
          f"MDD {pfull['max_drawdown']*100:.2f}%  换手/年 {pfull['ann_turnover']:.2f}")

    # ---------------- 分期（训练 / 验证 / 测试）-----------------
    print("⑥ 分期表现（同一套参数，只换区间）…")
    periods = {"train_2016_2019": ("2016-01-01", "2019-12-31"),
               "valid_2020_2022": ("2020-01-01", "2022-12-31"),
               "test_2023_2026": (TEST_START, TEST_END)}
    per_period = {}
    for pname, (s0, s1) in periods.items():
        nav_p, lg_p, st_p = simulate(ctx, s_mix, start=s0, end=s1, **CFG)
        bch = ctx["index"].dropna()
        bch = bch[(bch.index >= pd.Timestamp(s0)) & (bch.index <= pd.Timestamp(s1))]
        bch = bch / bch.iloc[0]
        pp = perf_stats(nav_p, bch)
        pp.update(st_p)
        pp["cost_per_year_pct"] = (st_p["total_cost"] / ACCOUNT /
                                   max(pp.get("years", 1), 1e-9) * 100)
        per_period[pname] = pp
        print(f"   {pname:<18} 年化 {pp['ann_return']*100:+7.2f}%  IR {pp.get('ir', 0):+.2f}  "
              f"MDD {pp['max_drawdown']*100:7.2f}%  换手/年 {pp['ann_turnover']:.2f}  "
              f"成本/年 {pp['cost_per_year_pct']:.2f}pct")
        navs[f"混合分@{pname}"] = nav_p

    # ---------------- 分年收益 -----------------
    yrows = []
    for name, nav in navs.items():
        yearly_last = nav.resample("YE").last()
        prev = nav.iloc[0]
        for ts, v in yearly_last.items():
            if pd.notna(v) and prev:
                yrows.append({"run": name, "year": ts.year, "ret": float(v / prev - 1)})
            prev = v
    ydf = pd.DataFrame(yrows)
    ydf.to_csv(RESULTS / "backtest_yearly.csv", index=False, encoding="utf-8-sig")

    out = {"test_period": [TEST_START, TEST_END], "config": CFG,
           "valid_best": {k: (None if pd.isna(v) else v) for k, v in best.items()},
           "weights": {
               "recommended": {"price": W_MIX[0], "fund": W_MIX[1], "event": W_MIX[2]},
               "valid_selected": {"price": W_SEL[0], "fund": W_SEL[1], "event": W_SEL[2]}},
           "cost_model": {"buy": COST_BUY, "sell": COST_SELL, "min_fee": MIN_FEE,
                          "account": ACCOUNT},
           "missing": miss, "runs": runs, "sensitivity": sens, "full_period": pfull,
           "per_period": per_period}
    (RESULTS / "backtest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2,
                                                       default=float), encoding="utf-8")
    pd.concat({k: v.rename(k) for k, v in navs.items()}, axis=1).to_parquet(
        RESULTS / "nav_curves.parquet")
    print("⑥ 写出 results/backtest.json / nav_curves.parquet / backtest_yearly.csv")


if __name__ == "__main__":
    main()
