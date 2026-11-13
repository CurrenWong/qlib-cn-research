"""调试：预测 top-K 的实际前瞻收益 vs 组合仿真净值。"""

import numpy as np
import pandas as pd

import model_core as mc
from backtest import build_pred_lookup, strategy_nav, index_nav

ctx = mc.load_all()
oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
valid = oos[(oos["datetime"] >= mc.VALID_START) & (oos["datetime"] <= mc.VALID_END)].copy()
print("验证期预测行数", len(valid), valid["datetime"].min().date(), valid["datetime"].max().date())

# 1) 直接看 top-10 的实现收益
lut = build_pred_lookup(ctx, valid)
dpos = {d: i for i, d in enumerate(ctx["dates"])}
close = ctx["close"]
rows = []
for i, items in sorted(lut.items()):
    if len(items) < 20:
        continue
    for K in (5, 10, 20):
        picks = [s for s, _ in items[:K]]
        fwd = []
        for s in picks:
            if i + 5 < close.shape[0] and np.isfinite(close[i, s]) and np.isfinite(close[i + 5, s]):
                fwd.append(close[i + 5, s] / close[i, s] - 1)
        rows.append({"i": i, "K": K, "mean_fwd": np.mean(fwd) if fwd else np.nan,
                     "n": len(fwd), "date": ctx["dates"][i]})
df = pd.DataFrame(rows)
for K in (5, 10, 20):
    sub = df[df["K"] == K]
    print(f"K={K}: 调仓次数 {len(sub)}, 平均前瞻5日收益 {sub['mean_fwd'].mean()*100:.3f}%, "
          f"中位 {sub['mean_fwd'].median()*100:.3f}%, 正比例 {(sub['mean_fwd']>0).mean()*100:.1f}%")

# 2) 组合仿真 vs 基准
for K, freq in [(10, 5), (10, 20), (20, 20)]:
    nav, lg = strategy_nav(ctx, valid, K, freq, mc.VALID_START, mc.VALID_END,
                           cost_buy=0.0, cost_sell=0.0, min_fee=0.0)
    b = index_nav(ctx, mc.VALID_START, mc.VALID_END)
    st = mc.perf_stats(nav, b)
    print(f"零成本 K={K} freq={freq}: 年化 {st['ann_return']*100:.2f}%  "
          f"超额年化 {st['excess_ann']*100:.2f}%  调仓 {len(lg)} 次")

# 3) 看一个具体调仓日的持仓与权重
sim = mc.Simulator(ctx, lambda i: [s for s, _ in lut.get(i, [])[:10]], freq=5,
                   start=mc.VALID_START, end=mc.VALID_END)
nav, lg = sim.run()
print(lg.head(6).to_string())
print("净值前5:", nav.head(5).round(4).to_dict())
print("净值末5:", nav.tail(5).round(4).to_dict())
