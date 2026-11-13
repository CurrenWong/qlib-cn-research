"""探针3：新闻与公告的历史覆盖深度。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_news import cninfo_announcements, em_search_page  # noqa: E402

if __name__ == "__main__":
    print("A) 东财个股新闻：还能再翻多深")
    for pi in (6, 7, 8, 9, 11, 15):
        rows = em_search_page("600418", pi, 50, "default")
        if rows:
            ds = [r.get("date", "")[:10] for r in rows]
            print(f"  page {pi}: {len(rows)} 条 | {ds[0]} ~ {ds[-1]}")
        else:
            print(f"  page {pi}: 空")

    print("\nB) 巨潮公告：全量一次拉")
    try:
        anns = cninfo_announcements("600418", "20010101", "20261028")
        print(f"  一次性返回 {len(anns)} 条")
        if anns:
            ys = {}
            for a in anns:
                ys[a["date"][:4]] = ys.get(a["date"][:4], 0) + 1
            print("  按年:", {k: v for k, v in sorted(ys.items())})
            print("  最早:", min(a["date"] for a in anns), "| 最晚:", max(a["date"] for a in anns))
    except Exception as e:  # noqa: BLE001
        print(f"  失败 {type(e).__name__}: {str(e)[:160]}")

    print("\nC) 巨潮公告：逐年拉（看历史能到多早）")
    for y in (2004, 2008, 2012, 2016, 2020, 2024):
        try:
            a = cninfo_announcements("600418", f"{y}0101", f"{y}1231")
            ds = [x["date"] for x in a]
            print(f"  {y}: {len(a)} 条" + (f" | {min(ds)} ~ {max(ds)}" if ds else ""))
        except Exception as e:  # noqa: BLE001
            print(f"  {y}: 失败 {type(e).__name__}: {str(e)[:100]}")
