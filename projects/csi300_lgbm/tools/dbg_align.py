"""校验：用手工重算的持仓收益 vs 模拟器净值 vs 分档统计（标签）三者对齐。"""

import numpy as np
import pandas as pd

import model_core as mc
from backtest import build_pred_lookup, strategy_nav, index_nav

ctx = mc.load_all()
dates = ctx["dates"]
close = ctx["close"]
oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
valid = oos[(oos["datetime"] >= mc.VALID_START) & (oos["datetime"] <= mc.VALID_END)]
lut = build_pred_lookup(ctx, valid)

K, freq = 10, 20
nav, lg = strategy_nav(ctx, valid, K, freq, mc.VALID_START, mc.VALID_END,
                       cost_buy=0.0, cost_sell=0.0, min_fee=0.0)

print("模拟器调仓日志前 5 行:")
print(lg.head(5).to_string(index=False))

# 手工重算：信号日 t 的 top-10，持有到下一次调仓（t+freq），用 close 直接算
dpos = {d: i for i, d in enumerate(dates)}
rows = []
exec_dates = list(lg["date"])
for k in range(len(exec_dates) - 1):
    d0 = pd.Timestamp(exec_dates[k])          # 成交日 = 信号日 + 1
    d1 = pd.Timestamp(exec_dates[k + 1])      # 下一次成交日
    sig_idx = dpos.get(d0 - pd.Timedelta(days=0))
    # 信号日 = 成交日的前一个交易日
    i_sig = dpos[d0] - 1
    picks = [s for s, _ in lut.get(i_sig, [])[:K]]
    i0, i1 = dpos[d0], dpos[d1]
    fwd5 = np.nanmean([close[i0 + 5, s] / close[i0, s] - 1 for s in picks
                       if i0 + 5 < close.shape[0] and np.isfinite(close[i0 + 5, s])
                       and np.isfinite(close[i0, s])])
    fwd20 = np.nanmean([close[i1, s] / close[i0, s] - 1 for s in picks
                        if np.isfinite(close[i1, s]) and np.isfinite(close[i0, s])])
    # 池内等权 20 日
    pool = np.where(ctx["mask"][i_sig])[0]
    pool20 = np.nanmean([close[i1, s] / close[i0, s] - 1 for s in pool
                         if np.isfinite(close[i1, s]) and np.isfinite(close[i0, s])])
    rows.append({"d": d0.date(), "top10_fwd5": fwd5, "top10_fwd20": fwd20,
                 "pool_fwd20": pool20, "nav_chg": nav.iloc[k + 1] / nav.iloc[k] - 1})
df = pd.DataFrame(rows)
print("\n手工重算 vs 模拟器净值（无成本）:")
print(df.head(8).to_string(index=False))
print(f"\n均值: top10_fwd20 {df['top10_fwd20'].mean()*100:+.3f}%  "
      f"pool_fwd20 {df['pool_fwd20'].mean()*100:+.3f}%  "
      f"nav_chg {df['nav_chg'].mean()*100:+.3f}%")
print(f"top10_fwd5 均值 {df['top10_fwd5'].mean()*100:+.3f}%")
print(f"相关性 nav_chg vs top10_fwd20: {df['nav_chg'].corr(df['top10_fwd20']):.4f}")

# 标签口径核对：oos 里的 y 与 close 重算是否一致
sub = oos[(oos["datetime"] == pd.Timestamp("2022-06-15"))].head(5)
i = dpos[pd.Timestamp("2022-06-15")]
for _, r in sub.iterrows():
    j = ctx["symbols"].index(r["symbol"])
    calc = close[i + 5, j] / close[i, j] - 1
    print(f"  {r['symbol']}: y={r['y']:.6f} 重算={calc:.6f} 差={abs(r['y']-calc):.2e}")
