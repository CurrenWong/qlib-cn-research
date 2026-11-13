"""探针：东财 vs 腾讯，哪个还能稳定拿到日线（含今天）。"""

import json
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def em(secid="1.600418", fqt=1):
    p = {"secid": secid, "fields1": "f1,f2,f3,f4,f5,f6",
         "fields2": "f51,f52,f53,f54,f55,f56", "klt": 101, "fqt": fqt,
         "beg": "19900101", "end": "20500101", "lmt": 100000}
    r = requests.get("https://push2his.eastmoney.com/api/qt/stock/kline/get",
                     params=p, headers={**UA, "Referer": "https://quote.eastmoney.com/"}, timeout=30)
    j = r.json()
    return (j.get("data") or {}).get("klines") or []


def tx(symbol="sh600418", fq="qfq"):
    # 腾讯：param=<市场代码>,day,<起>,<止>,<数量>,<复权类型>
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,10000,{fq}"
    r = requests.get(url, headers=UA, timeout=30)
    j = r.json()
    d = j.get("data", {}).get(symbol, {})
    key = f"{fq}day" if f"{fq}day" in d else "day"
    return d.get(key) or []


for name, fn, kw in [("东财 em", em, {}), ("腾讯 tx", tx, {})]:
    for attempt in range(3):
        try:
            rows = fn(**kw)
            if rows:
                print(f"{name}: ✅ {len(rows)} 根 | 首 {rows[0][0]} | 末 {rows[-1][0]}")
                break
            print(f"{name}: 空返回")
        except Exception as e:  # noqa: BLE001
            print(f"{name} 第{attempt+1}次: {type(e).__name__}: {str(e)[:100]}")
            time.sleep(2)
    else:
        print(f"{name}: ❌ 三次都失败")

# 腾讯 不复权 + 沪深300
for kw in [{"symbol": "sh600418", "fq": ""}, {"symbol": "sh000300", "fq": "qfq"}]:
    try:
        rows = tx(**kw)
        print(f"腾讯 {kw}: {'✅' if rows else '空'} {len(rows)} 根, 末 {rows[-1][0] if rows else '-'}")
    except Exception as e:  # noqa: BLE001
        print(f"腾讯 {kw}: ❌ {type(e).__name__}: {str(e)[:80]}")
