# -*- coding: utf-8 -*-
"""从巨潮查 2026 三季报公告，拿附件 URL。"""
import json
import re
from pathlib import Path

import requests

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

OUT = Path(_ROOT + r"/projects/q3_2026")
OUT.mkdir(parents=True, exist_ok=True)
API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "http://www.cninfo.com.cn/new/disclosure/stock",
     "X-Requested-With": "XMLHttpRequest",
     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

TARGETS = [("002230", "9900004565", "szse", "科大讯飞"),
           ("600418", "gssh0600418", "sse", "江淮汽车")]

found = {}
for code, org, col, name in TARGETS:
    print("=" * 70, "\n", code, name)
    for page in (1, 2):
        r = requests.post(API, headers=H, timeout=60, data={
            "pageNum": page, "pageSize": 30, "column": col,
            "tabName": "fulltext", "plate": "", "stock": f"{code},{org}",
            "searchkey": "", "secdate": "", "tdate": "",
            "category": "", "trade": "", "seDate": "2026-09-01~2026-10-31",
            "sortName": "", "sortType": "", "isHLtitle": "true"})
        j = r.json()
        anns = j.get("announcements") or []
        print(f"  page{page}: {len(anns)} 条")
        for a in anns:
            t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
            d = a.get("adjunctUrl", "")
            if "三季度" in t or "第三季度" in t:
                print(f"    ★ {a.get('announcementTime')} {t}")
                print(f"      {d}  ({a.get('adjunctSize')}KB)")
                found[code] = {"title": t, "adjunct": d,
                               "url": "http://static.cninfo.com.cn/" + d.lstrip("/")}
        if not anns:
            break

(OUT / "cninfo_q3.json").write_text(
    json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n--- 结果 ---")
for k, v in found.items():
    print(k, v["title"], "\n   ", v["url"])
