"""查：events.csv / news_matches.csv 有没有重复日期，以及按日期 merge 会不会行膨胀。"""

import pandas as pd
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

ROOT = Path(_ROOT)
for code, p in [("600418", ROOT / "projects/jac_600418/news_attribution"),
                ("002230", ROOT / "projects/iflytek_002230/news_attribution")]:
    ev = pd.read_csv(p / "events.csv")
    mt = pd.read_csv(p / "news_matches.csv")
    ev["date"] = ev["date"].astype(str)
    mt["event_date"] = mt["event_date"].astype(str)
    d1 = ev["date"].value_counts()
    d2 = mt["event_date"].value_counts()
    print(f"== {code} ==")
    print(f"  events 行数 {len(ev)}，唯一日期 {ev['date'].nunique()}")
    print(f"  news_matches 行数 {len(mt)}，唯一日期 {mt['event_date'].nunique()}")
    print(f"  events 重复日期: {dict(d1[d1 > 1])}")
    print(f"  mt 重复日期: {dict(d2[d2 > 1])}")
    m = ev.merge(mt[["event_date", "has_pre_evidence"]], left_on="date",
                 right_on="event_date", how="left")
    print(f"  按日期 merge 后行数 {len(m)}  （膨胀 {len(m) - len(ev)} 行）")
    print(f"  merge 后证据数 {int(m['has_pre_evidence'].sum())} vs news_matches 行内证据数 "
          f"{int(mt['has_pre_evidence'].sum())}")
    # 冲突检查：同一日期的两个事件，证据标记是否矛盾
    if len(m) > len(ev):
        g = m.groupby("date")["has_pre_evidence"].nunique()
        conflict = g[g > 1]
        print(f"  同日证据标记冲突的日期数: {len(conflict)} -> {dict(conflict)}")
