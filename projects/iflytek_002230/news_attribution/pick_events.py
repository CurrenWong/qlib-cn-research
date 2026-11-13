"""挑出配图候选事件：近期窗口内按 |涨跌| 排序，带归因标题。"""

import pandas as pd
from pathlib import Path

HERE = Path(__file__).resolve().parent

ev = pd.read_csv(HERE / "events.csv")
ev["date"] = ev["date"].astype(str)
mt = pd.read_csv(HERE / "news_matches.csv")
mt["event_date"] = mt["event_date"].astype(str)
m = ev.merge(mt, left_on="date", right_on="event_date", how="left", suffixes=("", "_m"))

for label, s, e in [
    ("近期窗口 2024-09-25 ~ 2026-10-29", "2024-09-25", "2026-10-29"),
    ("2023 AI 行情", "2023-01-01", "2023-12-31"),
    ("2015 股灾", "2015-06-01", "2015-09-30"),
]:
    g = m[(m["date"] >= s) & (m["date"] <= e)].copy()
    g["abs"] = g["ret"].abs()
    g = g.sort_values("abs", ascending=False)
    print(f"\n########## {label}（{len(g)} 条）##########")
    for _, r in g.iterrows():
        title = str(r.get("primary_title", ""))
        if len(title) > 46:
            title = title[:46] + "…"
        cat = r.get("primary_category", "")
        rel = r.get("primary_relation", "")
        print(f"{r['date']}  {r['ret']:+6.2f}%  超额{r['excess']:+6.2f}%  量比{r['vol_ratio']:>5.2f}  "
              f"{'涨停' if r['is_limit'] else '    '}  {str(cat):<12s} {str(rel):<8s} {title}")
