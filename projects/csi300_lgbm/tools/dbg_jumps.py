"""查数据质量：1) 最近 30 根 bar 的 close/factor/adjclose；2) 全池子里 |日收益|>11% 的"假崩盘"统计。"""

from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

DATA = Path(_ROOT + r"/qlib_data/cn_data_2026")
cal = (DATA / "calendars" / "day.txt").read_text().split()
P = Path(_ROOT + r"/projects/csi300_lgbm/data/panel.parquet")


def read_field(sym, field):
    p = DATA / "features" / sym.lower() / f"{field}.day.bin"
    if not p.exists():
        return None, None
    raw = p.read_bytes()
    a = np.frombuffer(raw, dtype="<f")
    start = int(a[0])
    n = len(a) - 1
    vals = a[1:]
    return start, vals


def show(sym, n=30):
    print(f"\n=== {sym} ===")
    out = {"date": []}
    for f in ("close", "factor", "adjclose"):
        start, vals = read_field(sym, f)
        if start is None:
            out[f] = [np.nan] * n
            continue
        d = [cal[start + i] for i in range(max(0, len(vals) - n), len(vals))]
        v = vals[max(0, len(vals) - n):]
        out[f] = v
        out["date"] = d
    df = pd.DataFrame(out)
    df["ret"] = df["close"].pct_change()
    print(df.to_string(index=False))


def main():
    for s in ["sh688521", "sz300394", "sz301165", "sz000988", "sz002837"]:
        show(s)

    panel = pd.read_parquet(P)
    close = panel["$close"].unstack(level=1).sort_index()
    ret = close.pct_change()
    big = (ret.abs() > 0.11).sum()
    print("\n|日收益|>11% 的天数统计（按标的）:")
    print(f"  总计 {int(big.sum())} 次，涉及 {int((big > 0).sum())} 只票")
    print("  top10:", big.sort_values(ascending=False).head(10).to_dict())
    # 最近 60 天
    r60 = ret.iloc[-60:]
    b60 = (r60.abs() > 0.11).sum()
    print(f"  最近 60 个交易日: {int(b60.sum())} 次，涉及 {int((b60>0).sum())} 只")
    if b60.sum():
        print("  明细:", {k: int(v) for k, v in b60[b60 > 0].items()})
    # 2016 年后
    r2 = ret[ret.index >= "2016-01-01"]
    b2 = (r2.abs() > 0.11).sum()
    print(f"  2016 年后: {int(b2.sum())} 次，涉及 {int((b2>0).sum())} 只 / {close.shape[1]} 只")


if __name__ == "__main__":
    main()
