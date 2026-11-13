"""检查：factor / close 的 NaN 分布 + 各区间 JAC 与沪深300 的实际涨跌。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config as cfg
import data_model as dm

dm.init_qlib()

df = dm.D.features([cfg.INSTRUMENT], ["$close", "$factor", "$volume"],
                   start_time="2016-01-01", end_time=cfg.DATA_END, freq="day")
df = df.xs(cfg.INSTRUMENT, level="instrument")
nan_f = df["$factor"].isna()
print("factor NaN 天数:", nan_f.sum(), "  其中 close 也 NaN 的:", (nan_f & df["$close"].isna()).sum())
print("close NaN 天数:", df["$close"].isna().sum())
if nan_f.sum():
    print(df[nan_f].to_string())

print("\n--- 各区间涨跌 ---")
for label, s, e in [("验证集", cfg.VALID_START, cfg.VALID_END), ("测试集", cfg.TEST_START, cfg.TEST_END)]:
    j = dm.stock_close(s, e)
    b = dm.bench_close(s, e)
    print(f"{label} {s}~{e}")
    print(f"  江淮汽车 : {j.iloc[0]:.3f} -> {j.iloc[-1]:.3f}  区间 {(j.iloc[-1]/j.iloc[0]-1):+.2%}  ({len(j)} 天)")
    print(f"  沪深300  : {b.iloc[0]:.3f} -> {b.iloc[-1]:.3f}  区间 {(b.iloc[-1]/b.iloc[0]-1):+.2%}  ({len(b)} 天)")
    print(f"  年化(252): 江淮 {(j.iloc[-1]/j.iloc[0])**(252/len(j))-1:+.2%}  沪深300 {(b.iloc[-1]/b.iloc[0])**(252/len(b))-1:+.2%}")
