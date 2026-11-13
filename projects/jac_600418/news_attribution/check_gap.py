"""三个除权跳空日在 qlib / 新浪raw / 新浪qfq 里分别长什么样。"""

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
QLIB = r"D:\Project\qlib\qlib_data\cn_data_2026"


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
for df in (raw, qfq):
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df.set_index("date", inplace=True)

close = load("sh600418", "close")
factor = load("sh600418", "factor")
adjc = load("sh600418", "adjclose")

qlib_ret = close.pct_change() * 100
raw_ret = raw["close"].pct_change() * 100
qfq_ret = qfq["close"].pct_change() * 100

for d in ["2004-10-28", "2005-12-14", "2007-07-05"]:
    print("\n" + "=" * 92)
    print(f"=== {d} 前后各 2 天 ===")
    idx = list(close.index).index(d)
    win = close.index[idx - 2 : idx + 3]
    tbl = pd.DataFrame(
        {
            "qlib close": close.reindex(win),
            "qlib factor": factor.reindex(win),
            "qlib adjclose": adjc.reindex(win),
            "qlib ret%": qlib_ret.reindex(win),
            "sina raw": raw["close"].reindex(win),
            "sina raw ret%": raw_ret.reindex(win),
            "sina qfq": qfq["close"].reindex(win),
            "sina qfq ret%": qfq_ret.reindex(win),
        }
    )
    print(tbl.round(4).to_string())

print("\n=== 结论用数据 ===")
for d in ["2004-10-28", "2005-12-14", "2007-07-05"]:
    print(f"{d}: qlib {qlib_ret.get(d, float('nan')):7.2f}%  "
          f"新浪raw {raw_ret.get(d, float('nan')):7.2f}%  "
          f"新浪qfq {qfq_ret.get(d, float('nan')):7.2f}%")

print("\n=== qlib close / 新浪raw 的比值随时间变化（看是否分段）===")
common = [d for d in close.index if d in raw.index]
ratio = (close.loc[common] / raw["close"].reindex(common))
ratio = ratio.dropna()
ratio = ratio[ratio > 0]
chg = ratio.pct_change().abs()
big = chg[chg > 0.02]
print(f"比值范围: {ratio.min():.6f} ~ {ratio.max():.6f}")
print(f"比值突变日（|变化|>2%）共 {len(big)} 天，前 20:")
for d in big.index[:20]:
    print(f"   {d}  比值 {ratio[d]:.6f}  (前日 {ratio.shift(1)[d]:.6f})  qlib涨跌 {qlib_ret.get(d, float('nan')):7.2f}%  新浪raw涨跌 {raw_ret.get(d, float('nan')):7.2f}%")
