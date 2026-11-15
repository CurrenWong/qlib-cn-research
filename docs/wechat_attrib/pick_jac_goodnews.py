"""给江淮也抓几个「利好出尽」实例：事前证据是利好、当天却跌。"""

from pathlib import Path

import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

D = Path(_ROOT + r"/projects/jac_600418/news_attribution")

ev = pd.read_csv(D / "events.csv")
ev["date"] = ev["date"].astype(str)
mt = pd.read_csv(D / "news_matches.csv")
mt["event_date"] = mt["event_date"].astype(str)
m = ev.merge(mt[["event_date", "primary_title", "primary_category", "primary_relation"]],
             left_on="date", right_on="event_date", how="left")

GOOD = ["增持", "回购", "中标", "合作", "订单", "业绩预增", "预增", "扭亏", "分红",
        "获批", "核准", "战略", "协议", "增持计划"]
m["t"] = m["primary_title"].fillna("")

print("=== 江淮：利好类公告 + 当天下跌 ===")
g = m[(m["ret"] < -3) & (m["t"].apply(lambda s: any(k in s for k in GOOD)))]
g = g.sort_values("ret")
for _, r in g.head(12).iterrows():
    print(f"{r['date']}  {r['ret']:+6.2f}%  超额{r['excess']:+6.2f}%  {str(r['primary_category']):<10s} {r['t'][:46]}")

print("\n=== 江淮：利好类公告 + 当天上涨（对照）===")
g2 = m[(m["ret"] > 3) & (m["t"].apply(lambda s: any(k in s for k in GOOD)))]
g2 = g2.sort_values("ret", ascending=False)
for _, r in g2.head(8).iterrows():
    print(f"{r['date']}  {r['ret']:+6.2f}%  超额{r['excess']:+6.2f}%  {str(r['primary_category']):<10s} {r['t'][:46]}")
