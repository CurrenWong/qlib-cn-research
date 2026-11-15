"""江淮 2018-2026 实际成交价 + 候选事件（带归因标题），给配图用。"""

from pathlib import Path

import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

D = Path(_ROOT + r"/projects/jac_600418/news_attribution")

px = pd.read_csv(D / "price_cache.csv", parse_dates=["date"]).set_index("date").sort_index()
px = px.loc["2018-01-01":"2026-10-29"]
print("区间", px.index[0].date(), "~", px.index[-1].date(), "共", len(px))
print("最低", px["close"].min(), px["close"].idxmin().date(), " 最高", px["close"].max(),
      px["close"].idxmax().date())
print("末值", px["close"].iloc[-1])

ev = pd.read_csv(D / "events.csv")
ev["date"] = ev["date"].astype(str)
mt = pd.read_csv(D / "news_matches.csv")
mt["event_date"] = mt["event_date"].astype(str)
m = ev.merge(mt[["event_date", "primary_title", "primary_category", "primary_relation"]],
             left_on="date", right_on="event_date", how="left")

picks = ["2018-03-23", "2020-06-12", "2020-11-04", "2020-11-26",
         "2020-12-03", "2024-07-10", "2025-04-08", "2026-07-07"]
print("\n候选事件：")
for d in picks:
    r = m[m["date"] == d]
    if not len(r):
        print(f"  {d}  无事件")
        continue
    r = r.iloc[0]
    close = float(px["close"].get(pd.Timestamp(d), float("nan")))
    print(f"  {d}  {r['ret']:+6.2f}%  超额{r['excess']:+6.2f}%  收盘 {close:.2f}  "
          f"{str(r['primary_category']):<10s} {str(r['primary_title'])[:44]}")
