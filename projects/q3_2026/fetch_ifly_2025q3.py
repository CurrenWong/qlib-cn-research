# -*- coding: utf-8 -*-
"""单独查讯飞 2025 年三季报（放宽时间窗，打印命中的标题）。"""
import datetime as dt
import io
import re

import pdfplumber
import requests

API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "http://www.cninfo.com.cn/new/disclosure/stock",
     "X-Requested-With": "XMLHttpRequest",
     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

r = requests.post(API, headers=H, timeout=60, data={
    "pageNum": 1, "pageSize": 30, "column": "szse", "tabName": "fulltext",
    "plate": "", "stock": "002230,9900004565", "searchkey": "", "secdate": "",
    "tdate": "", "category": "", "trade": "", "seDate": "2025-10-15~2025-10-31",
    "sortName": "", "sortType": "", "isHLtitle": "true"})
anns = r.json().get("announcements") or []
print("命中", len(anns), "条")
hit = None
for a in anns:
    t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
    d = dt.datetime.fromtimestamp(a["announcementTime"] / 1000).strftime("%Y-%m-%d")
    flag = " ★" if "季度报告" in t else ""
    print(f"  {d} {t[:48]}{flag}")
    if ("第三季度报告" in t) or ("三季度报告" in t):
        hit = a

if hit:
    url = "http://static.cninfo.com.cn/" + hit["adjunctUrl"].lstrip("/")
    print("\n下载:", url)
    pdf = requests.get(url, headers={"User-Agent": H["User-Agent"],
                                     "Referer": "http://www.cninfo.com.cn/"},
                       timeout=120).content
    with pdfplumber.open(io.BytesIO(pdf)) as f:
        txt = "\n".join((p.extract_text() or "") for p in f.pages[:2])
    print("=" * 60)
    for line in txt.splitlines():
        if re.search(r"营业收入|净利润|扣除非经常|经营活动产生|每股收益", line):
            print("   ", line.strip()[:150])


