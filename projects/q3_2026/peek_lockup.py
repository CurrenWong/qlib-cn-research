# -*- coding: utf-8 -*-
"""看讯飞 2026-10-21 限售股上市流通公告的要点。"""
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
    "tdate": "", "category": "", "trade": "", "seDate": "2026-10-20~2026-10-22",
    "sortName": "", "sortType": "", "isHLtitle": "true"})
url = None
for a in r.json().get("announcements") or []:
    t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
    print(" ", t[:60])
    if "限售股份上市流通的提示性公告" in t:
        url = "http://static.cninfo.com.cn/" + a["adjunctUrl"].lstrip("/")

if url:
    print("URL:", url)
    pdf = requests.get(url, headers={"User-Agent": H["User-Agent"],
                                     "Referer": "http://www.cninfo.com.cn/"},
                       timeout=120).content
    with pdfplumber.open(io.BytesIO(pdf)) as f:
        txt = "\n".join((p.extract_text() or "") for p in f.pages[:2])
    for line in txt.splitlines():
        if re.search(r"股|流通|占比|日期|解除", line):
            s = line.strip()
            if len(s) > 6:
                print("   ", s[:140])
