"""训练与选型。

流程（PLAN.md §2）：
- 年度 walk-forward 折：折 Y 的训练集 = 所有 **标签已知** 的历史样本（rows_date ≤ i0-6，
  标签期末 = 样本日 +5 个交易日，必须严格早于折首日）；
- 超参、top-K、调仓频率**只在验证期（2020-2022）选**；
- 测试期（2023-2026）用选定配置做 walk-forward 预测，最后一次性评估；
- 早停用的内层验证集 = 训练窗口尾部 120 个交易日（不碰验证/测试期）。

输出：
  results/hp_search.json    超参搜索（验证期）
  results/config.json       选定的模型配置 + 组合配置
  results/oos_preds.parquet 2018-2026 的 walk-forward 样本外预测
  results/ic_by_year.csv    分年度 RankIC
"""

import json
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

import model_core as mc

RNG = 42

HP_GRID = [
    {"num_leaves": 31, "learning_rate": 0.05, "min_data_in_leaf": 200, "feature_fraction": 0.8},
    {"num_leaves": 15, "learning_rate": 0.05, "min_data_in_leaf": 300, "feature_fraction": 0.9},
    {"num_leaves": 63, "learning_rate": 0.03, "min_data_in_leaf": 100, "feature_fraction": 0.8},
    {"num_leaves": 31, "learning_rate": 0.03, "min_data_in_leaf": 500, "feature_fraction": 0.7},
    {"num_leaves": 15, "learning_rate": 0.03, "min_data_in_leaf": 500, "feature_fraction": 0.9},
    {"num_leaves": 31, "learning_rate": 0.05, "min_data_in_leaf": 1000, "feature_fraction": 0.6},
]
BASE_HP = {"n_estimators": 800, "max_depth": -1, "lambda_l2": 1.0,
           "verbosity": -1, "seed": RNG, "n_jobs": -1, "deterministic": True,
           "force_col_wise": True}
INNER_VALID_DAYS = 120
LABEL_HORIZON = 5          # 标签是未来 5 日收益 → 训练样本必须早 5 个交易日


def log(*a):
    print(*a, flush=True)


def fold_bounds(dates, years):
    out = []
    for y in years:
        i0 = int(dates.searchsorted(pd.Timestamp(f"{y}-01-01")))
        i1 = int(dates.searchsorted(pd.Timestamp(f"{y}-12-31"), side="right")) - 1
        if i1 >= i0:
            out.append((y, i0, i1))
    return out


def train_fold(ctx, hp, i0, i1, cache_tag=None):
    """折 [i0,i1]：训练集 = rows_date ≤ i0-6（标签已知），早停用训练窗尾部 120 天。"""
    X, y, rd = ctx["X"], ctx["y"], ctx["rows_date"]
    inner0 = max(0, i0 - LABEL_HORIZON - 1 - INNER_VALID_DAYS)
    tr = np.where((rd <= i0 - LABEL_HORIZON - 1) & ~np.isnan(y))[0]
    va = np.where((rd >= inner0) & (rd <= i0 - LABEL_HORIZON - 1) & ~np.isnan(y))[0]
    te = np.where((rd >= i0) & (rd <= i1))[0]

    cache = mc.RESULTS / "cache" / f"{cache_tag}.npz" if cache_tag else None
    if cache and cache.exists():
        z = np.load(cache)
        return None, z["te"], z["pred"], int(z["bi"])

    params = dict(BASE_HP)
    params.update(hp)
    model = lgb.LGBMRegressor(**params)
    model.fit(X[tr], y[tr], eval_set=[(X[va], y[va])], eval_metric="l2",
              callbacks=[lgb.early_stopping(80, verbose=False)])
    bi = int(model.best_iteration_ or params["n_estimators"])
    pred = model.predict(X[te]) if len(te) else np.array([])
    if cache:
        cache.parent.mkdir(exist_ok=True)
        np.savez_compressed(cache, te=te, pred=pred, bi=bi)
    return model, te, pred, bi


def eval_preds(ctx, te, pred):
    ic, n = mc.daily_ic(pred, ctx["y"][te], ctx["rows_date"][te])
    return mc.ic_stats(ic), ic


def main():
    t0 = time.time()
    log("装载数据 …")
    ctx = mc.load_all()
    dates = ctx["dates"]
    log(f"  日期 {dates[0].date()} ~ {dates[-1].date()}，股票 {len(ctx['symbols'])}，"
        f"样本 {len(ctx['rows_date'])}，耗时 {time.time()-t0:.0f}s")

    # ---------------- 1. 超参搜索：只用验证期（2020-2022）
    valid_folds = fold_bounds(dates, [2020, 2021, 2022])
    log(f"超参搜索：{len(HP_GRID)} 组配置 × {len(valid_folds)} 折（2020-2022 验证期）")
    hp_results = []
    for gi, hp in enumerate(HP_GRID):
        ics, iters, t1 = [], [], time.time()
        for y, i0, i1 in valid_folds:
            _, te, pred, bi = train_fold(ctx, hp, i0, i1,
                                         cache_tag=f"v3_hp{gi}_{y}_{i0}")
            st, _ = eval_preds(ctx, te, pred)
            ics.append(st["ic_mean"])
            iters.append(bi)
        rec = {**hp, "valid_ic_mean": float(np.mean(ics)), "valid_ic_per_fold": ics,
               "best_iter": iters, "sec": round(time.time() - t1, 1)}
        hp_results.append(rec)
        log(f"  [{gi+1}/{len(HP_GRID)}] leaves={hp['num_leaves']} lr={hp['learning_rate']} "
            f"min_leaf={hp['min_data_in_leaf']} ff={hp['feature_fraction']} → "
            f"验证 RankIC {rec['valid_ic_mean']:.5f}  ({rec['sec']}s)")
    hp_results.sort(key=lambda r: -r["valid_ic_mean"])
    best_hp = {k: hp_results[0][k] for k in
               ("num_leaves", "learning_rate", "min_data_in_leaf", "feature_fraction")}
    log(f"选定超参: {best_hp}  验证 RankIC {hp_results[0]['valid_ic_mean']:.5f}")

    # ---------------- 2. 全期 walk-forward 预测（2018-2026）
    all_folds = fold_bounds(dates, list(range(2018, 2027)))
    rows = []
    fold_log = []
    for y, i0, i1 in all_folds:
        model, te, pred, bi = train_fold(ctx, best_hp, i0, i1, cache_tag=f"v3_final_{y}_{i0}")
        st, _ = eval_preds(ctx, te, pred)
        fold_log.append({"year": y, "i0": str(dates[i0].date()), "i1": str(dates[i1].date()),
                         "best_iter": bi, **st})
        rows.append(pd.DataFrame({
            "datetime": dates[ctx["rows_date"][te]],
            "symbol": [ctx["symbols"][s] for s in ctx["rows_sym"][te]],
            "pred": pred, "y": ctx["y"][te],
            "close": ctx["close"][ctx["rows_date"][te], ctx["rows_sym"][te]],
            "ret_1": ctx["ret"][ctx["rows_date"][te], ctx["rows_sym"][te]],
        }))
        log(f"  折 {y}: 训练截止样本日 ≤ {dates[i0-LABEL_HORIZON-1].date()}, "
            f"iter={bi}, RankIC {st.get('ic_mean', 0):.5f} (t={st.get('t_stat', 0):.2f})")
    oos = pd.concat(rows, ignore_index=True)
    oos.to_parquet(mc.RESULTS / "oos_preds.parquet")

    # 分年度 IC
    ic_list = []
    for y, _, _ in all_folds:
        r = oos[oos["datetime"].dt.year == y]
        df = pd.DataFrame({"d": r["datetime"], "p": r["pred"], "y": r["y"]}).dropna()
        ic2 = []
        for _, g in df.groupby("d"):
            if len(g) < 10:
                continue
            a = g["p"].rank().to_numpy()
            b = g["y"].rank().to_numpy()
            if np.std(a) == 0 or np.std(b) == 0:
                continue
            ic2.append(np.corrcoef(a, b)[0, 1])
        ic_list.append({"year": y, "ic_mean": float(np.mean(ic2)),
                        "ic_std": float(np.std(ic2, ddof=1)), "n_days": len(ic2)})
    ic_df = pd.DataFrame(ic_list)
    ic_df.to_csv(mc.RESULTS / "ic_by_year.csv", index=False)
    log("分年度 RankIC:\n" + ic_df.to_string(index=False))

    # ---------------- 3. 组合配置选择（只用验证期 2020-2022）
    valid_pred = oos[(oos["datetime"] >= mc.VALID_START) & (oos["datetime"] <= mc.VALID_END)]
    cfg_results = []
    for K in (5, 10, 20):
        for freq in (5, 20):
            nav = run_strategy_nav(ctx, valid_pred, K, freq, mc.VALID_START, mc.VALID_END)
            b = mc.bench_nav(ctx, mc.VALID_START, mc.VALID_END)
            st = mc.perf_stats(nav, b)
            cfg_results.append({"K": K, "freq": freq, **{k: st[k] for k in
                              ("ann_return", "ann_vol", "sharpe", "max_drawdown", "ir",
                               "excess_ann", "excess_total", "excess_win_days")}})
            log(f"  配置 K={K:2d} freq={freq:2d}: 年化 {st['ann_return']*100:6.2f}%  "
                f"IR {st['ir']:5.2f}  超额年化 {st['excess_ann']*100:6.2f}%  "
                f"MDD {st['max_drawdown']*100:6.2f}%")
    cfg_results.sort(key=lambda r: -(r["ir"] if r["ir"] == r["ir"] else -9))
    best_cfg = {"K": cfg_results[0]["K"], "freq": cfg_results[0]["freq"]}
    log(f"选定组合配置: {best_cfg}")

    (mc.RESULTS / "hp_search.json").write_text(json.dumps(
        {"hp_grid": hp_results, "selected_hp": best_hp}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (mc.RESULTS / "config.json").write_text(json.dumps(
        {"model_hp": best_hp, "portfolio": best_cfg, "folds": fold_log,
         "config_search_valid": cfg_results,
         "note": "超参与组合配置全部在 2020-2022 验证期选定；测试期 2023-2026 未参与任何选择"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"总耗时 {time.time()-t0:.0f}s")


def run_strategy_nav(ctx, oos_pred, K, freq, start=None, end=None):
    """用给定 OOS 预测跑一次组合仿真（只用 qlib 的 close 序列算收益）。"""
    from backtest import strategy_nav
    nav, _ = strategy_nav(ctx, oos_pred, K=K, freq=freq, start=start, end=end)
    return nav


if __name__ == "__main__":
    main()


