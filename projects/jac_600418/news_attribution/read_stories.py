"""按关键词读新闻正文，核对归因事实。"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

news = json.loads((HERE / "news_cache" / "em_news.json").read_text(encoding="utf-8"))
ann = json.loads((HERE / "news_cache" / "cninfo.json").read_text(encoding="utf-8"))

KEYWORDS = sys.argv[1:] or ["华为", "尊界", "三部门", "回购", "产销", "预亏", "异动"]

for kw in KEYWORDS:
    hits = [n for n in news if kw in n["title"] or kw in n.get("content", "")]
    if not hits:
        hits = [a for a in ann if kw in a["title"]]
        for a in hits[:8]:
            print(f"[公告] {a['date']}  {a['title']}")
        print()
        continue
    print(f"===== 关键词「{kw}」命中 {len(hits)} 条 =====")
    for n in hits[:8]:
        print(f"\n● {n['date']}  {n.get('media','')}")
        print(f"  标题: {n['title']}")
        print(f"  正文: {n.get('content','')[:420]}")
        print(f"  链接: {n.get('url','')}")
    print()
