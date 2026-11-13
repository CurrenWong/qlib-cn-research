"""宽持仓方案对比：K（持仓只数）× 调仓频率（交易日）。

背景：原方案 top10 + 月度调仓在测试期年化 -2.13%，失败原因之一是"10 只太集中"，
年化波动 32% 把算术超额拖死。本脚本把 K 放宽到 20/30/50/100，并把调仓拉长到
季度（60 日）和半年（120 日），看组合层面能否改善。

协议（与 PLAN.md 一致）：
- 选型只看验证期 2020-2022；
- 测试期 2023-2026 只作一次性评估，但**本脚本会在测试期跑多个配置**，
  属于多重比较，结论必须降级看待（见输出的 caveat）。

输出：results/wide_portfolio.json + results/wide_portfolio.log
"""

import json

import numpy as np
import pandas as pd

import backtest as bt
import model_core as mc

VALID = (mc.VALID_START, mc.VALID_END)
TEST = (mc.TEST_START, "2026-10-30")

KS = [10, 20, 30, 50, 100]
FREQS = [20, 60, 120]


def log(*a):
    print(*a, flush=True)


def main():
    ctx = mc.load_all()
    oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
    log(f"预测 {len(oos)} 行 {oos['datetime'].min().date()} ~ {oos['datetime'].max().date()}")
    dpos = {d: i for i, d in enumerate(ctx["dates"])}
    nav_idx = {}
    for period, label in ((VALID, "valid"), (TEST, "test")):
        nav_idx[label] = mc.bench_nav(ctx, period[0], period[1])

    rows = []
    navs = {}
    for K in KS:
        for freq in FREQS:
            row = {"K": K, "freq": freq}
            for period, label in ((VALID, "valid"), (TEST, "test")):
                start, end = period
                nav, lg = bt.strategy_nav(ctx, oos, K, freq, start, end)
                b = nav_idx[label]
                st = mc.perf_stats(nav, b)
                st["cost_total"] = float(lg["cost"].sum())
                st["rebalances"] = int(len(lg))
                st["avg_trades"] = float(lg["traded"].mean()) if len(lg) else 0.0
                navs[f"{label}|K{K}_f{freq}"] = nav
                row[label] = st
            rows.append(row)
            v, t = row["valid"], row["test"]
            log(f"K={K:3d} f={freq:3d} | 验证 年化 {v['ann_return']*100:6.2f}% "
                f"IR {v['ir']:5.2f} MDD {v['max_drawdown']*100:6.2f}% | "
                f"测试 年化 {t['ann_return']*100:6.2f}% IR {t['ir']:5.2f} "
                f"MDD {t['max_drawdown']*100:6.2f}% | 测试成本 {t['cost_total']:.0f}")

    # 基线（同期）
    base = {}
    for period, label in ((VALID, "valid"), (TEST, "test")):
        start, end = period
        eq, _ = bt.equal_pool_nav(ctx, start, end)
        b = nav_idx[label]
        base[label] = {
            "index_buyhold": mc.perf_stats(b, b),
            "equal_pool": mc.perf_stats(eq, b),
        }
        log(f"{label} 基线: 指数年化 {base[label]['index_buyhold']['ann_return']*100:.2f}% "
            f"| 池内等权 {base[label]['equal_pool']['ann_return']*100:.2f}%")

    out = {"grid": rows, "baselines": base,
           "caveat": "测试期被多个配置看过，属多重比较，测试期数字只能当参考，不能当新的选型依据。"}
    (mc.RESULTS / "wide_portfolio.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(navs).to_parquet(mc.RESULTS / "wide_nav.parquet")
    log("已写出 results/wide_portfolio.json + wide_nav.parquet")


if __name__ == "__main__":
    main()
