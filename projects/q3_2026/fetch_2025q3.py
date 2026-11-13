# -*- coding: utf-8 -*-
"""抓两家 2025 年三季报，核对上期扣非 / 归母。"""
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
TARGETS = [("002230", "9900004565", "szse"), ("600418", "gssh0600418", "sse")]

for code, org, col in TARGETS:
    print("=" * 70, "\n", code)
    r = requests.post(API, headers=H, timeout=60, data={
        "pageNum": 1, "pageSize": 30, "column": col, "tabName": "fulltext",
        "plate": "", "stock": f"{code},{org}", "searchkey": "", "secdate": "",
        "tdate": "", "category": "", "trade": "", "seDate": "2025-10-01~2025-11-10",
        "sortName": "", "sortType": "", "isHLtitle": "true"})
    anns = r.json().get("announcements") or []
    hit = None
    for a in anns:
        t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
        d = dt.datetime.fromtimestamp(a["announcementTime"] / 1000).strftime("%Y-%m-%d")
        if "第三季度报告" in t:
            print(f"  ★ {d} {t}")
            hit = a
    if not hit:
        print("  未找到"); continue
    url = "http://static.cninfo.com.cn/" + hit["adjunctUrl"].lstrip("/")
    pdf = requests.get(url, headers={"User-Agent": H["User-Agent"],
                                     "Referer": "http://www.cninfo.com.cn/"},
                       timeout=120).content
    with pdfplumber.open(io.BytesIO(pdf)) as f:
        txt = "\n".join((p.extract_text() or "") for p in f.pages[:3])
    for line in txt.splitlines():
        if re.search(r"营业收入|净利润|扣除非经常|经营活动产生|每股收益", line):
            print("   ", line.strip()[:150])
