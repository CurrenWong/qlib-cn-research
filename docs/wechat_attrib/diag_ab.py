"""A/B：analysis.py 的 lim-t1 算法 vs compare.py 的 blk 算法，逐事件对齐找出差异。"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\Project\qlib")
QLIB = ROOT / "qlib_data" / "cn_data_2026"
D = ROOT / "projects" / "iflytek_002230" / "news_attribution"

cal = [x.strip() for x in (QLIB / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load(sym, field):
    arr = np.fromfile(QLIB / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    start = int(arr[0])
    return pd.Series(arr[1:], index=pd.DatetimeIndex(cal[start:start + len(arr) - 1]),
                      dtype="float64")


px, bench = load("sz002230", "adjclose"), load("sh000300", "close")

# --- A: analysis.py 的写法 ---
dfA = pd.DataFrame({"px": px, "bench": bench}).dropna()
dfA["ret"] = dfA["px"].pct_change()
dfA["ret_b"] = dfA["bench"].pct_change()
dfA["exc"] = dfA["ret"] - dfA["ret_b"]
dfA = dfA.dropna()
idxA = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(dfA.index)}


def fwd(df, i, k):
    return df["exc"].iloc[i + k] if i + k < len(df) else np.nan


# --- B: compare.py 的写法 ---
dfB = pd.DataFrame({"px": px, "bench": bench}).dropna()
dfB["r"] = dfB["px"].pct_change()
dfB["rb"] = dfB["bench"].pct_change()
exB = (dfB["r"] - dfB["rb"]).dropna()
idxB = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(exB.index)}

print("A 行数", len(dfA), "首", dfA.index[0].date(), "末", dfA.index[-1].date())
print("B 行数", len(exB), "首", exB.index[0].date(), "末", exB.index[-1].date())
print("A/B 索引是否一致:", list(dfA.index) == list(exB.index))
# 逐点比较 excess
d = (dfA["exc"].values - exB.values)
print("exc 最大绝对差:", np.nanmax(np.abs(d)))

ev = pd.read_csv(D / "events.csv")
ev["date"] = ev["date"].astype(str)
lim = ev[ev["is_limit"] == True].copy()
lim["t1"] = [fwd(dfA, idxA[d], 1) if d in idxA else np.nan for d in lim["date"]]
t1B = []
for d_ in lim["date"]:
    i = idxB.get(d_)
    t1B.append(exB.iloc[i + 1] if (i is not None and i + 1 < len(exB)) else np.nan)
lim["t1B"] = t1B

diff = lim[(lim["t1"] - lim["t1B"]).abs() > 1e-12]
print("跌停组不一致条数:", len(diff))
if len(diff):
    print(diff[["date", "ret", "t1", "t1B"]].head(20).to_string(index=False))
    print("A 均值", lim["t1"].mean() * 100, "B 均值", lim["t1B"].mean() * 100)
