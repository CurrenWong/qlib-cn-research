"""拆解模拟器：打印每次调仓后的权重、日收益贡献，与手工重算对比。"""

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
nav, lg = sim.run()

dpos = {d: i for i, d in enumerate(dates)}
i0 = sim.i0
print("price/ret 形状", sim.price.shape, sim.ret.shape)
print("前 3 天的 ret 非零个数:", [(str(dates[i].date()), int((sim.ret[i] != 0).sum())) for i in range(i0, i0 + 3)])

# 手工走一遍：模拟器的 weights 演变 vs 手工收益
weights = np.zeros(len(ctx["symbols"]))
nav2 = 1e6
rows = []
exec_days = sorted(sim.exec_days)
for d in range(sim.i0, sim.i1 + 1):
    r = sim.ret[d]
    dr = float(np.dot(weights, r))
    nav2 *= (1 + dr)
    if d in sim.exec_days:
        sig = d - 1
        picks = [s for s, _ in lut.get(sig, [])[:10]]
        w_new, cost, traded = sim._rebalance(d, picks, weights, nav2)
        # 手工算这 10 只在 [d, 下个执行日] 的收益
        nd = next((x for x in exec_days if x > d), None)
        if nd is not None:
            manual = np.nanmean([close[nd, s] / close[d, s] - 1 for s in picks
                                 if np.isfinite(close[nd, s]) and np.isfinite(close[d, s])])
        else:
            manual = np.nan
        rows.append({"d": str(dates[d].date()), "w_sum": weights.sum(),
                     "n_held": int((weights > 0).sum()),
                     "ret_dot": dr, "nav": nav2,
                     "manual_next": manual,
                     "picks": [ctx["symbols"][s] for s in picks[:3]],
                     "w_new_sum": w_new.sum(), "w_new_n": int((w_new > 0).sum())})
        weights = w_new
        nav2 -= cost
df = pd.DataFrame(rows)
print(df.head(6).to_string(index=False))
print("\n模拟器隐含的每期收益（nav 变化）vs 手工:")
nav_s = nav
chg = nav_s.pct_change().dropna()
print(f"  模拟器 平均每期 {chg.mean()*100:+.3f}%")
print(f"  手工   平均每期 {df['manual_next'].mean()*100:+.3f}%")
print(f"  相关 {chg.reset_index(drop=True).corr(df['manual_next'].iloc[1:].reset_index(drop=True)):.4f}")
