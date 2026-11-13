# -*- coding: utf-8 -*-
"""查讯飞 2025 三季报，打印「扣非」附近的原始行（含下 3 行）。"""
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
url = None
for a in r.json().get("announcements") or []:
    t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
    if "季度报告" in t:
        url = "http://static.cninfo.com.cn/" + a["adjunctUrl"].lstrip("/")
print("URL:", url)

pdf = requests.get(url, headers={"User-Agent": H["User-Agent"],
                                 "Referer": "http://www.cninfo.com.cn/"},
                   timeout=120).content
with pdfplumber.open(io.BytesIO(pdf)) as f:
    txt = "\n".join((p.extract_text() or "") for p in f.pages[:3])
lines = [l.strip() for l in txt.splitlines()]
for i, line in enumerate(lines):
    if re.search(r"扣除非经常|归属于上市公司股东的净利润|营业收入（|经营活动产生", line):
        print(f"[{i}] {line[:110]}")
        for j in (1, 2):
            if i + j < len(lines):
                print(f"    +{j}: {lines[i + j][:110]}")
