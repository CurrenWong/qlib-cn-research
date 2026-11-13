"""逐只打印 kline 最近 6 根 + 实时行情的昨收/今开/现价，定位 11-02/11-03 数据差异。"""
import requests
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"

CODES = ["SZ300394", "SH688521", "SH600795", "SH601998", "SH601138", "SZ301165", "SZ002837",
         "SH600674", "SZ000001", "SZ000988", "SH603501", "SH600522", "SH601229", "SZ002142",
         "SZ300433", "SZ002049", "SZ002384", "SZ300408", "SH601728", "SH601169"]


def tx(c):
    return ("sh" if c.startswith("SH") else "sz") + "".join(x for x in c if x.isdigit())


def kline(sym):
    r = requests.get(KLINE_URL, params={"param": f"{sym},day,,,12"}, headers=UA, timeout=30)
    d = (r.json().get("data") or {}).get(sym) or {}
    rows = d.get("day") or []
    return pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "volume"])


def main():
    q = ",".join(tx(c) for c in CODES)
    rt = requests.get(f"https://qt.gtimg.cn/q={q}", headers=UA, timeout=30)
    quote = {}
    for line in rt.content.decode("gbk", errors="ignore").split(";"):
        line = line.strip()
        if not line.startswith("v_"):
            continue
        key = line.split("=", 1)[0].replace("v_", "").upper()
        f = line.split("=", 1)[1].strip('"').split("~")
        quote[key] = {"name": f[1], "now": f[3], "prev": f[4], "open": f[5], "high": f[33], "low": f[34]}

    for c in CODES:
        df = kline(tx(c))
        qd = quote.get(c, {})
        print(f"\n=== {c} {qd.get('name','')} | 实时: 昨收={qd.get('prev')} 今开={qd.get('open')} "
              f"现价={qd.get('now')} ===")
        print(df.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
