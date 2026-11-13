"""交叉核对某一天的收盘价：腾讯 kline vs 东财 push2his（不复权）。

用途：追踪期间每天收盘后验证 track_pnl.py 取的价格没有接口层面的偏差。
用法：
    D:\\Project\\qlib\\.venv\\Scripts\\python.exe tools\\verify_closes.py 2026-11-04
不带参数则用 track_positions_latest.csv 里最新的日期。
"""

import json
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://quote.eastmoney.com/"}


def em_secid(symbol: str) -> str:
    code = "".join(c for c in symbol if c.isdigit())
    return ("1." if symbol.upper().startswith("SH") else "0.") + code


def em_close(symbol: str, date: str):
    url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={em_secid(symbol)}&fields1=f1,f2,f3,f4,f5,f6"
           "&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=0"
           f"&beg={date.replace('-', '')}&end={date.replace('-', '')}")
    r = requests.get(url, headers=UA, timeout=25)
    data = (r.json().get("data") or {})
    kl = data.get("klines") or []
    if not kl:
        return None
    parts = kl[0].split(",")
    return float(parts[2])   # f51 日期, f52 开, f53 收


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    pos = json.loads((RES / "positions_A.json").read_text(encoding="utf-8"))["positions"]
    if date is None:
        # 取 track_pnl.csv 里最新的一行日期（track_positions_latest.csv 没有 date 列，
        # 早前这里写死 2026-11-04 会导致「不带参数就核对成前一天」，差异全是隔夜涨跌）
        import csv
        with open(RES / "track_pnl.csv", encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if r.get("date")]
        date = rows[-1]["date"] if rows else "2026-11-04"

    tracker = {}
    import csv
    with open(RES / "track_positions_latest.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            tracker[r["symbol"]] = float(r["close"])

    diffs = []
    print(f"{'名称':<10}{'代码':<10}{'腾讯':>9}{'东财':>9}{'差异%':>9}")
    for p in pos:
        s = p["symbol"]
        em = em_close(s, date)
        tx = tracker.get(s)
        if em is None or tx is None:
            print(f"{p['name']:<10}{s:<10}{str(tx):>9}{str(em):>9}{'缺数据':>9}")
            continue
        d = (tx / em - 1) * 100
        diffs.append((abs(d), p["name"], s, tx, em, d))
        print(f"{p['name']:<10}{s:<10}{tx:>9.2f}{em:>9.2f}{d:>9.4f}")

    b = em_close("SH000300", date)
    print(f"\n沪深300 东财收盘: {b}")
    if diffs:
        diffs.sort(reverse=True)
        mx = diffs[0]
        print(f"最大绝对差异: {mx[1]} {mx[2]} | 腾讯 {mx[3]:.2f} vs 东财 {mx[4]:.2f} = {mx[5]:+.4f}%")
        print("结论:", "✅ 两源一致" if mx[0] < 0.1 else "⚠️ 有偏差，需人工复核")


if __name__ == "__main__":
    main()
