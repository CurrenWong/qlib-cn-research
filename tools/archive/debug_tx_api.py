"""调试腾讯接口的返回结构。"""

import json

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600418,day,,,10000,qfq"
r = requests.get(url, headers=UA, timeout=30)
print("HTTP", r.status_code, "len", len(r.text))
j = r.json()
print("top keys:", list(j.keys()))
d = j.get("data")
print("data type:", type(d).__name__)
if isinstance(d, dict):
    print("data keys:", list(d.keys()))
    sub = d.get("sh600418")
    print("sh600418 type:", type(sub).__name__)
    if isinstance(sub, dict):
        print("  sub keys:", list(sub.keys()))
        for k, v in sub.items():
            if isinstance(v, list):
                print(f"  {k}: list len={len(v)} first={v[0] if v else None}")
    elif isinstance(sub, list):
        print("  list len:", len(sub), "first:", sub[0] if sub else None)
elif isinstance(d, list):
    print("list len:", len(d), "first:", d[0] if d else None)
print("\nraw head:", r.text[:400])
