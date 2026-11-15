"""核对本地 qlib 数据的绝对价格 vs 新闻报价 vs 新浪行情。"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

QLIB = Path(_ROOT + r"/qlib_data/cn_data_2026")
OLD = Path(_ROOT + r"/qlib_data/cn_data")


def cal(d):
    return [x.strip() for x in (d / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load(d, sym, field):
    arr = np.fromfile(d / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    c = cal(d)
    start = int(arr[0])
    return pd.Series(arr[1:], index=c[start : start + len(arr) - 1], dtype="float64")


dates = ["2026-03-25", "2026-04-01", "2026-04-27", "2026-06-30", "2026-09-22",
         "2026-10-08", "2026-10-16", "2026-10-28"]

close = load(QLIB, "sh600418", "close")
factor = load(QLIB, "sh600418", "factor")
adjc = load(QLIB, "sh600418", "adjclose")
volume = load(QLIB, "sh600418", "volume")

print("=== cn_data_2026 (新数据) ===")
print(f"{'日期':12s} {'close':>9s} {'factor':>9s} {'adjclose':>10s} {'volume':>12s}")
for d in dates:
    if d in close.index:
        print(f"{d:12s} {close[d]:9.4f} {factor[d]:9.4f} {adjc[d]:10.4f} {volume[d]:12.0f}")
    else:
        print(f"{d:12s} (非交易日)")

print("\n=== 旧 cn_data (Microsoft 快照) 同日期对比 ===")
for d in ["2019-01-02", "2019-04-10", "2020-09-24"]:
    try:
        c2 = load(OLD, "sh600418", "close")
        f2 = load(OLD, "sh600418", "factor")
        print(f"{d}: close {c2[d]:.4f} factor {f2[d]:.4f} adjclose {c2[d]*f2[d]:.4f}")
    except Exception as e:
        print(f"{d}: {type(e).__name__} {e}")

print("\n=== 新浪行情 (akshare, 独立源) ===")
try:
    import akshare as ak

    sd = ak.stock_zh_a_daily(symbol="sh600418", adjust="")
    sd = sd.set_index("date")
    print(f"{'日期':12s} {'close':>9s} {'volume':>12s}")
    for d in dates:
        key = d.replace("-", "")
        if key in sd.index:
            print(f"{d:12s} {sd.loc[key, 'close']:9.4f} {sd.loc[key, 'volume']:12.0f}")
        else:
            print(f"{d:12s} (无)")
    print("\n新浪最近 5 行:")
    print(sd.tail(5)[["open", "high", "low", "close", "volume"]].to_string())
except Exception as e:
    print(f"新浪失败: {type(e).__name__}: {e}")

print("\n=== 换算检验：qlib close / 新浪 close ===")
try:
    sd = ak.stock_zh_a_daily(symbol="sh600418", adjust="").set_index("date")
    for d in dates:
        key = d.replace("-", "")
        if d in close.index and key in sd.index:
            print(f"{d}: qlib {close[d]:.4f} / 新浪 {sd.loc[key,'close']:.4f} = {close[d]/sd.loc[key,'close']:.6f}")
except Exception as e:
    print(f"跳过: {e}")
