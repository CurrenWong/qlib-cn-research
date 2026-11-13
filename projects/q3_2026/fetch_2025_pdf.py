# -*- coding: utf-8 -*-
"""存档 2025 年三季报 PDF + 文本（供 check_article.py 核对上期数字）。"""
import io
import re
from pathlib import Path

import pdfplumber
import requests

OUT = Path(r"D:\Project\qlib\projects\q3_2026\pdf")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "http://www.cninfo.com.cn/"}
DOCS = {
    "002230_2025Q3": "http://static.cninfo.com.cn/finalpage/2025-10-21/1224720682.PDF",
    "600418_2025Q3": "http://static.cninfo.com.cn/finalpage/2025-10-31/1224999999.PDF",
}

# 江淮那条 URL 需要现查
API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
HQ = {**H, "X-Requested-With": "XMLHttpRequest",
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
r = requests.post(API, headers=HQ, timeout=60, data={
    "pageNum": 1, "pageSize": 30, "column": "sse", "tabName": "fulltext",
    "plate": "", "stock": "600418,gssh0600418", "searchkey": "", "secdate": "",
    "tdate": "", "category": "", "trade": "", "seDate": "2025-10-25~2025-11-05",
    "sortName": "", "sortType": "", "isHLtitle": "true"})
for a in r.json().get("announcements") or []:
    t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
    if "季度报告" in t:
        DOCS["600418_2025Q3"] = ("http://static.cninfo.com.cn/"
                                 + a["adjunctUrl"].lstrip("/"))
        print("江淮 2025Q3:", DOCS["600418_2025Q3"])

for name, url in DOCS.items():
    pdf = OUT / f"{name}.pdf"
    txt = OUT / f"{name}.txt"
    if not pdf.exists():
        c = requests.get(url, headers=H, timeout=120).content
        if c[:4] != b"%PDF":
            print(name, "不是 PDF:", c[:80]); continue
        pdf.write_bytes(c)
    with pdfplumber.open(pdf) as f:
        body = "\n".join((p.extract_text() or "") for p in f.pages)
    txt.write_text(body, encoding="utf-8")
    print(f"{name}: {len(body)} 字 -> {txt.name}")
