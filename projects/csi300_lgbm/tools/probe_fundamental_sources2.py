"""探针 2：历史估值接口 + MAINFINADATA 全字段 + akshare 可用性。"""

import json

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://data.eastmoney.com/"}


def get(url, referer="https://data.eastmoney.com/"):
    h = dict(UA)
    h["Referer"] = referer
    return requests.get(url, headers=h, timeout=25).json()


print("=" * 90)
print("1) 东财 历史估值 RPT_VALUEANALYSIS_DET (600519, 最近 3 条)")
try:
    j = get("https://datacenter-web.eastmoney.com/api/data/v1/get?"
            "reportName=RPT_VALUEANALYSIS_DET&columns=ALL&filter="
            "(SECURITY_CODE%3D%22600519%22)&pageNumber=1&pageSize=3&sortTypes=-1&"
            "sortColumns=TRADE_DATE&source=WEB&client=WEB")
    rows = (j.get("result") or {}).get("data") or []
    print("  count:", (j.get("result") or {}).get("count"))
    if rows:
        print("  keys:", list(rows[0].keys()))
        print("  sample:", json.dumps(rows[0], ensure_ascii=False)[:700])
except Exception as e:
    print("  ERR", e)

print("=" * 90)
print("2) MAINFINADATA 全字段（贵州茅台 最新一条）")
try:
    j = get("https://datacenter.eastmoney.com/securities/api/data/v1/get?"
            "reportName=RPT_F10_FINANCE_MAINFINADATA&columns=ALL&filter="
            "(SECUCODE%3D%22600519.SH%22)&pageNumber=1&pageSize=1&sortTypes=-1&"
            "sortColumns=REPORT_DATE&source=HSF10&client=PC")
    rows = (j.get("result") or {}).get("data") or []
    if rows:
        r = rows[0]
        print("  全字段 (%d):" % len(r))
        for k, v in r.items():
            print(f"    {k:28s} = {v}")
except Exception as e:
    print("  ERR", e)

print("=" * 90)
print("3) akshare 可用性")
try:
    import akshare as ak
    print("  akshare", ak.__version__)
    try:
        df = ak.stock_a_indicator_lg(symbol="600519")
        print("  stock_a_indicator_lg OK", df.shape, list(df.columns)[:12])
        print(df.tail(2).to_string(index=False)[:600])
    except Exception as e:
        print("  stock_a_indicator_lg ERR", type(e).__name__, str(e)[:200])
except Exception as e:
    print("  akshare import ERR", e)
