"""打印归因结果的各种视角（v2 列）。"""

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
mt = pd.read_csv(HERE / "news_matches.csv")
mt["date"] = mt["event_date"].astype(str)
mt["abs_exc"] = mt["excess"].abs()


def show(df, title, width=96):
    print("\n" + "=" * 118)
    print(title, f"（{len(df)} 条）")
    print("=" * 118)
    for _, r in df.iterrows():
        flag = "涨停" if r["ret"] > 9.5 else ("跌停" if r["ret"] < -9.5 else "")
        print(
            f"{r['date']}  涨跌 {r['ret']:+6.2f}%  超额 {r['excess']:+6.2f}%  "
            f"量比 {r['vol_ratio']:.2f}  {flag:4s}"
        )
        if isinstance(r.get("primary_title"), str) and r["primary_title"]:
            print(f"    └ [{r['primary_relation']}|{r['primary_category']}] {r['primary_title'][:width]}")
        else:
            print("    └ 无事前证据")


mode = sys.argv[1] if len(sys.argv) > 1 else "all"

if mode in ("all", "2026"):
    show(mt[mt["date"] >= "2026-01-01"].sort_values("date"), "【2026 年全部事件】")

if mode in ("all", "top"):
    show(mt.nlargest(20, "abs_exc").sort_values("date"), "【按超额绝对值 Top20（全历史）】")

if mode in ("all", "limit"):
    lim = mt[mt["is_limit"] == True]  # noqa: E712
    show(lim[lim["date"] >= "2024-01-01"].sort_values("date"), "【2024 年后涨跌停事件】")

if mode in ("all", "hist"):
    h = mt[(mt["date"] < "2020-01-01") & (mt["has_pre_evidence"] == True)]
    show(h.nlargest(22, "abs_exc").sort_values("date"), "【2019 前有事前证据的事件 Top22】")

if mode in ("all", "noev"):
    show(mt[mt["has_pre_evidence"] == False].nlargest(15, "abs_exc").sort_values("date"),
         "【无事前证据但幅度最大的事件 Top15】")
