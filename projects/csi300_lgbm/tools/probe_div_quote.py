"""探测两件事：
1) 腾讯实时行情接口（qt.gtimg.cn）能否给 2026-11-03 收盘价（对账用）
2) 东财分红送配接口能否拿到 2026-10~11 的除权除息日与每股现金红利（判断 11-02 的跳空是不是除权）
"""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}

QUOTE_URL = "https://qt.gtimg.cn/q={}"
DIV_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
           "sortColumns=EX_DIVIDEND_DATE&sortTypes=-1&pageSize=30&pageNumber=1&"
           "reportName=RPT_SHAREBONUS_DET&columns=ALL&filter="
           "(SECURITY_CODE%3D%22{code}%22)")


def get(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("gbk", errors="ignore")


def main():
    picks = json.loads(open(r"D:\Project\qlib\projects\csi300_lgbm\results\picks_K20_price.json",
                            encoding="utf-8").read())
    rows = picks["rows"]
    codes = [r["symbol"] for r in rows]

    # ---- 1) 腾讯实时行情（一次多只）----
    q = ",".join(("sh" if c.startswith("SH") else "sz") + "".join(x for x in c if x.isdigit())
                 for c in codes)
    try:
        txt = get(QUOTE_URL.format(q))
        print("=== 腾讯实时行情（前 4 只，字段 3=昨收? 见下）===")
        for line in txt.strip().split(";"):
            line = line.strip()
            if not line.startswith("v_"):
                continue
            body = line.split("=", 1)[1].strip('"')
            f = body.split("~")
            if len(f) < 40:
                continue
            print(f"{f[1]:<8} {f[2]:<10} 现价={f[3]:>9} 昨收={f[4]:>9} 今开={f[5]:>9} "
                  f"最高={f[33]:>9} 最低={f[34]:>9} 时间={f[30]}")
    except Exception as e:  # noqa: BLE001
        print("腾讯行情接口失败:", type(e).__name__, str(e)[:120])

    # ---- 2) 东财分红送配 ----
    print("\n=== 东财分红送配（取 2026 年记录）===")
    for r in rows:
        code = "".join(x for x in r["symbol"] if x.isdigit())
        try:
            js = json.loads(get(DIV_URL.format(code=code)))
            recs = (js.get("result") or {}).get("data") or []
            hit = [x for x in recs if str(x.get("EX_DIVIDEND_DATE", "")).startswith("2026")]
            if not hit:
                print(f"{r['name']:<8} {code}: 2026 年无分红记录")
                continue
            for x in hit:
                print(f"{r['name']:<8} {code}: 除权除息日={x.get('EX_DIVIDEND_DATE')} "
                      f"股权登记日={x.get('EQUITY_RECORD_DATE')} "
                      f"每10股派息(税前)={x.get('PRETAX_BONUS_RMB')} "
                      f"方案={str(x.get('PLAN_NOTICE_DATE'))} 股息率={x.get('DIVIDENT_RATIO')}")
        except Exception as e:  # noqa: BLE001
            print(f"{r['name']:<8} {code}: 接口失败 {type(e).__name__} {str(e)[:70]}")


if __name__ == "__main__":
    main()
