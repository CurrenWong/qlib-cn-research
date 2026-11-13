"""新数据集（cn_data_2026）体检：SHA256 补校验 + 字段完整性 + 600418 全区间。"""

import hashlib
import json
import os
import sys

import pandas as pd
import requests

SRC = r"C:\Users\curre\Downloads\qlib_bin.tar.gz"
MANIFEST_URL = "https://github.com/chenditc/investment_data/releases/download/2026-10-27/qlib_bin.manifest.json"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024 * 8), b""):
            h.update(b)
    return h.hexdigest()


def main():
    # ---------- 1. SHA256 补校验 ----------
    print("=" * 70)
    print("1) SHA256 校验（上次因网络降级，这次补上）")
    print("=" * 70)
    try:
        r = requests.get(MANIFEST_URL, timeout=90, headers={"User-Agent": "qlib-check"})
        r.raise_for_status()
        j = r.json()
        exp_sha = j["archive_sha256"].split(":")[-1]
        exp_size = int(j["archive_size_bytes"])
        size = os.path.getsize(SRC)
        print(f"清单: tag={j['release_tag']} target_trade_date={j['target_trade_date']}")
        print(f"大小: {size:,} / {exp_size:,} → {'✅' if size == exp_size else '❌'}")
        print("计算 SHA256 ...")
        got = sha256_of(SRC)
        print(f"  got     : {got}")
        print(f"  expected: {exp_sha}")
        print("→", "✅ SHA256 校验通过，文件完好" if got == exp_sha else "❌ 不匹配！")
    except Exception as e:  # noqa: BLE001
        print("manifest 仍取不到:", type(e).__name__, e)

    # ---------- 2. 字段完整性 + 600418 ----------
    print("\n" + "=" * 70)
    print("2) 数据字段与 600418 覆盖（cn_data_2026）")
    print("=" * 70)
    sys.path.insert(0, r"D:\Project\qlib")
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=r"D:\Project\qlib\qlib_data\cn_data_2026", region=REG_CN)

    root = r"D:\Project\qlib\qlib_data\cn_data_2026"
    feat = os.path.join(root, "features", "sh600418")
    print("600418 目录字段:", sorted(os.listdir(feat)) if os.path.isdir(feat) else "目录不存在")

    fields = ["$open", "$high", "$low", "$close", "$volume", "$factor", "$change", "$vwap"]
    df = D.features(["SH600418"], fields, start_time="2000-01-01", end_time="2026-12-31", freq="day")
    d = df.xs("SH600418", level="instrument")
    print(f"\nSH600418: {len(d)} 行 | {d.index[0].date()} ~ {d.index[-1].date()}")
    print("各字段缺失数:")
    print(d.isna().sum().to_string())
    print("\n最后 5 行:")
    print(d.tail(5).to_string())
    print("\n2019-2026 年度收益:")
    c = d["$close"].dropna()
    yearly = c.resample("YE").last().pct_change().dropna()
    for ts, v in yearly.items():
        print(f"  {ts.year}: {v:+.2%}")

    b = D.features(["SH000300"], ["$close"], start_time="2000-01-01", end_time="2026-12-31", freq="day")
    bc = b.xs("SH000300", level="instrument")["$close"].dropna()
    print(f"\n沪深300: {len(bc)} 行 | {bc.index[0].date()} ~ {bc.index[-1].date()} | 末值 {bc.iloc[-1]:.3f}")
    print("2019-2026 年度收益:")
    for ts, v in bc.resample("YE").last().pct_change().dropna().items():
        print(f"  {ts.year}: {v:+.2%}")


if __name__ == "__main__":
    main()
