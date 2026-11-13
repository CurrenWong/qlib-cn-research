"""探针：002230 在 cn_data_2026 里的完整历史长度与缺口。"""

import numpy as np
import pandas as pd
from pathlib import Path

QLIB_DIR = Path(r"D:\Project\qlib\qlib_data\cn_data_2026")


def read_bin(path):
    arr = np.fromfile(path, dtype=np.float32)
    return int(arr[0]), arr[1:]


cal = [x.strip() for x in (QLIB_DIR / "calendars" / "day.txt").read_text().splitlines() if x.strip()]
print(f"日历 {cal[0]} ~ {cal[-1]}（{len(cal)} 天）")

for sym in ["sz002230"]:
    print(f"\n===== {sym} =====")
    for field in ["adjclose", "close", "volume", "amount", "factor", "high", "low"]:
        p = QLIB_DIR / "features" / sym / f"{field}.day.bin"
        if not p.exists():
            print(f"  缺 {field}")
            continue
        start, vals = read_bin(p)
        idx = cal[start:start + len(vals)]
        s = pd.Series(vals, index=idx, dtype="float64")
        print(f"  {field:9s} n={len(s):5d}  {s.index[0]} ~ {s.index[-1]}  末值 {s.iloc[-1]:.4f}")

    start, vals = read_bin(QLIB_DIR / "features" / sym / "adjclose.day.bin")
    idx = cal[start:start + len(vals)]
    adj = pd.Series(vals, index=idx, dtype="float64")
    full = pd.Series(np.nan, index=cal)
    full.loc[adj.index] = adj
    print(f"  覆盖日历 {full.notna().sum()}/{len(cal)} 天；缺失 {full.isna().sum()} 天")
    # 缺失日是否集中在某段
    miss = [d for d in cal if pd.isna(full[d])]
    if miss:
        # 压缩成区间
        runs, s0, prev = [], None, None
        for d in miss:
            if s0 is None:
                s0 = prev = d
                continue
            if (pd.Timestamp(d) - pd.Timestamp(prev)).days > 4:
                runs.append((s0, prev))
                s0 = d
            prev = d
        runs.append((s0, prev))
        print(f"  缺失区间(共 {len(runs)} 段): " + "  ".join(f"{a}~{b}" for a, b in runs[:12])
              + (" ..." if len(runs) > 12 else ""))

    # 涨跌停幅度检查（深主板 10%）
    ret = adj.pct_change()
    print(f"  |日涨跌| max {ret.abs().max()*100:.2f}%  分布 99分位 {ret.abs().quantile(0.99)*100:.2f}%")
    lim = full[full.notna()]
    print(f"  最近 10 日: ")
    print(lim.tail(10).round(4).to_string())
