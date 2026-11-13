import numpy as np
import pandas as pd

import model_core as mc
from backtest import strategy_nav, index_nav

ctx = mc.load_all()
oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
valid = oos[(oos["datetime"] >= mc.VALID_START) & (oos["datetime"] <= mc.VALID_END)]
nav, lg = strategy_nav(ctx, valid, 10, 5, mc.VALID_START, mc.VALID_END,
                       cost_buy=0.0, cost_sell=0.0, min_fee=0.0)
bn = index_nav(ctx, mc.VALID_START, mc.VALID_END)
print("bench index range", bn.index[0], bn.index[-1], "len", len(bn), "first/last", bn.iloc[0], bn.iloc[-1])

b = bn.reindex(nav.index).ffill().bfill()
b = b / b.iloc[0]
rb = b.pct_change().dropna()
rr = nav.pct_change().reindex(rb.index).fillna(0.0)
print("rb len", len(rb), "rr len", len(rr))
ex = rr - rb
print("ex head:"); print(ex.head(3))
print("ex tail:"); print(ex.tail(3))
print("ex mean", ex.mean(), "rr mean", rr.mean(), "rb mean", rb.mean())
ex_nav = (1 + ex).cumprod()
print("ex_nav last", ex_nav.iloc[-1])
print("naive: rr cum", (1 + rr).cumprod().iloc[-1], "rb cum", (1 + rb).cumprod().iloc[-1])
print("nav cum", nav.iloc[-1] / nav.iloc[0], "bench cum", bn.iloc[-1] / bn.iloc[0])
print("dtypes", rr.dtype, rb.dtype, ex.dtype)
print("rr index[:3]", rr.index[:3].tolist())
print("rb index[:3]", rb.index[:3].tolist())
