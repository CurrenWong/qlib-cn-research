# -*- coding: utf-8 -*-
"""探测东财公告接口，拿标题 / 股票 / PDF 附件地址。"""
import json

import requests

CODES = ["AN202610201830716111", "AN202610301831237531"]
API = "https://np-cnotice-stock.eastmoney.com/api/content/ann"
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}

for code in CODES:
    print("=" * 70)
    print(code)
    try:
        r = requests.get(API, params={"art_code": code, "client_source": "web",
                                      "page_index": 1}, headers=H, timeout=30)
        print("  HTTP", r.status_code, len(r.content), "bytes")
        j = r.json()
        d = j.get("data") or {}
        print("  keys:", list(d.keys()))
        for k in ("notice_title", "notice_date", "stock_name", "stock_code",
                  "attach_url", "attach_size", "codes", "columns"):
            if k in d:
                print(f"  {k}: {str(d[k])[:200]}")
        body = d.get("notice_content") or ""
        print("  notice_content 长度:", len(body))
        if body:
            print("  开头:", body[:300].replace("\n", " "))
    except Exception as e:
        print("  ERR", type(e).__name__, str(e)[:300])
