# -*- coding: utf-8 -*-
"""核实两家公司 2026 年的定增细节（价格/规模/时间）+ 股价区间。"""
import json
import re

import qlib
import requests
from qlib.data import D

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

API = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "http://www.cninfo.com.cn/new/disclosure/stock",
     "X-Requested-With": "XMLHttpRequest",
     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
TARGETS = [("002230", "9900004565", "szse"), ("600418", "gssh0600418", "sse")]


def main():
    print("========== 定增公告（2025-09 ~ 2026-10）==========")
    for code, org, col in TARGETS:
        print("-" * 70, "\n", code)
        for page in (1, 2, 3):
            r = requests.post(API, headers=H, timeout=60, data={
                "pageNum": page, "pageSize": 30, "column": col,
                "tabName": "fulltext", "plate": "", "stock": f"{code},{org}",
                "searchkey": "", "secdate": "", "tdate": "",
                "category": "", "trade": "", "seDate": "2025-09-01~2026-10-31",
                "sortName": "", "sortType": "", "isHLtitle": "true"})
            anns = r.json().get("announcements") or []
            for a in anns:
                t = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
                if re.search(r"发行|募集|结果暨股份变动|验资", t):
                    ts = a.get("announcementTime")
                    import datetime as dt
                    d = dt.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                    print(f"  {d}  {t[:60]}")
            if not anns:
                break

    print("\n========== 2026 年股价区间（实际成交价）==========")
    qlib.init(provider_uri=_ROOT + r"/qlib_data/cn_data_2026", region="cn")
    df = D.features(["SZ002230", "SH600418", "SH000300"],
                    ["$close", "$factor"], start_time="2026-01-01",
                    end_time="2026-10-30", freq="day")
    df.index.names = ["instrument", "datetime"]
    for code in ("SZ002230", "SH600418"):
        s = df.loc[code]
        px = (s["$close"] / s["$factor"]).round(2)
        print(f"{code}: 最高 {px.max():.2f} ({px.idxmax().date()})  "
              f"最低 {px.min():.2f} ({px.idxmin().date()})  "
              f"最新 {px.iloc[-1]:.2f} ({px.index[-1].date()})")
        for m in ("2026-01-05", "2026-04-24", "2026-06-30", "2026-09-30"):
            try:
                print(f"   {m}: {px.loc[m]:.2f}")
            except KeyError:
                pass


if __name__ == "__main__":
    main()
