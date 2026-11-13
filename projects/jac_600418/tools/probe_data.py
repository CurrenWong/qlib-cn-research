import qlib
from qlib.constant import REG_CN
from qlib.data import D

qlib.init(provider_uri=r"D:\Project\qlib\qlib_data\cn_data", region=REG_CN)

c = D.calendar(freq="day")
print("calendar:", c[0], "->", c[-1], len(c))

for code in ["SH600418", "SH000300"]:
    df = D.features([code], ["$close", "$volume"], start_time="2007-01-01", end_time="2020-12-31", freq="day")
    print(code, "rows:", len(df))
    if len(df):
        print("  first:", df.index[0], float(df.iloc[0, 0]))
        print("  last :", df.index[-1], float(df.iloc[-1, 0]))

# 是否有复权因子 / 基准指数数据
inst = D.instruments("all")
lst = D.list_instruments(inst, start_time="2010-01-01", end_time="2020-08-01", as_list=True)
print("instruments(all) count:", len(lst))
print("SH600418 in all:", "SH600418" in lst)

import pandas as pd
from pathlib import Path

root = Path(r"D:\Project\qlib\qlib_data\cn_data")
print("instruments files:", [p.name for p in (root / "instruments").iterdir()])
print("features dirs:", len(list((root / "features").iterdir())))
print("SH600418 feature files:", [p.name for p in (root / "features" / "sh600418").iterdir()])
