"""查两件事：1) qlib 收益序列是否与新浪一致；2) 4-5月那段跌幅怎么走的。"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

warnings.filterwarnings("ignore")
QLIB = Path(_ROOT + r"/qlib_data/cn_data_2026")


def cal():
    return [x.strip() for x in (QLIB / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load(sym, field):
    arr = np.fromfile(QLIB / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    c = cal()
    start = int(arr[0])
    s = pd.Series(arr[1:], index=c[start : start + len(arr) - 1], dtype="float64")
    s.name = field
    return s


print("=== 各字段的索引范围（是否对齐）===")
for f in ["close", "adjclose", "factor", "volume", "open", "high", "low"]:
    s = load("sh600418", f)
    print(f"  {f:9s} 首 {s.index[0]}  末 {s.index[-1]}  条数 {len(s)}")

adjc = load("sh600418", "adjclose")
close = load("sh600418", "close")
factor = load("sh600418", "factor")

print("\n=== 2026-04-20 ~ 2026-07-05 每日 close / factor / adjclose / 收益 ===")
seg = pd.DataFrame({"close": close, "factor": factor, "adjclose": adjc}).loc["2026-04-20":"2026-07-05"]
seg["adj_ret%"] = seg["adjclose"].pct_change() * 100
seg["close_ret%"] = seg["close"].pct_change() * 100
print(seg.round(4).to_string())

print("\n=== 全序列最大单日跌幅 Top10（按 adjclose）===")
r = adjc.pct_change() * 100
print(r.nsmallest(10).round(2).to_string())

print("\n=== 新浪行情对比（原始价 & 前复权）===")
try:
    import akshare as ak

    raw = ak.stock_zh_a_daily(symbol="sh600418", adjust="").set_index("date")
    qfq = ak.stock_zh_a_daily(symbol="sh600418", adjust="qfq").set_index("date")
    keys = ["20260424", "20260427", "20260601", "20260630", "20260922", "20261008", "20261016", "20261028"]
    print(f"{'日期':12s} {'新浪raw':>10s} {'qlib close':>11s} {'比值':>8s} {'新浪qfq':>10s} {'qlib adjclose':>13s} {'比值':>8s}")
    for k in keys:
        d = k[:4] + "-" + k[4:6] + "-" + k[6:]
        if k in raw.index and d in close.index:
            print(f"{d:12s} {raw.loc[k,'close']:10.4f} {close[d]:11.4f} {close[d]/raw.loc[k,'close']:8.4f} "
                  f"{qfq.loc[k,'close']:10.4f} {adjc[d]:13.4f} {adjc[d]/qfq.loc[k,'close']:8.4f}")
    print("\n新浪 qfq 近 8 行:")
    print(qfq.tail(8)[["open", "high", "low", "close", "volume"]].to_string())
except Exception as e:
    print(f"新浪失败: {type(e).__name__}: {e}")
