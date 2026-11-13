"""打印 601229 等异常票的腾讯 kline 原始 JSON 行 + 实时行情。"""
import json

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"

for sym in ["sh601229", "sz002142", "sz002384", "sz300408", "sh601169", "sz002049", "sz300433"]:
    r = requests.get(KLINE_URL, params={"param": f"{sym},day,,,12"}, headers=UA, timeout=30)
    d = (r.json().get("data") or {}).get(sym) or {}
    rows = d.get("day") or []
    print(f"\n=== {sym} keys={list(d.keys())} rows={len(rows)} ===")
    for row in rows[-5:]:
        print(len(row), row)

print("\n=== 实时行情 ===")
q = "sh601229,sz002142,sz002384,sz300408,sh601169,sz002049,sz300433"
rt = requests.get(f"https://qt.gtimg.cn/q={q}", headers=UA, timeout=30)
for line in rt.content.decode("gbk", errors="ignore").split(";"):
    line = line.strip()
    if not line.startswith("v_"):
        continue
    f = line.split("=", 1)[1].strip('"').split("~")
    print(f"{f[2]} {f[1]:<8} 现价={f[3]:>9} 昨收={f[4]:>9} 今开={f[5]:>9} 最高={f[33]:>9} 最低={f[34]:>9} "
          f"涨跌%={f[32]:>8} 时间={f[30]}")

print("\n=== 东财不复权日线（601229 交叉验证）===")
em = requests.get("https://push2his.eastmoney.com/api/qt/stock/kline/get",
                  params={"secid": "1.601229", "fields1": "f1,f2,f3", "fields2": "f51,f52,f53,f54,f55,f56,f57",
                          "klt": "101", "fqt": "0", "beg": "20261020", "end": "20261104"},
                  headers={"User-Agent": UA["User-Agent"]}, timeout=25)
try:
    js = em.json()
    klines = (js.get("data") or {}).get("klines") or []
    for k in klines:
        print(k)
except Exception as e:
    print("东财失败:", type(e).__name__, str(e)[:100], em.text[:200])
