"""基本面数据源探针：确认哪些接口在本机可用、字段长什么样。

只打印结构和样本，不落盘。跑完就知道「推荐方案」里的数据层能不能落地。
"""

import json

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://data.eastmoney.com/"}


def probe(name, url, pick=None):
    print("=" * 90)
    print(name)
    try:
        r = requests.get(url, headers=UA, timeout=20)
        print("  HTTP", r.status_code, "len", len(r.text))
        j = r.json()
        if isinstance(j, dict):
            print("  top keys:", list(j.keys())[:8])
            data = j.get("data") or j.get("result") or {}
            if isinstance(data, dict):
                print("  data keys:", list(data.keys())[:12])
                for k in ("result", "data", "list"):
                    if k in data and isinstance(data[k], list) and data[k]:
                        rows = data[k]
                        print(f"  rows: {len(rows)}  first row keys:", list(rows[0].keys())[:30])
                        print("  sample:", json.dumps(rows[0], ensure_ascii=False)[:600])
                        return rows[0]
            elif isinstance(data, list) and data:
                print("  rows:", len(data), "keys:", list(data[0].keys())[:30])
                print("  sample:", json.dumps(data[0], ensure_ascii=False)[:600])
                return data[0]
        print("  raw:", r.text[:300])
    except Exception as e:
        print("  ERR", type(e).__name__, e)
    return None


if __name__ == "__main__":
    # 1) 东方财富 F10 主要财务指标（含报告期 + 披露日，可做 PIT）
    probe("东财 F10 MAINFINADATA (600519)",
          "https://datacenter.eastmoney.com/securities/api/data/v1/get?"
          "reportName=RPT_F10_FINANCE_MAINFINADATA&columns=ALL&quoteColumns=&filter="
          "(SECUCODE%3D%22600519.SH%22)&pageNumber=1&pageSize=3&sortTypes=-1&"
          "sortColumns=REPORT_DATE&source=HSF10&client=PC")

    # 2) 东财 F10 主要财务指标（杜邦/每股）
    probe("东财 F10 FINANCE_MAINFINADATA-V2 (600519)",
          "https://datacenter.eastmoney.com/securities/api/data/v1/get?"
          "reportName=RPT_F10_FINANCE_MAINFINADATA_V2&columns=ALL&filter="
          "(SECUCODE%3D%22600519.SH%22)&pageNumber=1&pageSize=3&sortTypes=-1&"
          "sortColumns=REPORT_DATE&source=HSF10&client=PC")

    # 3) 业绩预告（事件类）
    probe("东财 业绩预告 NEWPREDICT (600519)",
          "https://datacenter-web.eastmoney.com/api/data/v1/get?"
          "reportName=RPT_PUBLIC_OP_NEWPREDICT&columns=ALL&filter="
          "(SECURITY_CODE%3D%22600519%22)&pageNumber=1&pageSize=3&sortTypes=-1&"
          "sortColumns=NOTICE_DATE&source=WEB&client=WEB")

    # 4) 实时估值（push2）
    probe("东财 push2 估值快照 (600519)",
          "https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&"
          "fields=f43,f57,f58,f162,f167,f116,f117,f173,f164,f165")

    # 5) 乐咕乐股历史估值（akshare stock_a_indicator_lg 的底层）
    probe("乐咕 A股历史指标 (600519)",
          "https://legulegu.com/api/stockdata/stock-a-indicator?token=x"
          "&scode=600519")
