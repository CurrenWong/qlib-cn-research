# -*- coding: utf-8 -*-
"""拉两家公司三季报前后的行情（含基准），算累计涨跌。

Windows 下 qlib 的 D.features 会 fork，必须放在 __main__ 保护里（本项目实测坑）。
"""
import csv

import qlib
from qlib.data import D

PROVIDER_URI = r"D:\Project\qlib\qlib_data\cn_data_2026"
CODES = {"SZ002230": "科大讯飞", "SH600418": "江淮汽车", "SH000300": "沪深300"}
START, END = "2026-09-15", "2026-10-30"


def main():
    qlib.init(provider_uri=PROVIDER_URI, region="cn")
    df = D.features(list(CODES), ["$close", "$volume", "$factor"],
                    start_time=START, end_time=END, freq="day")
    df.index.names = ["instrument", "datetime"]

    rows = []
    for code, name in CODES.items():
        sub = df.loc[code]
        cl = sub["$close"]
        print("=" * 72)
        print(f"{name} {code}   {START} ~ {END}   {len(sub)} 个交易日")
        prev = cl.shift(1)
        print("最近 10 个交易日:")
        for d, v in cl.tail(10).items():
            pct = (v / prev.loc[d] - 1) * 100
            print(f"  {d.date()}  {v:8.4f}  {pct:+6.2f}%")
            rows.append([name, code, d.date().isoformat(), round(v, 4), round(pct, 2)])
        base, last = cl.iloc[0], cl.iloc[-1]
        print(f"区间: {cl.index[0].date()} {base:.4f} → {cl.index[-1].date()} {last:.4f}"
              f"  = {(last / base - 1) * 100:+.2f}%")

    with open(r"D:\Project\qlib\projects\q3_2026\price_recent.csv", "w",
              newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["name", "code", "date", "close", "pct"])
        w.writerows(rows)
    print("\n已写 price_recent.csv")


if __name__ == "__main__":
    main()
