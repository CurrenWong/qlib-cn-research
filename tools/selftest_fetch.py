"""`fetch_stock_prices.py` / `fetch_sw_industry.py` 的自检（离线优先，网络结果落缓存）。

## 为什么需要
抓数据的脚本「跑通了」和「抓对了」是两件事。这里的每一项都对应一个**真踩过的坑**：

| # | 检查 | 防的是哪个坑 |
|---|---|---|
| 1 | `chunk_by_row_budget` 行数预算 | Tushare `pro.daily` 单次 6000 **行**上限，按只数切批会超 |
| 2 | `trading_day_count` 用本地日历 | 按 250 天/年估算会让每批只数偏大 → 截断 |
| 3 | 复权纯数学（送转股当天收益应为 0） | `close_hfq = close_qfq × factor` 把因子**平方**（v1 真 bug） |
| 4 | Tushare 路径注入假数据 | `ffill/bfill` 不分组 → 上一只票的因子串到下一只 |
| 5 | 腾讯多年度分页连续性 | 单次 640 根上限，按年切片漏年/漏月 |
| 6 | 已退市股能取到历史 | 只测活票 → 退市股静默返回空 |
| 7 | 降级路径（不复权 × 本地因子）与腾讯前复权同口径 | WAF 501 时降级算错基准 |

## 用法
```cmd
cd /d D:\\Project\\qlib
.venv\\Scripts\\python.exe tools\\selftest_fetch.py            :: 默认：离线项全跑 + 网络项走缓存
.venv\\Scripts\\python.exe tools\\selftest_fetch.py --online   :: 强制重新联网抓（会慢）
.venv\\Scripts\\python.exe tools\\selftest_fetch.py --offline  :: 只跑离线项
```
退出码：0 全过；2 有失败项。

## 网络项为什么要缓存
腾讯 fqkline 对连续请求回 **HTTP 501**（WAF 限频）。早期版本一次自检发 40+ 个请求，
退避重试直接把脚本拖到 10 分钟以上还没跑完。现在：
- 请求间强制 1.2s 间隔，501 只退避 10/20s 两次就放弃；
- **抓到的结果落 `tools/_cache/*.parquet`**，重跑直接读盘 → 自检常在 5s 内完成。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fetch_stock_prices as FSP  # noqa: E402
from tushare_common import (  # noqa: E402
    chunk_by_row_budget,
    load_qlib_series,
    qlib_to_ts_code,
    trading_day_count,
)

CACHE = HERE / "_cache"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))
    return ok


def cached(symbol: str, since: str, until: str, allow_qfq: bool = True) -> pd.DataFrame:
    """带磁盘缓存的 `fetch_tencent_one`（--online 时不读缓存）。"""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = f"tx_{symbol}_{since}_{until}_{'qfq' if allow_qfq else 'raw'}.parquet"
    f = CACHE / key
    if not ONLINE and f.exists():
        df = pd.read_parquet(f)
        print(f"    （缓存 {f.name}，{len(df)} 行）")
        return df
    t0 = time.time()
    df = FSP.fetch_tencent_one(symbol, since, until, allow_qfq=allow_qfq)
    print(f"    （联网 {symbol} → {len(df)} 行，{time.time()-t0:.1f}s）")
    if not df.empty:
        df.to_parquet(f, index=False)
    return df


# ------------------------------------------------------------------ 1 行数预算


def t1_row_budget() -> None:
    print("\n=== 1. chunk_by_row_budget 行数预算（Tushare 6000 行上限）===")
    cases = [(243, 6000, 1000), (800, 6000, 1000), (200, 2000, 1000)]
    for rpi, limit, n in cases:
        batches = chunk_by_row_budget([f"S{i}" for i in range(n)], rpi, limit)
        worst = max(len(b) * rpi for b in batches)
        total = sum(len(b) for b in batches)
        check(f"rows_per_item={rpi} limit={limit} n={n}",
              worst <= limit and total == n,
              f"{len(batches)} 批 / 单批最坏 {worst} 行 / 合计 {total} 只")


# ------------------------------------------------------------------ 2 交易日数


def t2_trading_days() -> None:
    print("\n=== 2. trading_day_count（走本地 qlib 日历）===")
    n2024 = trading_day_count("2024-01-01", "2024-12-31")
    check("2024 全年交易日 242~245", 240 <= n2024 <= 246, f"实际 {n2024}")
    n_full = trading_day_count("2020-01-01", "2026-11-12")
    check("2020~2026.11 交易日 1600~1700", 1600 <= n_full <= 1700, f"实际 {n_full}")


# ------------------------------------------------------------------ 3 复权数学


def t3_adj_math() -> None:
    print("\n=== 3. 复权纯数学（10 送 10，送转当天真实收益应为 0%）===")
    raw = np.array([10.0, 11.0, 5.5])
    fac = np.array([1.0, 1.0, 2.0])
    qfq = raw * fac / fac[-1]
    hfq = raw * fac / fac[0]
    # v1 的错误写法：用 qfq 再乘一次 factor → 因子被平方
    wrong = qfq * fac
    print(f"    close_raw={raw.tolist()}  factor={fac.tolist()}")
    print(f"    close_qfq={qfq.tolist()}  close_hfq={hfq.tolist()}")
    print(f"    错误写法 qfq×factor={wrong.tolist()} → 日收益 {wrong[2]/wrong[1]-1:+.2%}")
    check("qfq 抹平送转跳空", abs(qfq[2] / qfq[1] - 1) < 1e-9,
          f"送转日收益 {qfq[2]/qfq[1]-1:+.4%}")
    check("hfq 抹平送转跳空", abs(hfq[2] / hfq[1] - 1) < 1e-9,
          f"送转日收益 {hfq[2]/hfq[1]-1:+.4%}")
    check("v1 的 qfq×factor 确实是错的", abs(wrong[2] / wrong[1] - 1) > 0.1,
          "（回归保护：以后谁再写成平方，这行会提醒）")


# ------------------------------------------------------------------ 4 Tushare 路径


class _FakePro:
    """假 Tushare 客户端：只实现自检要用的 `daily` / `adj_factor`。

    两只票的 factor **基准不同**（A 从 1 起、B 从 2 起），一旦 `ffill/bfill`
    没按股票分组，就会互相串值。

    支持两种调用方式：
      - `daily(trade_date=...)`  ← 默认的按交易日批量
      - `daily(ts_code="A,B", start_date=..., end_date=...)` ← 按代码
    """

    DAILY = pd.DataFrame({
        "ts_code": ["600000.SH"] * 3 + ["000001.SZ"] * 3,
        "trade_date": ["20240102", "20240103", "20240104"] * 2,
        "open": [10.0, 11.0, 5.5, 20.0, 21.0, 10.5],
        "high": [10.0, 11.0, 5.5, 20.0, 21.0, 10.5],
        "low": [10.0, 11.0, 5.5, 20.0, 21.0, 10.5],
        "close": [10.0, 11.0, 5.5, 20.0, 21.0, 10.5],
        "vol": [100.0] * 6,
    })
    FAC = pd.DataFrame({
        "ts_code": ["600000.SH"] * 3 + ["000001.SZ"] * 3,
        "trade_date": ["20240102", "20240103", "20240104"] * 2,
        "adj_factor": [1.0, 1.0, 2.0, 2.0, 2.0, 4.0],
    })

    @staticmethod
    def _pick(df: pd.DataFrame, ts_code=None, start_date=None, end_date=None,
              trade_date=None) -> pd.DataFrame:
        out = df
        if trade_date:
            out = out[out["trade_date"] == trade_date]
        if ts_code:
            codes = ts_code.split(",")
            out = out[out["ts_code"].isin(codes)]
        if start_date:
            out = out[out["trade_date"] >= start_date]
        if end_date:
            out = out[out["trade_date"] <= end_date]
        return out.copy()

    def daily(self, ts_code=None, start_date=None, end_date=None, trade_date=None, **kw):
        return self._pick(self.DAILY, ts_code, start_date, end_date, trade_date)

    def adj_factor(self, ts_code=None, start_date=None, end_date=None, trade_date=None, **kw):
        return self._pick(self.FAC, ts_code, start_date, end_date, trade_date)


def t4_tushare_path() -> None:
    print("\n=== 4. fetch_prices_tushare 注入假数据（跨股票 ffill 串值）===")
    try:
        df = FSP.fetch_prices_tushare(["SH600000", "SZ000001"], "2024-01-02", "2024-01-04",
                                     _FakePro())
    except Exception as e:  # noqa: BLE001
        check("Tushare 路径可跑通", False, f"{type(e).__name__}: {e}")
        return
    check("Tushare 路径可跑通", not df.empty, f"{len(df)} 行 / {df['qlib_symbol'].nunique()} 只")
    if df.empty:
        return

    bad = []
    for sym, g in df.groupby("qlib_symbol"):
        g = g.sort_values("trade_date")
        # 送转当天（第 3 行）前复权日收益应为 0
        r = g["close_qfq"].iloc[2] / g["close_qfq"].iloc[1] - 1
        r_h = g["close_hfq"].iloc[2] / g["close_hfq"].iloc[1] - 1
        # 前复权基准=末日 → qfq 末日 == 不复权末日
        base_q = abs(g["close_qfq"].iloc[-1] - g["close"].iloc[-1])
        # 后复权基准=首日 → hfq 首日 == 不复权首日
        base_h = abs(g["close_hfq"].iloc[0] - g["close"].iloc[0])
        if abs(r) > 1e-9 or abs(r_h) > 1e-9 or base_q > 1e-9 or base_h > 1e-9:
            bad.append(f"{sym}(qfq日收益{r:+.2%} hfq日收益{r_h:+.2%} "
                       f"末基准差{base_q:.4f} 首基准差{base_h:.4f})")
    check("每只票的复权基准/收益率各自正确", not bad, "; ".join(bad) or "2 只票均通过")

    # 因子串值检测：A 的 factor 只应是 1/1/2，B 是 2/2/4
    fa = df[df["qlib_symbol"] == "SH600000"]["factor"].tolist()
    fb = df[df["qlib_symbol"] == "SZ000001"]["factor"].tolist()
    check("A 的因子未被 B 污染", fa == [1.0, 1.0, 2.0], f"{fa}")
    check("B 的因子保持自身基准", fb == [2.0, 2.0, 4.0], f"{fb}")


# ------------------------------------------------------------------ 5 腾讯分页


def t5_tencent_paging() -> None:
    print("\n=== 5. 腾讯多年度分页连续性（SH600519, 2020-01-01~2026-11-12）===")
    df = cached("SH600519", "2020-01-01", "2026-11-12")
    if df.empty or not check("取到数据", not df.empty):
        return
    d = pd.to_datetime(df["trade_date"]).sort_values()
    print(f"    {len(df)} 行 | {d.min().date()} ~ {d.max().date()} | "
          f"每年 {df.groupby(d.dt.year).size().to_dict()}")
    check("区间覆盖完整（首尾日期对得上）",
          str(d.min().date()) <= "2020-01-10" and str(d.max().date()) >= "2026-10-31",
          f"{d.min().date()} ~ {d.max().date()}")
    check("无重复交易日", d.duplicated().sum() == 0, f"重复 {int(d.duplicated().sum())} 条")
    check("相邻间隔 ≤ 20 天（长假容忍）", d.diff().dt.days.max() <= 20,
          f"最大间隔 {d.diff().dt.days.max()} 天")

    # 与本地 bin 的实际交易日对齐（本地覆盖到哪天就比到哪天）
    try:
        local = load_qlib_series("SH600519", "close")
        local = local[(local.index >= d.min()) & (local.index <= d.max())]
        missing = local.index.difference(pd.DatetimeIndex(d))
        extra = pd.DatetimeIndex(d).difference(local.index)
        check("腾讯日期覆盖本地全部交易日", len(missing) == 0,
              f"本地 {len(local)} 天 / 缺 {len(missing)} / 多 {len(extra)}"
              + (f" 缺例 {[str(x.date()) for x in missing[:3]]}" if len(missing) else ""))
    except FileNotFoundError as e:
        check("本地 bin 可读", False, str(e))


# ------------------------------------------------------------------ 6 等额复权口径


def t6_bases() -> None:
    print("\n=== 6. 腾讯三序列的等额复权关系（vfq/hfq 都是 raw ± 累计分红）===")
    df = cached("SH600519", "2024-01-01", "2026-11-12")
    if df.empty or not check("取到数据", not df.empty):
        return
    for c in ["close", "close_qfq", "close_hfq"]:
        print(f"    {c:<10} 首={df[c].iloc[0]:>12.4f} 末={df[c].iloc[-1]:>12.4f}")

    check("前复权基准=末日（qfq 末值 == 不复权末值）",
          abs(df["close_qfq"].iloc[-1] - df["close"].iloc[-1]) < 1e-4,
          f"差 {abs(df['close_qfq'].iloc[-1]-df['close'].iloc[-1]):.6f}")
    check("前复权 ≤ 不复权（分红只往下减）", bool((df["close_qfq"] <= df["close"] + 1e-9).all()))
    check("后复权 ≥ 不复权（分红只往上加）", bool((df["close_hfq"] >= df["close"] - 1e-9).all()))

    # 核心不变式：raw − qfq 必须是「分段常数的阶梯」，只在除权日跳变
    off = df["close"] - df["close_qfq"]
    step = off.diff().abs()
    n_step = int((step > 0.01).sum())
    max_noise = step[step <= 0.01].max() if (step <= 0.01).any() else 0.0
    print(f"    raw-qfq 范围 {off.min():.4f} ~ {off.max():.4f} | "
          f"跳变(>0.01元) {n_step} 天 | 非跳变日最大抖动 {max_noise:.6f}")
    check("raw-qfq 是阶梯（非跳变日抖动 < 0.01 元）", max_noise < 0.01,
          f"{max_noise:.6f}")
    check("跳变次数 = 分红次数（2 年 5 次以内）", 0 < n_step <= 8, f"{n_step} 次")
    check("阶梯只降不升（累计分红单调增 → 价差单调减）",
          bool((off.diff().dropna() <= 0.01).all()),
          f"最大 Δ {off.diff().max():+.4f}")

    # hfq 由 qfq 的阶梯反推（derive_hfq），必须满足：乘权、除权日连续、能复原 qfq
    r_q = df["close_qfq"].pct_change()
    r_h = df["close_hfq"].pct_change()
    r_r = df["close"].pct_change()
    fac = df["factor"]
    f_step = fac.pct_change().abs()
    print(f"    factor 范围 {fac.min():.6f} ~ {fac.max():.6f} | "
          f"跳变日 {int((f_step > 1e-9).sum())}")
    check("factor 是乘权因子（只在除权日跳变）", int((f_step > 1e-9).sum()) == n_step,
          f"{int((f_step > 1e-9).sum())} 天跳变 vs {n_step} 次分红")
    is_ex = step > 0.01
    d_h = (r_h - r_r).dropna()
    d_h_plain = d_h[~d_h.index.isin(df.index[is_ex])]
    check("非除权日 hfq 收益 == 不复权收益（乘权平移不改收益）",
          d_h_plain.abs().max() < 1e-9, f"最大差 {d_h_plain.abs().max():.2e}")
    dev_ex = d_h[d_h.index.isin(df.index[is_ex])]
    check("除权日 hfq 收益 > 不复权收益（分红被加回）",
          bool(len(dev_ex) > 0 and (dev_ex > 0).all()),
          f"{len(dev_ex)} 个除权日，最小差额 {dev_ex.min()*100:.2f}pct" if len(dev_ex) else "无")
    # 用推出来的 factor 重建前复权，应能大体复原源序列。
    # 注意：源 qfq 是**等额**口径、factor 是**乘权**口径，两者数学上就不等价，
    # 差异随累计分红率放大（600519 两年 5 次分红 → 约 1.7%），这是口径差不是 bug；
    # 反过来，若 factor 被写错（比如因子平方），偏离会直接到几十个百分点。
    rebuilt = df["close"] * fac / fac.iloc[-1]
    dev_rebuild = (rebuilt / df["close_qfq"] - 1).abs()
    print(f"    重建 qfq vs 源 qfq：中位 {dev_rebuild.median()*100:.4f}% "
          f"最大 {dev_rebuild.max()*100:.4f}%（等额 vs 乘权的口径差）")
    check("用 factor 重建 qfq 与源序列同量级（偏离 < 2%）", dev_rebuild.max() < 0.02,
          f"最大 {dev_rebuild.max()*100:.4f}%")
    gap_ex = (r_q - r_r).abs().loc[df.index[is_ex]]
    check("除权日前复权收益与不复权收益明显分叉（分红被加回）",
          bool(len(gap_ex) > 0 and gap_ex.min() > 0.005),
          f"{len(gap_ex)} 个除权日，最小分叉 {gap_ex.min()*100:.2f}pct" if len(gap_ex) else "无除权日")


# ------------------------------------------------------------------ 7 降级行为


def t7_fallback() -> None:
    print("\n=== 7. 复权接口不可用时只取不复权（不编造复权序列）===")
    r = cached("SH600519", "2024-01-01", "2026-11-12", allow_qfq=False)
    if not check("降级路径取到数据", not r.empty):
        return
    missing = [c for c in ["close_qfq", "close_hfq", "factor", "div_offset"]
               if c not in r.columns]
    check("复权列存在但为空", not missing, f"缺列 {missing}")
    if not missing:
        check("复权列全为 NaN（不拿本地因子瞎凑）",
              bool(r[["close_qfq", "close_hfq", "factor"]].isna().all().all()))
    check("不复权价非空", bool(r["close"].notna().all()), f"{len(r)} 行")
    check("不复权价与正常路径逐日一致",
          _same_raw("SH600519", r), "对比正常路径的 close")


def _same_raw(symbol: str, degraded: pd.DataFrame) -> bool:
    full = cached(symbol, "2024-01-01", "2026-11-12")
    if full.empty:
        return False
    j = (degraded.set_index("trade_date")["close"]
         .to_frame("d").join(full.set_index("trade_date")["close"].to_frame("f"))).dropna()
    return bool(len(j) > 50 and (j["d"] - j["f"]).abs().max() < 1e-9)



# ------------------------------------------------------------------ 8 退市股


def t8_delisted() -> None:
    print("\n=== 8. 已退市股 SH600001（邯郸钢铁，1998 上市 / 2009 退市）===")
    df = cached("SH600001", "1998-01-01", "2010-12-31")
    if not check("取到历史数据", not df.empty):
        return
    d = pd.to_datetime(df["trade_date"]).sort_values()
    print(f"    {len(df)} 行 | {d.min().date()} ~ {d.max().date()}")
    check("最后交易日落在 2009 年（退市年）",
          d.max().year == 2009, f"{d.max().date()}")
    check("首日落在 1998 年", d.min().year in (1998, 1999), f"{d.min().date()}")


# ------------------------------------------------------------------ 9 真实 Tushare


def t9_tushare_real() -> None:
    """有 token 且有权限时，才真跑一次 Tushare 路径并和腾讯对账。

    没有 token / 没有接口权限都只是**跳过**，不算失败——
    否则没 token 的机器上自检永远红，倒逼别人去改断言。
    """
    print("\n=== 9. Tushare 真实接口（--with-tushare）===")
    from tushare_common import call_with_retry, resolve_token

    try:
        tok = resolve_token()
    except RuntimeError as e:
        print(f"    跳过：{e}")
        return
    import tushare as ts

    pro = ts.pro_api(tok)
    try:
        df = call_with_retry(pro.daily, ts_code="600519.SH",
                             start_date="20261101", end_date="20261112", retries=1)
    except RuntimeError as e:
        msg = str(e)
        if "权限" in msg or "没有接口" in msg or "积分" in msg:
            print("    跳过：该 token 认证通过但**没有 daily 权限**（账号积分为 0）。")
            print("          → Tushare 路径只能靠第 4 段（注入假 pro）验证；")
            print("          → 真行情用 --source tencent，或先跑 tools/check_tushare.py 体检。")
            return
        check("Tushare 真实 daily 可调", False, msg[:120])
        return
    if not check("Tushare 真实 daily 可调", df is not None and not df.empty,
                 f"{0 if df is None else len(df)} 行"):
        return

    # 有权限就顺手和腾讯对账：同一区间、同一只票，不复权收盘价应逐日相等
    tx = cached("SH600519", "2026-11-01", "2026-11-12")
    if tx.empty:
        print("    （腾讯侧没数据，跳过对账）")
        return
    ts_df = df.copy()
    ts_df["trade_date"] = pd.to_datetime(ts_df["trade_date"], format="%Y%m%d")
    j = (ts_df.set_index("trade_date")["close"].to_frame("ts")
         .join(tx.set_index("trade_date")["close"].to_frame("tx"))).dropna()
    if j.empty:
        check("与腾讯对账有重叠", False, "无重叠交易日")
        return
    dev = (j["ts"] - j["tx"]).abs().max()
    check(f"Tushare 不复权收盘价 == 腾讯（{len(j)} 天重叠）", dev < 1e-6, f"最大差 {dev:.6f}")


# ------------------------------------------------------------------ main


def main() -> int:
    global ONLINE, OFFLINE
    ap = argparse.ArgumentParser(description="fetch_stock_prices 自检")
    ap.add_argument("--online", action="store_true", help="忽略缓存，强制重新联网")
    ap.add_argument("--offline", action="store_true", help="只跑离线项（无网络）")
    ap.add_argument("--with-tushare", action="store_true",
                    help="额外真跑一段 Tushare（需 token 且账号有 daily 权限，否则自动跳过）")
    args = ap.parse_args()
    ONLINE, OFFLINE = args.online, args.offline

    t0 = time.time()
    t1_row_budget()
    t2_trading_days()
    t3_adj_math()
    t4_tushare_path()
    if not OFFLINE:
        t5_tencent_paging()
        t6_bases()
        t7_fallback()
        t8_delisted()
    else:
        print("\n=== 5~8. 网络项已跳过（--offline）===")
    if args.with_tushare:
        t9_tushare_real()
    else:
        print("\n=== 9. Tushare 真实接口已跳过（加 --with-tushare 才跑）===")

    failed = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 60)
    print(f"共 {len(RESULTS)} 项，失败 {len(failed)} 项，用时 {time.time()-t0:.1f}s")
    for name, _, detail in failed:
        print(f"  ❌ {name} — {detail}")
    print("结论：" + ("✅ 全部通过" if not failed else "❌ 有失败项"))
    return 0 if not failed else 2


ONLINE = False
OFFLINE = False

if __name__ == "__main__":
    raise SystemExit(main())
