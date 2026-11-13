"""校验抓下来的行情与本地 qlib bin 是否对得上。

## 为什么要有这个脚本
`fetch_stock_prices.py` 抓回来的数据要能拿去和本地 `qlib_data/cn_data_2026` 交叉核对，
否则「抓到了」不等于「能用」。这个脚本做三层核对：

| 层 | 比什么 | 通过标准 |
|---|---|---|
| ① 原始价 | `ql_close / ql_factor` vs 腾讯不复权 close | 比值恒定 → 两源原始价一致 |
| ② 收益率 | qlib 日收益 vs 腾讯**不复权**日收益 | 贴近不复权 → 说明 qlib 的 factor 只在除权日跳变 |
| ③ 前复权 | qlib 日收益 vs 腾讯**前复权**日收益 | 偏离量级应与 AGENTS.md §6.4 记录的一致（约 0.06pct） |

## 实测结论（2026-11-13，区间 2024-01-01~2026-11-12）
```
SZ000001  原始价比值 MAD 0.000000 | qlib vs 腾讯不复权 日收益差均值 0.029pct（最大 6.73pct）
SH600519  原始价比值 MAD 0.000000 | qlib vs 腾讯不复权 日收益差均值 0.014pct（最大 2.28pct）
SH600418  原始价比值 MAD 0.000000 | qlib vs 腾讯不复权 日收益差均值 0.002pct（最大 0.09pct）
```
→ **原始价两源逐日完全一致**（最大偏离 0.0000%），
→ 与腾讯前复权的日收益差 0.05~0.11pct，和 AGENTS.md §6.4 记录的
「qlib 前复权 vs 新浪前复权 平均绝对差 0.062pct」同一量级，**不是新 bug**。

## 用法
```cmd
cd /d D:\\Project\\qlib
.venv\\Scripts\\python.exe tools\\verify_fetched_prices.py
.venv\\Scripts\\python.exe tools\\verify_fetched_prices.py --file data\\prices\\daily_tencent.parquet
```
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tushare_common import load_qlib_series  # noqa: E402

QLIB_ROOT = HERE.parent
DEFAULT_FILE = QLIB_ROOT / "data" / "prices" / "daily_tencent.parquet"


def local_series(symbol: str, field: str) -> pd.Series:
    """读本地 qlib bin 的一路字段，按日历对齐（薄封装，实现见 tushare_common）。"""
    return load_qlib_series(symbol, field)


def check_one(symbol: str, g: pd.DataFrame) -> dict:
    ql_close = local_series(symbol, "close")
    ql_fac = local_series(symbol, "factor")

    j = pd.concat([
        g[["close", "close_qfq", "factor"]].rename(columns={
            "close": "tx_raw", "close_qfq": "tx_qfq", "factor": "tx_factor"}),
        ql_close.rename("ql_close"), ql_fac.rename("ql_factor"),
    ], axis=1, join="inner").dropna(subset=["tx_raw", "ql_close", "ql_factor"])

    if len(j) < 30:
        return {"symbol": symbol, "days": len(j), "skip": "重叠不足"}

    # qlib 的 close = 不复权价 × factor（factor 有自己的基准常数 k）
    j["ql_implied_raw"] = j["ql_close"] / j["ql_factor"]
    ratio = j["ql_implied_raw"] / j["tx_raw"]
    rel_dev = ((ratio / ratio.median()) - 1).abs()

    j["ql_r"] = j["ql_close"].pct_change()
    j["tx_raw_r"] = j["tx_raw"].pct_change()
    j["tx_qfq_r"] = j["tx_qfq"].pct_change()
    d_raw = (j["ql_r"] - j["tx_raw_r"]).abs()
    d_qfq = (j["ql_r"] - j["tx_qfq_r"]).abs()

    return {
        "symbol": symbol,
        "days": len(j),
        "start": str(j.index[0].date()),
        "end": str(j.index[-1].date()),
        "raw_ratio_med": ratio.median(),
        "raw_ratio_mad": (ratio - ratio.median()).abs().median(),
        "raw_max_dev_pct": rel_dev.max() * 100,
        "d_raw_mean_pct": d_raw.mean() * 100,
        "d_raw_max_pct": d_raw.max() * 100,
        "d_qfq_mean_pct": d_qfq.mean() * 100,
        "d_qfq_max_pct": d_qfq.max() * 100,
        "d_qfq_corr": j["ql_r"].corr(j["tx_qfq_r"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="校验抓取的行情 vs 本地 qlib bin")
    ap.add_argument("--file", default=str(DEFAULT_FILE))
    ap.add_argument("--max-dev-pct", type=float, default=0.01,
                    help="原始价最大偏离阈值（%%），超过判失败")
    args = ap.parse_args()

    f = Path(args.file)
    if not f.exists():
        print(f"找不到 {f}")
        return 1
    df = pd.read_parquet(f)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    print(f"== 校验 {f} ==")
    print(f"   {len(df):,} 行 | {df['qlib_symbol'].nunique()} 只 | "
          f"{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}")

    rows = []
    for sym, g in df.groupby("qlib_symbol"):
        g = g.set_index("trade_date").sort_index()
        rows.append(check_one(sym, g))

    ok = True
    print(f"\n{'symbol':<11}{'天数':>7}{'原始价比值MAD':>14}{'最大偏离%':>11}"
          f"{'vs不复权均值%':>14}{'vs前复权均值%':>14}{'前复权corr':>11}")
    print("-" * 92)
    for r in rows:
        if "skip" in r:
            print(f"{r['symbol']:<11}{r['days']:>7}  {r['skip']}")
            continue
        flag = ""
        if r["raw_max_dev_pct"] > args.max_dev_pct:
            flag = "  ← 原始价不一致！"
            ok = False
        print(f"{r['symbol']:<11}{r['days']:>7}{r['raw_ratio_mad']:>14.8f}"
              f"{r['raw_max_dev_pct']:>11.4f}{r['d_raw_mean_pct']:>14.4f}"
              f"{r['d_qfq_mean_pct']:>14.4f}{r['d_qfq_corr']:>11.6f}{flag}")

    print("\n判读：")
    print("  · 原始价比值 MAD ≈ 0 → 两源【不复权原始价】逐日完全一致（抓取可信）")
    print("  · vs 不复权 的日收益差  <  vs 前复权 的日收益差")
    print("    → qlib 那条 close 的收益更接近**不复权**序列，不是腾讯的前复权序列；")
    print("      qlib 的 factor 是逐日微漂的（692 天里 632 天在动），**不是乘权因子**，")
    print("      别拿它做乘法复权（要用后复权就用 fetch_stock_prices.derive_hfq 推的 factor）")
    print("  · vs 前复权 的日收益差应在 0.1pct 量级（AGENTS.md §6.4 记录 0.062pct），")
    print("    超过 1pct 才需要排查")

    print(f"\n结论：{'✅ 通过' if ok else '❌ 未通过（原始价对不上）'}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
