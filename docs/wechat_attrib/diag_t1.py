"""诊断：002230 的 T+1 在两套实现里到底差在哪。"""

from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

ROOT = Path(_ROOT)
QLIB = ROOT / "qlib_data" / "cn_data_2026"
D = ROOT / "projects" / "iflytek_002230" / "news_attribution"

cal = [x.strip() for x in (QLIB / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load(sym, field):
    arr = np.fromfile(QLIB / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    start = int(arr[0])
    return pd.Series(arr[1:], index=pd.DatetimeIndex(cal[start:start + len(arr) - 1]),
                      dtype="float64")


px = load("sz002230", "adjclose")
bench = load("sh000300", "close")
print("adjclose NaN 数:", int(px.isna().sum()))
for d in ["2015-07-08", "2015-07-09", "2015-07-10", "2026-07-31"]:
    print(f"  {d}: adjclose={px.get(pd.Timestamp(d))} bench={bench.get(pd.Timestamp(d))}")

df = pd.DataFrame({"px": px, "bench": bench}).dropna()
df["ret"] = df["px"].pct_change()
df["ret_b"] = df["bench"].pct_change()
df["exc"] = df["ret"] - df["ret_b"]
df = df.dropna()
idx = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(df.index)}
print("df 行数", len(df), "首日", df.index[0].date())

ev = pd.read_csv(D / "events.csv")
ev["date"] = ev["date"].astype(str)
print("events 里不在 idx 的日期:", [d for d in ev["date"] if d not in idx][:10])

t1 = []
for d in ev["date"]:
    i = idx.get(d)
    t1.append(df["exc"].iloc[i + 1] if (i is not None and i + 1 < len(df)) else np.nan)
ev["t1"] = t1
print("NaN 的 t1 条数:", int(ev["t1"].isna().sum()))
print(ev[ev["t1"].isna()][["date", "ret", "tier"]].to_string(index=False))

has = pd.read_csv(D / "news_matches.csv")
has["event_date"] = has["event_date"].astype(str)
m = ev.merge(has[["event_date", "has_pre_evidence"]], left_on="date", right_on="event_date")
print("\nmerge 行数", len(m))
for label, sub in [("全部", m), ("有证据", m[m["has_pre_evidence"] == True]),  # noqa: E712
                    ("无证据", m[m["has_pre_evidence"] == False])]:  # noqa: E712
    s = sub["t1"]
    print(f"  {label}: n={len(s)} notna={int(s.notna().sum())} "
          f"mean={s.mean()*100:.3f} 胜率(含NaN记负)={(s > 0).mean()*100:.1f} "
          f"胜率(仅有效)={(s.dropna() > 0).mean()*100:.1f}")
