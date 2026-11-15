"""查「为什么 637 只里有 338 只在 2026-10-30 没有收盘价」。

步骤：
  1. 每只票在面板里最后一个有收盘价的日期 → 分布
  2. 有 10-30 价 vs 没 10-30 价的两组，分别的最后日期分布
  3. 本地 qlib bin 里这些票的真实最后日期（直接读 bin）
  4. 数据更新脚本的日志
"""

from pathlib import Path

import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

PROJ = Path(__file__).resolve().parent.parent
LGBM = Path(_ROOT + r"/projects/csi300_lgbm")
QLIB = Path(_ROOT + r"/data/qlib_data/cn_data_2026")

sc = pd.read_parquet(PROJ / "data" / "scores.parquet", columns=["datetime", "symbol", "close"])
sc["datetime"] = pd.to_datetime(sc["datetime"])
last = sc["datetime"].max()

last_date = sc[sc["close"].notna()].groupby("symbol")["datetime"].max()
have = set(last_date[last_date == last].index)
all_syms = sorted(set(sc["symbol"]))
print("面板最后日期:", last.date())
print("总票数", len(all_syms), "| 有 10-30 价", len(have), "| 没有", len(all_syms) - len(have))

miss = [s for s in all_syms if s not in have]
d = last_date[miss]
print("\n=== 没有 10-30 价的 %d 只：各自最后有价日期分布 ===" % len(miss))
print(d.value_counts().sort_index(ascending=False).head(15).to_string())
print("\n最老 5 只:")
print(d.sort_values().head(5).to_string())

print("\n=== 有 10-30 价的 %d 只：最后日期都是 %s？ ===" % (len(have), last.date()))
print(last_date[list(have)].value_counts().head(3).to_string())

print("\n=== 本地 qlib bin 里 bin 的真实最后日期（抽样 6 只） ===")
import numpy as np

for sym in [have.__iter__().__next__()] + miss[:5]:
    f = QLIB / "features" / sym / "day.bin"
    if not f.exists():
        print(f"  {sym}: bin 不存在")
        continue
    arr = np.fromfile(f, dtype=np.float32)
    # qlib bin: 第一个 float 是起始下标，后面每 5 个 float 一根 bar
    start = int(arr[0])
    n = (len(arr) - 1) // 5
    print(f"  {sym}: bin bars={n} 起始下标={start} 末日偏移={n - 1}")

print("\n=== 更新脚本日志尾部 ===")
log = LGBM / "results" / "update_data.log"
if log.exists():
    txt = log.read_text(encoding="utf-8", errors="replace")
    print(txt[-1500:])
else:
    print("  无 update_data.log")
