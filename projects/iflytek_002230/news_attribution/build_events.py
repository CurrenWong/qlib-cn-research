"""从本地 qlib 数据生成 002230 科大讯飞的"明显涨跌"事件表。

数据源：qlib_data\\cn_data_2026（已校验到 2026-10-28）
输出：events.csv

事件定义（三档，取并集）：
  L1 绝对涨跌 ≥ 5%              —— 明显涨跌
  L2 相对沪深300 超额 ≥ 4%      —— 个股特异性涨跌（剔除大盘 beta）
  L3 涨跌停（|涨跌| ≥ 9.5%）    —— 情绪极值

附加标记：量比（成交量 / 20 日均量）、后续 5 日累计收益。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

QLIB_DIR = Path(_ROOT + r"/qlib_data/cn_data_2026")
OUT = Path(__file__).resolve().parent / "events.csv"

SYM = "sz002230"
BENCH = "sh000300"


def read_bin(path: Path) -> tuple[int, np.ndarray]:
    arr = np.fromfile(path, dtype=np.float32)
    if arr.size == 0:
        raise ValueError(f"空文件: {path}")
    return int(arr[0]), arr[1:]


def load_series(symbol: str, field: str, calendar: list[str]) -> pd.Series:
    path = QLIB_DIR / "features" / symbol / f"{field}.day.bin"
    if not path.exists():
        raise FileNotFoundError(path)
    start, vals = read_bin(path)
    s = pd.Series(vals, index=calendar[start : start + len(vals)], dtype="float64")
    return s


def main():
    cal_path = QLIB_DIR / "calendars" / "day.txt"
    calendar = [x.strip() for x in cal_path.read_text().splitlines() if x.strip()]
    print(f"日历 {calendar[0]} ~ {calendar[-1]}（{len(calendar)} 天）")

    df = pd.DataFrame(index=pd.Index(calendar, name="date"))
    for f in ["adjclose", "close", "volume", "amount", "high", "low", "factor"]:
        try:
            df[f] = load_series(SYM, f, calendar)
        except FileNotFoundError:
            print(f"  (缺 {f})")

    # 基准：沪深300（指数无复权因子，直接用 close）
    bench = pd.Series(dtype="float64")
    for f in ["close", "adjclose"]:
        try:
            bench = load_series(BENCH, f, calendar)
            break
        except FileNotFoundError:
            continue

    df["ret"] = df["adjclose"].pct_change()
    df["ret_bench"] = bench.pct_change().reindex(df.index)
    df["excess"] = df["ret"] - df["ret_bench"]
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma20"]
    df["fwd5"] = df["adjclose"].shift(-5) / df["adjclose"] - 1
    df["turnover_value"] = df["amount"]

    df["tier"] = ""
    m_abs = df["ret"].abs() >= 0.05
    m_exc = df["excess"].abs() >= 0.04
    m_lim = df["ret"].abs() >= 0.095
    df.loc[m_abs, "tier"] += "L1绝对"
    df.loc[m_exc, "tier"] += "L2超额"
    df.loc[m_lim, "tier"] += "L3涨跌停"
    df["is_limit"] = m_lim

    ev = df[df["tier"] != ""].copy()
    ev["tier"] = ev["tier"].str.strip()
    ev = ev.reset_index()

    cols = [
        "date", "tier", "close", "adjclose", "ret", "ret_bench", "excess",
        "volume", "vol_ratio", "amount", "is_limit", "fwd5",
    ]
    ev = ev[cols]
    ev["ret"] = (ev["ret"] * 100).round(2)
    ev["ret_bench"] = (ev["ret_bench"] * 100).round(2)
    ev["excess"] = (ev["excess"] * 100).round(2)
    ev["vol_ratio"] = ev["vol_ratio"].round(2)
    ev["fwd5"] = (ev["fwd5"] * 100).round(2)
    ev["close"] = ev["close"].round(3)
    ev["adjclose"] = ev["adjclose"].round(4)

    ev.to_csv(OUT, index=False, encoding="utf-8-sig")

    print(f"\n事件总数: {len(ev)}")
    print("分档:")
    for t in ["L1绝对", "L2超额", "L3涨跌停"]:
        print(f"  {t}: {df['tier'].str.contains(t).sum()}")
    print("\n按年分布:")
    yr = ev.assign(year=ev["date"].str[:4]).groupby("year").size()
    for y, n in yr.items():
        print(f"  {y}: {n}", end="   ")
    print("\n\n最近 25 条:")
    print(ev.tail(25).to_string(index=False))
    print(f"\n已写入 {OUT}")


if __name__ == "__main__":
    main()
