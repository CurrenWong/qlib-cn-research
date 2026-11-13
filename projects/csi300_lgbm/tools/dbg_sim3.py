"""逐股核对：同一批持仓，用 sim.ret 累乘 vs 用 close 直接算，看差在哪。"""

import numpy as np
import pandas as pd

import model_core as mc
from backtest import build_pred_lookup

ctx = mc.load_all()
dates = ctx["dates"]
close = ctx["close"]
oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
valid = oos[(oos["datetime"] >= mc.VALID_START) & (oos["datetime"] <= mc.VALID_END)]
lut = build_pred_lookup(ctx, valid)

sim = mc.Simulator(ctx, lambda i: [s for s, _ in lut.get(i, [])[:10]], freq=20,
                   cost_buy=0.0, cost_sell=0.0, min_fee=0.0,
                   start=mc.VALID_START, end=mc.VALID_END)

d0 = int(sorted(sim.exec_days)[1])          # 第二次调仓日
d1 = int(sorted(sim.exec_days)[2])          # 下一次
i_sig = d0 - 1
picks = [s for s, _ in lut.get(i_sig, [])[:10]]
print(f"窗口 {dates[d0].date()} → {dates[d1].date()}")
print(f"{'symbol':10s} {'close@d0':>10s} {'close@d1':>10s} {'close收益':>10s} "
      f"{'sim.ret累乘':>12s} {'差':>10s}")
for s in picks:
    a, b = close[d0, s], close[d1, s]
    r_sim = float(np.prod(1 + sim.ret[d0 + 1: d1 + 1, s]) - 1)
    r_cls = float(b / a - 1) if np.isfinite(a) and np.isfinite(b) else np.nan
    print(f"{ctx['symbols'][s]:10s} {a:10.4f} {b:10.4f} {r_cls*100:9.3f}% "
          f"{r_sim*100:11.3f}% {(r_sim-r_cls)*100:9.3f}%")

w = np.zeros(len(ctx["symbols"]))
for s in picks:
    w[s] = 1.0 / len(picks)
acc_sim = float(np.prod(1 + sim.ret[d0 + 1: d1 + 1] @ w) - 1)
acc_close = float(np.mean([close[d1, s] / close[d0, s] - 1 for s in picks]))
print(f"\n组合：sim.ret 累乘 {acc_sim*100:+.3f}%   close 直接算 {acc_close*100:+.3f}%")

# sim.price 与 ctx['close'] 是否一致
print("\nprice==close 检查:", np.allclose(np.nan_to_num(sim.price), np.nan_to_num(close)))
diff = np.abs(sim.price - close)
bad = np.argwhere(diff > 1e-6)
print("不一致的格子数:", len(bad))
if len(bad):
    for i, j in bad[:5]:
        print(f"   {dates[i].date()} {ctx['symbols'][j]}: price {sim.price[i,j]:.4f} "
              f"close {close[i,j]:.4f}")
print("\nret 重算检查（自乘）:")
manual_ret = sim.price[d0 + 1: d1 + 1] / sim.price[d0: d1] - 1
print("   与 sim.ret 最大差:", float(np.nanmax(np.abs(manual_ret - sim.ret[d0 + 1: d1 + 1]))))

