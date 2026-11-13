"""变体与附录：全部配置在两期的表现 + 一个"指数 MA60 过滤"变体（只在验证期选）。

规则（AGENTS §5.2）：变体的**选择在验证期做**；测试期只用于最终展示，不回头改选型。
"""

import json

import numpy as np
import pandas as pd

import model_core as mc
from backtest import (VALID, TEST, index_nav, strategy_nav, equal_pool_nav, ma20_nav,
                      build_pred_lookup)


def log(*a):
    print(*a, flush=True)


def trend_filter_nav(ctx, oos_pred, K, freq, ma=60, start=None, end=None):
    """LGBM top-K + 指数趋势过滤：沪深300 收盘 < MA60 时空仓。"""
    idx = ctx["index"]
    ma_series = idx.rolling(ma).mean()
    lut = build_pred_lookup(ctx, oos_pred)

    def sel(i):
        d = ctx["dates"][i]
        if d in ma_series.index:
            v = ma_series.loc[d]
            if np.isfinite(v) and idx.loc[d] < v:
                return []          # 空仓
        return [s for s, _ in lut.get(i, [])[:K]]

    sim = mc.Simulator(ctx, sel, freq=freq, start=start, end=end)
    nav, lg = sim.run()
    return nav, lg


def all_configs(ctx, oos, period):
    start, end = period
    b = index_nav(ctx, start, end)
    rows = []
    for K in (5, 10, 20):
        for freq in (5, 20):
            nav, lg = strategy_nav(ctx, oos, K, freq, start, end)
            st = mc.perf_stats(nav, b)
            rows.append({"K": K, "freq": freq,
                         "ann_return": st["ann_return"], "ir": st["ir"],
                         "excess_ann": st["excess_ann"], "mdd": st["max_drawdown"],
                         "sharpe": st["sharpe"], "cost": float(lg["cost"].sum())})
    return pd.DataFrame(rows)


def main():
    ctx = mc.load_all()
    cfg = json.loads((mc.RESULTS / "config.json").read_text(encoding="utf-8"))
    pc = cfg["portfolio"]
    oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
    out = {"selected": pc, "appendix": {}, "variant": {}}

    for period, label in [(VALID, "valid_2020_2022"), (TEST, "test_2023_2026")]:
        df = all_configs(ctx, oos, period)
        out["appendix"][label] = df.to_dict("records")
        log(f"\n== {label} 全部配置 ==")
        log(df.to_string(index=False))

    # ---- 变体：趋势过滤，**只在验证期比较**，测试期只展示 ----
    log("\n== 变体：top-10 + 指数 MA60 过滤 ==")
    res = {}
    for period, label in [(VALID, "valid_2020_2022"), (TEST, "test_2023_2026")]:
        start, end = period
        b = index_nav(ctx, start, end)
        nav, lg = trend_filter_nav(ctx, oos, 10, 20, 60, start, end)
        st = mc.perf_stats(nav, b)
        st["cost_total"] = float(lg["cost"].sum())
        res[label] = st
        log(f"  {label}: 年化 {st['ann_return']*100:6.2f}%  IR {st['ir']:5.2f}  "
            f"超额年化 {st['excess_ann']*100:6.2f}%  MDD {st['max_drawdown']*100:6.2f}%")
    # 无过滤版本对照
    nav0, _ = strategy_nav(ctx, oos, 10, 20, *VALID)
    b0 = index_nav(ctx, *VALID)
    st0 = mc.perf_stats(nav0, b0)
    log(f"  验证期 无过滤版本: 年化 {st0['ann_return']*100:6.2f}%  IR {st0['ir']:5.2f}")
    out["variant"] = {"with_ma60_filter": res,
                      "no_filter_valid": {k: st0[k] for k in
                                          ("ann_return", "ir", "excess_ann", "max_drawdown")},
                      "note": "变体只在验证期比较；若验证期不占优则不采用"}

    (mc.RESULTS / "variants.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    log("\n已写出 results/variants.json")


if __name__ == "__main__":
    main()
