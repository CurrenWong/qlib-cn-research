"""打印指定日期区间的个股新闻全文（避开 cmd 管道的编码问题）。"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
news = json.loads((HERE / "news_cache" / "em_news.json").read_text(encoding="utf-8"))

windows = [("2026-07-08", "2026-07-10"), ("2026-09-22", "2026-09-23"), ("2026-10-13", "2026-10-15")]

for lo, hi in windows:
    print("\n" + "=" * 100)
    print(f"=== {lo} ~ {hi} ===")
    print("=" * 100)
    for n in sorted([x for x in news if lo <= x["date"][:10] <= hi], key=lambda x: x["date"]):
        print(f"\n[{n['date']}] {n.get('media','')}")
        print(f"  {n['title']}")
        c = n.get("content", "")
        print(f"  {c[:520]}")
