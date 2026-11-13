"""一次性抓取全部新闻/公告并落本地缓存。

  cninfo.json   巨潮公告 600418 全历史（2001-08 ~ 2026-10，2300+ 条）
  em_news.json  东财个股新闻（keyword=600418，2026-04 ~ 2026-10）
  flash.json    东财/同花顺/财联社快讯（最近若干条，用于当日背景）

用法：..\\..\\..\\.venv\\Scripts\\python.exe fetch_all.py
"""

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_news import cninfo_announcements, em_news, flash_news, save  # noqa: E402


def main():
    print("== 巨潮公告（全历史）==")
    anns = cninfo_announcements("600418", "20010101", "20261028")
    print(f"  共 {len(anns)} 条")
    save("cninfo", anns)

    print("\n== 东财个股新闻（翻页）==")
    news = em_news("600418", pages=10, page_size=50)
    print(f"  共 {len(news)} 条")
    save("em_news", news)

    print("\n== 快讯 ==")
    fl = flash_news()
    print(f"  共 {len(fl)} 条")
    save("flash", fl)

    print("\n缓存目录:", Path(__file__).resolve().parent / "news_cache")


if __name__ == "__main__":
    main()
