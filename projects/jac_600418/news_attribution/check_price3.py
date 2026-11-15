"""决定性检验：qlib cn_data_2026 与 新浪 原始价/前复权 的逐日对齐。

要回答的问题：qlib 的 close 是原始价还是前复权价？两者之间有没有除权跳空？
"""

import warnings

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

warnings.filterwarnings("ignore")
QLIB = _ROOT + r"/qlib_data/cn_data_2026"


def cal():
    with open(QLIB + r"\calendars\day.txt", encoding="utf-8") as f:
        return [x.strip() for x in f if x.strip()]


def load(sym, field):
    arr = np.fromfile(f"{QLIB}\\features\\{sym}\\{field}.day.bin", dtype=np.float32)
    c = cal()
    start = int(arr[0])
    return pd.Series(arr[1:], index=c[start : start + len(arr) - 1], dtype="float64")


import akshare as ak

raw = ak.stock_zh_a_daily(symbol="sh600418", adjust="").copy()
qfq = ak.stock_zh_a_daily(symbol="sh600418", adjust="qfq").copy()
raw["date"] = pd.to_datetime(raw["date"]).dt.strftime("%Y-%m-%d")
qfq["date"] = pd.to_datetime(qfq["date"]).dt.strftime("%Y-%m-%d")
raw = raw.set_index("date")
qfq = qfq.set_index("date")

close = load("sh600418", "close")
factor = load("sh600418", "factor")
adjc = load("sh600418", "adjclose")

print(f"新浪 raw   : {raw.index[0]} ~ {raw.index[-1]}  ({len(raw)} 行)")
print(f"新浪 qfq   : {qfq.index[0]} ~ {qfq.index[-1]}  ({len(qfq)} 行)")
print(f"qlib close : {close.index[0]} ~ {close.index[-1]}  ({len(close)} 行)")

dates = ["2026-03-25", "2026-04-01", "2026-04-27", "2026-05-08", "2026-06-01",
         "2026-06-30", "2026-09-22", "2026-10-08", "2026-10-16", "2026-10-28"]

print(f"\n{'日期':12s} {'qlib close':>11s} {'新浪raw':>10s} {'close/raw':>10s} "
      f"{'qlib adjclose':>14s} {'新浪qfq':>10s} {'adj/qfq':>9s} {'factor':>8s}")
for d in dates:
    if d not in close.index:
        print(f"{d:12s} (qlib 无此日)")
        continue
    r = raw.loc[d, "close"] if d in raw.index else float("nan")
    q = qfq.loc[d, "close"] if d in qfq.index else float("nan")
    print(f"{d:12s} {close[d]:11.4f} {r:10.4f} {close[d]/r:10.4f} "
          f"{adjc[d] if d in adjc.index else float('nan'):14.4f} {q:10.4f} "
          f"{(adjc[d]/q if d in adjc.index and q else float('nan')):9.4f} {factor[d]:8.4f}")

# 找新浪 raw 的最大单日跌幅 —— 如果存在 -50% 的跳空，说明确实发生过转增/送股
rawr = raw["close"].pct_change() * 100
print("\n=== 新浪 raw 最大单日跌幅 Top8（若接近 -50% 即为除权跳空）===")
print(rawr.nsmallest(8).round(2).to_string())
print("\n=== 新浪 raw 2026 年最大单日跌幅 Top8 ===")
print(rawr.loc["2026-01-01":"2026-12-31"].nsmallest(8).round(2).to_string())
print("\n=== 新浪 raw 2026 年最大单日涨幅 Top8 ===")
print(rawr.loc["2026-01-01":"2026-12-31"].nlargest(8).round(2).to_string())

# qlib 前复权序列 vs 新浪 qfq 的日收益相关性
common = [d for d in close.index if d in qfq.index]
a = close.loc[common].pct_change().dropna()
b = qfq.loc[common, "close"].pct_change().dropna()
j = pd.concat([a, b], axis=1, keys=["qlib_close", "sina_qfq"]).dropna()
print(f"\n=== qlib close 日收益 vs 新浪 qfq 日收益（{len(j)} 个共同交易日）===")
print(f"  相关系数: {j.corr().iloc[0,1]:.6f}")
print(f"  平均绝对差: {(j.iloc[:,0]-j.iloc[:,1]).abs().mean()*100:.4f} pct")
print(f"  最大绝对差: {(j.iloc[:,0]-j.iloc[:,1]).abs().max()*100:.4f} pct")
