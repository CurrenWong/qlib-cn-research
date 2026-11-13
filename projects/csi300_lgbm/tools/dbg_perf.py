import numpy as np
import pandas as pd

import model_core as mc
from backtest import strategy_nav, index_nav

ctx = mc.load_all()
oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
valid = oos[(oos["datetime"] >= mc.VALID_START) & (oos["datetime"] <= mc.VALID_END)]

nav, lg = strategy_nav(ctx, valid, 10, 5, mc.VALID_START, mc.VALID_END,
                       cost_buy=0.0, cost_sell=0.0, min_fee=0.0)
print("nav type", type(nav), "len", len(nav))
print("first", nav.index[0], nav.iloc[0], "last", nav.index[-1], nav.iloc[-1])
total = nav.iloc[-1] / nav.iloc[0]
years = (nav.index[-1] - nav.index[0]).days / 365.25
print("total", total, "years", years, "ann", total ** (1 / years) - 1)
st = mc.perf_stats(nav, index_nav(ctx, mc.VALID_START, mc.VALID_END))
print("perf_stats ann", st["ann_return"], "total", st["total_return"], "bench_total", st["bench_total"])

idx = ctx["index"].dropna()
for d in ("2020-01-02", "2020-12-31", "2021-12-31", "2022-12-30", "2023-12-29", "2026-10-30"):
    t = pd.Timestamp(d)
    if t in idx.index:
        print(d, float(idx.loc[t]))
print("index head/tail", idx.head(2).to_dict(), idx.tail(2).to_dict())
