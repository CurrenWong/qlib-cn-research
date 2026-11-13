"""调试腾讯接口参数（count 上限）+ 再试东财。"""

import json
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def tx(param):
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={param}"
    r = requests.get(url, headers=UA, timeout=30)
    j = r.json()
    return j.get("msg"), j.get("data")


for param in [
    "sh600418,day,,,320,qfq",
    "sh600418,day,,,640,qfq",
    "sh600418,day,2001-01-01,2026-10-28,640,qfq",
    "sh600418,day,,,10000,qfq",
]:
    try:
        msg, data = tx(param)
        n = len(data) if isinstance(data, list) else (
            len(data.get("sh600418", {}).get("qfqday", [])) if isinstance(data, dict) else "?")
        print(f"{param:45s} msg={msg!r} 类型={type(data).__name__} 条数={n}")
        if isinstance(data, dict) and "sh600418" in data:
            sub = data["sh600418"]
            if isinstance(sub, dict):
                ks = [k for k in sub if isinstance(sub[k], list)]
                print("    可用的 list 键:", ks)
                for k in ks[:2]:
                    lst = sub[k]
                    if lst:
                        print(f"      {k}: len={len(lst)} 首={lst[0][:6]} 末={lst[-1][:6]}")
    except Exception as e:  # noqa: BLE001
        print(f"{param:45s} ❌ {type(e).__name__}: {str(e)[:80]}")
    time.sleep(1)

print("\n=== 东财再试 ===")
p = {"secid": "1.600418", "fields1": "f1,f2,f3,f4,f5,f6",
     "fields2": "f51,f52,f53,f54,f55,f56", "klt": 101, "fqt": 1,
     "beg": "19900101", "end": "20500101", "lmt": 100000}
for i in range(2):
    try:
        r = requests.get("https://push2his.eastmoney.com/api/qt/stock/kline/get", params=p,
                         headers={**UA, "Referer": "https://quote.eastmoney.com/"}, timeout=30)
        k = (r.json().get("data") or {}).get("klines") or []
        print(f"  第{i+1}次: HTTP {r.status_code} 条数 {len(k)}")
        if k:
            print("    末:", k[-1])
            break
    except Exception as e:  # noqa: BLE001
        print(f"  第{i+1}次 ❌ {type(e).__name__}: {str(e)[:90]}")
    time.sleep(3)
