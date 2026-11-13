"""诊断：腾讯接口当前返回什么（原始文本），以及限流恢复情况。"""

import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}

urls = [
    ("fqkline-qfq", "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600418,day,,,640,qfq"),
    ("fqkline-day", "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600418,day,,,640,"),
    ("kline(无复权)", "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=sh600418,day,,,640"),
    ("实时快照", "https://qt.gtimg.cn/q=sh600418"),
]

for name, u in urls:
    for attempt in range(2):
        try:
            r = requests.get(u, headers=UA, timeout=20)
            txt = r.text
            print(f"\n[{name}] HTTP {r.status_code} len={len(txt)} attempt={attempt+1}")
            print("  内容前 200 字:", txt[:200].replace("\n", " "))
            if r.status_code == 200 and txt.strip().startswith("{"):
                break
        except Exception as e:  # noqa: BLE001
            print(f"\n[{name}] attempt={attempt+1} ❌ {type(e).__name__}: {str(e)[:100]}")
        time.sleep(3)
    time.sleep(1)
