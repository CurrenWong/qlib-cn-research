"""回测：策略 vs 四个基线，含零成本对照。

基线（PLAN.md §1，AGENTS §5.2 要求保留"干脆别择时"的退路）：
  B1 沪深300买入持有
  B2 池内等权（20 天调仓）
  B3 MA20 趋势过滤等权（20 天调仓）
  S  LGBM top-K（周度或月度调仓）

另跑一遍**零成本对照**，把成本影响和信号影响分开。
"""

import json

import numpy as np
import pandas as pd

import model_core as mc

VALID = (mc.VALID_START, mc.VALID_END)
TEST = (mc.TEST_START, "2026-10-30")


def log(*a):
    print(*a, flush=True)


def build_pred_lookup(ctx, oos_pred):
    dpos = {d: i for i, d in enumerate(ctx["dates"])}
    spos = {s: i for i, s in enumerate(ctx["symbols"])}
    lut = {}
    for d, s, p in zip(oos_pred["datetime"], oos_pred["symbol"], oos_pred["pred"]):
        i = dpos.get(d)
        if i is None:
            continue
        lut.setdefault(i, []).append((spos[s], float(p)))
    for v in lut.values():
        v.sort(key=lambda x: -x[1])
    return lut


def strategy_nav(ctx, oos_pred, K, freq, start=None, end=None,
                 cost_buy=0.0005, cost_sell=0.0015, min_fee=5.0):
    lut = build_pred_lookup(ctx, oos_pred)

    def sel(i):
        return [s for s, _ in lut.get(i, [])[:K]]

    sim = mc.Simulator(ctx, sel, freq=freq, cost_buy=cost_buy, cost_sell=cost_sell,
                       min_fee=min_fee, start=start, end=end)
    nav, log_df = sim.run()
    return nav, log_df


def equal_pool_nav(ctx, start, end, freq=20, **kw):
    def sel(i):
        members = np.where(ctx["mask"][i])[0]
        return list(members)

    sim = mc.Simulator(ctx, sel, freq=freq, start=start, end=end, **kw)
    nav, lg = sim.run()
    return nav, lg


def ma20_nav(ctx, start, end, freq=20, **kw):
    ma20 = pd.DataFrame(ctx["close"]).rolling(20).mean().to_numpy()

    def sel(i):
        m = ctx["mask"][i]
        c = ctx["close"][i]
        ok = m & np.isfinite(c) & np.isfinite(ma20[i]) & (c > ma20[i])
        return list(np.where(ok)[0])

    sim = mc.Simulator(ctx, sel, freq=freq, start=start, end=end, **kw)
    nav, lg = sim.run()
    return nav, lg


def index_nav(ctx, start, end):
    s = ctx["index"].dropna()
    s = s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    return s / s.iloc[0]


def evaluate(ctx, oos_pred, cfg, period, label):
    start, end = period
    K, freq = cfg["K"], cfg["freq"]
    out = {"period": label, "start": start, "end": end, "K": K, "freq": freq}
    navs = {}

    nav, lg = strategy_nav(ctx, oos_pred, K, freq, start, end)
    navs["strategy"] = nav
    b = index_nav(ctx, start, end)
    out["strategy"] = mc.perf_stats(nav, b)
    out["strategy"]["cost_total"] = float(lg["cost"].sum())
    out["strategy"]["rebalances"] = int(len(lg))
    out["strategy"]["turnover_per_year"] = float(lg["traded"].mean() / freq * 244 / len(nav)) \
        if len(nav) else 0.0

    nav0, lg0 = strategy_nav(ctx, oos_pred, K, freq, start, end,
                             cost_buy=0.0, cost_sell=0.0, min_fee=0.0)
    out["strategy_zero_cost"] = mc.perf_stats(nav0, b)
    navs["strategy_zero_cost"] = nav0

    eq, _ = equal_pool_nav(ctx, start, end)
    navs["equal_pool"] = eq
    out["equal_pool"] = mc.perf_stats(eq, b)

    ma, _ = ma20_nav(ctx, start, end)
    navs["ma20"] = ma
    out["ma20_trend"] = mc.perf_stats(ma, b)

    navs["index"] = b
    out["index_buyhold"] = mc.perf_stats(b, b)
    return out, navs


def extra_configs(ctx, oos_pred, period, label):
    """附：用户要 10 只，故额外跑 K=10 月度版本（选型结论仍是 K=20，这里只是补充展示）。"""
    start, end = period
    b = index_nav(ctx, start, end)
    out = {}
    for K, freq in ((10, 20),):
        nav, lg = strategy_nav(ctx, oos_pred, K, freq, start, end)
        st = mc.perf_stats(nav, b)
        st["cost_total"] = float(lg["cost"].sum())
        st["rebalances"] = int(len(lg))
        out[f"strategy_K{K}_freq{freq}"] = st
    return out


def main():
    ctx = mc.load_all()
    cfg = json.loads((mc.RESULTS / "config.json").read_text(encoding="utf-8"))
    pc = cfg["portfolio"]
    oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
    log(f"组合配置 K={pc['K']} freq={pc['freq']}；预测 {len(oos)} 行 "
        f"{oos['datetime'].min().date()} ~ {oos['datetime'].max().date()}")

    res = {"config": cfg, "periods": {}}
    all_navs = {}
    for period, label in [(VALID, "valid_2020_2022"), (TEST, "test_2023_2026")]:
        out, navs = evaluate(ctx, oos, pc, period, label)
        out.update(extra_configs(ctx, oos, period, label))
        res["periods"][label] = out
        all_navs[label] = navs
        s = out["strategy"]
        log(f"\n== {label} ({period[0]} ~ {period[1]}) ==")
        log(f"  策略      年化 {s['ann_return']*100:7.2f}%  波 {s['ann_vol']*100:5.2f}%  "
            f"IR {s['ir']:5.2f}  MDD {s['max_drawdown']*100:7.2f}%  超额年化 {s['excess_ann']*100:6.2f}%")
        log(f"  零成本    年化 {out['strategy_zero_cost']['ann_return']*100:7.2f}%  "
            f"IR {out['strategy_zero_cost']['ir']:5.2f}")
        log(f"  沪深300   年化 {out['index_buyhold']['ann_return']*100:7.2f}%  "
            f"MDD {out['index_buyhold']['max_drawdown']*100:7.2f}%")
        log(f"  池内等权  年化 {out['equal_pool']['ann_return']*100:7.2f}%  IR {out['equal_pool']['ir']:5.2f}")
        log(f"  MA20趋势  年化 {out['ma20_trend']['ann_return']*100:7.2f}%  IR {out['ma20_trend']['ir']:5.2f}")
        log(f"  成本合计 {s['cost_total']:.0f} 元 / {s['rebalances']} 次调仓")

    (mc.RESULTS / "backtest.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
    nav_df = {}
    for label, navs in all_navs.items():
        for name, s in navs.items():
            nav_df[f"{label}|{name}"] = s
    pd.DataFrame(nav_df).to_parquet(mc.RESULTS / "nav_curves.parquet")
    log(f"\n已写出 results/backtest.json + nav_curves.parquet")


if __name__ == "__main__":
    main()
