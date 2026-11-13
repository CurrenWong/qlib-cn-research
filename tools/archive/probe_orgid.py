# -*- coding: utf-8 -*-
"""查 orgId，再按 orgId 拉公告。"""
import json
import re

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "http://www.cninfo.com.cn/new/disclosure/stock",
     "X-Requested-With": "XMLHttpRequest"}

for kw in ("002230", "科大讯飞"):
    r = requests.post("http://www.cninfo.com.cn/new/information/topSearch/query",
                      headers=H, timeout=60,
                      data={"keyWord": kw, "maxSecNum": 10, "maxListNum": 10})
    print(kw, "->", r.status_code, r.text[:300])
