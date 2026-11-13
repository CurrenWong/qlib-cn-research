# -*- coding: utf-8 -*-
"""抓江淮 2026-02-14 定增结果公告，确认发行价。"""
import datetime as dt
import re

import pdfplumber
import requests

API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "http://www.cninfo.com.cn/new/disclosure/stock",
     "X-Requested-With": "XMLHttpRequest",
     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

r = requests.post(API, headers=H, timeout=60, data={
    "pageNum": 1, "pageSize": 30, "column": "sse", "tabName": "fulltext",
    "plate": "", "stock": "600418,gssh0600418", "searchkey": "", "secdate": "",
    "tdate": "", "category": "", "trade": "", "seDate": "2026-02-10~2026-02-16",
    "sortName": "", "sortType": "", "isHLtitle": "true"})
anns = r.json().get("announcements") or []
print(f"{len(anns)} 条")
target = None
for a in anns:
    t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
    d = dt.datetime.fromtimestamp(a["announcementTime"] / 1000).strftime("%Y-%m-%d")
    print(f"  {d}  {t[:50]}  {a.get('adjunctUrl')}")
    if "结果暨股本变动" in t:
        target = a.get("adjunctUrl")

if target:
    url = "http://static.cninfo.com.cn/" + target.lstrip("/")
    print("\n下载:", url)
    pdf = requests.get(url, headers={"User-Agent": H["User-Agent"],
                                     "Referer": "http://www.cninfo.com.cn/"},
                       timeout=120).content
    open(r"D:\Project\qlib\projects\q3_2026\pdf\600418_placement.pdf", "wb").write(pdf)
    with pdfplumber.open(r"D:\Project\qlib\projects\q3_2026\pdf\600418_placement.pdf") as f:
        txt = "\n".join((p.extract_text() or "") for p in f.pages[:6])
    print("=" * 60)
    for line in txt.splitlines():
        if re.search(r"发行价格|发行数量|募集资金总额|每股|股/元|元/股|发行对象", line):
            print("  ", line.strip()[:160])
