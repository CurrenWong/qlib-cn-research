"""探针：能否免依赖（只用 requests）拿到 A 股前复权/不复权日线。

东财 klines 接口：
  fqt=1 前复权 / fqt=0 不复权 / fqt=2 后复权
  600418 用 secid=1.600418（1=沪市，0=深市），沪深300 用 secid=1.000300
"""

import json

import requests

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
BASE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


def klines(secid, fqt, beg="19900101", end="20500101", klt=101):
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": klt,      # 101=日线
        "fqt": fqt,      # 0=不复权 1=前复权 2=后复权
        "beg": beg,
        "end": end,
        "lmt": 100000,
    }
    r = requests.get(BASE, params=params, headers=UA, timeout=60)
    r.raise_for_status()
    j = r.json()
    data = (j.get("data") or {}).get("klines") or []
    rows = [x.split(",") for x in data]
    return rows


def main():
    for name, secid in [("江淮汽车", "1.600418"), ("沪深300", "1.000300")]:
        for fqt, tag in [(1, "前复权"), (0, "不复权")]:
            try:
                rows = klines(secid, fqt)
                if not rows:
                    print(f"{name} {tag}: 空返回")
                    continue
                print(f"{name} {tag}: {len(rows)} 根 | 首 {rows[0][0]} 收 {rows[0][2]} | 末 {rows[-1][0]} 收 {rows[-1][2]}")
            except Exception as e:  # noqa: BLE001
                print(f"{name} {tag}: 失败 {type(e).__name__}: {e}")

    # 因子一致性验证：前复权/不复权 = 复权因子？
    adj = klines("1.600418", 1)
    raw = klines("1.600418", 0)
    adj_map = {r[0]: float(r[2]) for r in adj}
    raw_map = {r[0]: float(r[2]) for r in raw}
    common = sorted(set(adj_map) & set(raw_map))[-5:]
    print("\n最近 5 天 前复权/不复权 比值（应≈复权因子）：")
    for d in common:
        print(f"  {d}  前复权 {adj_map[d]:8.3f}  不复权 {raw_map[d]:8.3f}  比值 {adj_map[d]/raw_map[d]:.6f}")


if __name__ == "__main__":
    main()
