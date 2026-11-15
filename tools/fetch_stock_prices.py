"""获取股票历史收盘价（对应图片第 2 段：`pro.daily` 批量抓 + 复权处理）。

## 图片原版的问题
原图这一段基本是**从聊天记录里 OCR 出来的残片**，多处无法运行：

| 原图代码 | 问题 |
|---|---|
| `stk_num = int(6000 / (count * 20) ** 0.99)` | `count` 未定义；且按「只数」切批不是 Tushare 的限制口径 |
| `for i in range(0, len(stock_list), stk_num): ... joined_str = ','.join(stock_list[i:idx_end])` | `idx_end` 未定义；循环体里没真正调用接口 |
| `for j, pro.daily(ts_code=joined_str, start_date=since, end_date=until):` | 语法错误（`for` 后缺赋值） |
| `price_all = pd.concat(price_all)` | 若一次都没成功会 `ValueError: No objects to concatenate` |
| `df[date] = df.index` / `if i == price_all.index[0]:` | OCR 残缺，逻辑不通 |
| `for i, stk in enumerate(stock_list): ... df = df.sort_index()` | 每只股票都重新排序全表，O(N² log N) |
| 复权段没有真正算因子 | 只有一句「pro.daily 是没有复权的，需要复权处理」，实现缺失 |

这里按 Tushare 的真实限制重写：
- `pro.daily` **单次最多 6000 行**（不是 6000 只），所以按「行数预算」切批；
- 复权用 `pro.adj_factor` 正规算：`qfq_close = close * adj_factor / adj_factor_last`；
- 全流程向量化，不用逐只循环。

## 复权口径（重要，别搞混）
| 口径 | 公式 | 用途 |
|---|---|---|
| 不复权 `close` | 原始成交价 | 对账真实成交 |
| 前复权 `close_qfq` | `close * factor / factor[-1]` | 与本项目 `qlib_data/cn_data_2026` 的 `$close` 同口径（AGENTS.md §6.3） |
| 后复权 `close_hfq` | `close * factor` | 长期序列、不受除权影响 |

> 本项目 `cn_data_2026` 的 `close.bin` 是**前复权价**，且与新浪原始价之比恒为 0.4831。
> 想用 Tushare 数据交叉校验时，要比**前复权**列（且注意基准日不同，比的是**收益率**不是绝对价）。

## 用法
```cmd
cd /d <repo>
:: 图片原版（Tushare 行情，需 token）
.venv\\Scripts\\python.exe tools\\fetch_stock_prices.py --source tushare --since 2020-01-01 --until 2026-11-12
:: 免 token 源（腾讯，双域名轮换 + 响应缓存）
.venv\\Scripts\\python.exe tools\\fetch_stock_prices.py --source tencent --since 2020-01-01
:: 只取几只试试 / 放缓节奏 / 被限频中断后接着跑
.venv\\Scripts\\python.exe tools\\fetch_stock_prices.py --source tencent --symbols SH600519,SZ000001 --sleep 3
.venv\\Scripts\\python.exe tools\\fetch_stock_prices.py --source tencent --resume
```

## 产出
```
data\\prices\\daily_<source>.parquet
  qlib_symbol, ts_code, trade_date, open/high/low/close, volume, amount,
  close_qfq, close_hfq, factor, div_offset
  · close       不复权成交价（对账用）
  · close_qfq   前复权（腾讯口径=等额，基准=区间末日）
  · close_hfq   后复权（乘权，由前复权阶梯推出，见 derive_hfq）
  · factor      乘权因子 F（除权日跳变，别拿 qfq/raw 当因子）
  · div_offset  等额口径的累计分红额 = close − close_qfq
```
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tushare_common import (  # noqa: E402
    DAILY_ROW_LIMIT,
    call_with_retry,
    chunk_by_row_budget,
    make_pro,
    to_ts_date,
    ts_code_to_qlib,
    trading_day_count,
    qlib_to_ts_code,
)

HERE = Path(__file__).resolve().parent
QLIB_ROOT = HERE.parent
OUT_DIR = QLIB_ROOT / "data" / "prices"

TENCENT_HOSTS = [
    # (tag, url, 备注)：两个域名是不同的 WAF 策略，互不连坐
    ("ifzq", "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"),
    ("proxy", "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get"),
]
#: 原始 K 线（不认 qfq 参数）的备用端点
TENCENT_RAW_FALLBACK = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
#: 腾讯对连续请求会回 501（WAF 限频），调用之间必须留间隔。
#: 实测：自检连发 ~40 个请求就把整个 IP 打进冷却（连不复权一起 501，持续 10 分钟以上），
#: 所以默认放到 2.5s（≈24 次/分），批量抓全市场时建议再用 --sleep 放缓。
TENCENT_SLEEP = 2.5
#: 首次撞 501 时先整体冷却这么久再试一次
TENCENT_COOLDOWN = 90
TENCENT_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://gu.qq.com/",
}
#: 全局节流：上一次请求的时间戳（秒）
_LAST_CALL = [0.0]
#: 一旦被判限频，后续股票直接走「不复权 + 本地因子」，不再浪费配额
_QFQ_BLOCKED = [False]
#: 本轮已被限频的域名（tag），不再碰
_HOST_BLOCKED: set[str] = set()
#: 响应级缓存目录（同一 param 只抓一次，重跑/补抓都不用再问腾讯）
CACHE_DIR = HERE / "_cache" / "tencent"
#: 是否读写响应缓存（--no-cache 关掉）
USE_CACHE = True

_ONE_DAY = timedelta(days=1)


def _d(s: str):
    """`2024-01-02` → date（腾讯返回的日期都带横杠）。"""
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()

OUT_COLS = ["qlib_symbol", "ts_code", "trade_date", "open", "high", "low", "close",
            "volume", "amount", "close_qfq", "close_hfq", "factor", "div_offset"]


class TencentRateLimited(RuntimeError):
    """腾讯 WAF 限频（HTTP 501）。退避后仍失败才抛，别无限重试。"""


# ------------------------------------------------------------------ 腾讯（免 token）


def _tencent_symbol(symbol: str) -> str:
    """qlib 风格 → 腾讯风格：`SH600519` → `sh600519`。"""
    sym = symbol.strip().lower()
    return ("sh" if sym.startswith("sh") else "sz") + "".join(c for c in sym if c.isdigit())


def _tencent_rows(sym: str, fq: str, start: str, end: str) -> list:
    """取腾讯 K 线：多域名轮换 + 向后翻页。

    ## 端点与翻页
    - `fqkline/get`（web.ifzq）与 `newfqkline/get`（proxy.finance）**参数格式一样**，
      响应里分别是 `qfqday` / `hfqday` / `day`（fq 为空时）；
    - 单次最多 640 根，但两个域名都**只认右边界**：给 `lo..hi` 它会返回 hi 之前 640 根，
      所以按「从 until 往前翻页」抓，直到某页的第一根 ≤ since。

    ## 为什么要有第二个域名
    腾讯的限频是**按域名（WAF 策略）**的：web.ifzq 连续几十个请求就整片 501
    （连不复权一起挂，冷却 10~20 分钟），而 `proxy.finance.qq.com` 同一个时刻**照常返回 200**。
    所以一个域名被判限频就切下一个，并记住它这一轮别再碰。

    ⚠ `web.ifzq` 的 `kline/kline`（纯不复权）参数里**不能有 fq 位**，所以单独一个 URL。
    """
    import requests

    errors = []
    for tag, url in TENCENT_HOSTS:
        if tag in _HOST_BLOCKED:
            continue
        try:
            return _paged(requests, sym, fq, start, end, url, tag)
        except TencentRateLimited as e:
            _HOST_BLOCKED.add(tag)
            errors.append(f"{tag}: {e}")
            print(f"      ⚠ 域名 {tag} 被限频，切换下一个域名（本轮到 {tag} 不再请求）")
    raise TencentRateLimited("所有腾讯域名都失败: " + " | ".join(errors) if errors
                             else "没有可用域名")


def _paged(requests, sym: str, fq: str, start: str, end: str,
           url: str, tag: str, page: int = 640, max_pages: int = 20) -> list:
    """向后翻页抓 [start, end]，返回按日期升序的原始数组。"""
    rows: list = []
    hi = end
    for _ in range(max_pages):
        param = f"{sym},day,{start},{hi},{page},{fq}"
        got = _tencent_get(requests, U=sym, param=param, url=url, tag=tag, fq=fq)
        if not got:
            break
        rows = got + rows
        if got[0][0] <= start:
            break
        # 上一页第一天再往前一天，作为下一页的右边界
        hi = (_d(got[0][0]) - _ONE_DAY).strftime("%Y-%m-%d")
    return [r for r in rows if start <= r[0] <= end]


def _throttle() -> None:
    """两次腾讯请求之间至少隔 TENCENT_SLEEP 秒。"""
    wait = TENCENT_SLEEP - (time.time() - _LAST_CALL[0])
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL[0] = time.time()


def _cache_path(param: str) -> Path:
    import hashlib

    return CACHE_DIR / (hashlib.md5(param.encode("utf-8")).hexdigest()[:16] + ".json")


def _tencent_get(requests, U: str, param: str, url: str, tag: str, fq: str,
                 retries: int = 2) -> list:
    """单次腾讯请求：命中响应缓存则不发网络；501 只冷却重试一次，仍失败就抛。

    被限频时**不要逐个股票硬试**——限频按域名算，继续试只会把冷却期拖长。
    这里抛 `TencentRateLimited`，由 `_tencent_rows` 切域名，切完都不行就让整轮中止。
    """
    key = f"{fq}day" if fq else "day"

    cp = _cache_path(f"{tag}|{param}")
    if USE_CACHE and cp.exists():
        try:
            return (json.loads(cp.read_text(encoding="utf-8")).get("data") or {}).get(U, {}).get(key) or []
        except (OSError, ValueError):
            pass  # 缓存坏了就重新抓

    last_err = None
    for attempt in range(1, retries + 1):
        _throttle()
        try:
            r = requests.get(url, params={"param": param}, headers=TENCENT_UA, timeout=30)
            if r.status_code == 501:
                raise TencentRateLimited(f"{tag} HTTP 501（WAF 限频）")
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            j = r.json()
            if j.get("code") not in (0, None):
                raise RuntimeError(f"返回 code={j.get('code')} msg={j.get('msg')}")
            if USE_CACHE:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cp.write_text(json.dumps(j), encoding="utf-8")
            sub = (j.get("data") or {}).get(U) or {}
            return sub.get(key) or []
        except TencentRateLimited as e:
            # 501 是「域名级」的，冷却期 10~20 分钟，这里等 90s 没意义 → 立刻交给上层换域名
            raise
 
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt == retries:
                break
            wait = 2 * attempt
            print(f"      {tag} 请求失败（第 {attempt}/{retries} 次）: {type(e).__name__}: "
                  f"{str(e)[:60]} → {wait}s 后重试")
            time.sleep(wait)
    raise TencentRateLimited(f"{tag} 请求失败: {type(last_err).__name__}: {last_err}")


def _mk_kline(rows: list) -> pd.DataFrame:
    """腾讯 K 线数组 → DataFrame（列序：日期/开/收/高/低/量）。"""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).iloc[:, :6]
    df.columns = ["trade_date", "open", "close", "high", "low", "volume"]
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    for c in ["open", "close", "high", "low", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.drop_duplicates("trade_date").sort_values("trade_date").reset_index(drop=True)


def fetch_tencent_one(symbol: str, since: str, until: str, allow_qfq: bool = True) -> pd.DataFrame:
    """腾讯取单只股票：不复权价 + 前复权价，后复权由 `derive_hfq` 推出。

    ## 关键结论（2026-11-13 实测，别再踩）
    腾讯的 **qfq 是「等额复权」**（=`不复权价 − 累计分红`），不是乘权：

        raw − qfq  在两次除权之间**恒定**（600519 两年 692 个交易日里只有 5 天跳变，
                   恰好等于 5 次分红：30.876 / 23.882 / 27.600 / 23.957 / 28.024 元）

    所以 **`factor = qfq / raw` 是错的**：那个比值会随价格漂移（涨的时候天天变），
    拿它去算 `close_hfq` 会凭空造出 0.02%~0.7% 的波动（本脚本 v2 就是这么错的，
    自检里「hfq 日波动 10.03% > raw 9.29%」就是它露的马脚）。
    腾讯自己的 `hfq` 接口同样对不上它的 raw/qfq（见 `derive_hfq` 的说明），也已弃用。
    正确做法：**用 qfq 的阶梯还原每次分红，再乘权推出 hfq**（`derive_hfq`）。

    Parameters
    ----------
    allow_qfq : False 或已探测到 WAF 拦截时只取不复权价，复权列留 NaN。
                宁可留空，也不用错误口径编一条复权序列。
    """
    sym = _tencent_symbol(symbol)

    qfq = pd.DataFrame()
    if allow_qfq and not _QFQ_BLOCKED[0]:
        # 限频异常直接往上抛：宁可整轮中止（再 --resume），也不要一半有复权一半没有
        qfq = _mk_kline(_tencent_rows(sym, "qfq", since, until))

    raw = _mk_kline(_tencent_rows(sym, "", since, until))
    if raw.empty:
        return pd.DataFrame()

    out = raw.copy()
    out["qlib_symbol"] = symbol
    out["amount"] = np.nan

    if qfq.empty:
        out["close_qfq"] = np.nan
        out["close_hfq"] = np.nan
        out["factor"] = np.nan
        out["div_offset"] = np.nan
        return out

    out = out.merge(
        qfq[["trade_date", "close"]].rename(columns={"close": "close_qfq"}),
        on="trade_date", how="left",
    )
    return derive_hfq(out)



def derive_hfq(out: pd.DataFrame) -> pd.DataFrame:
    """从「不复权 + 前复权（等额口径）」反推**乘权**后复权序列 + 乘权因子。

    ## 为什么不直接用腾讯的 hfq 接口
    实测（600519，2024-01~2026-11）：腾讯 `hfq` 序列和它自家的 `raw`/`qfq` **对不上**——
    非除权日 hfq 与 raw 的日收益差中位 **0.1%**、最大 **1.6%**，
    与 qfq 的日收益差最大 **2.1%**。也就是说那一路序列既不是乘权也不是等额，
    拿来当"后复权"会凭空造出波动。**弃用**。

    ## 这里怎么算
    腾讯 qfq 是等额的（`raw − qfq` = 累计分红，分段恒定），所以能精确还原每次分红：

        d_i = off(t⁺) 前后的差值        （本次每股分红额）
        除权比例 = d_i / 前一日不复权价
        F(t) = Π_{i≤t} 1 / (1 − 除权比例)   ← 乘权因子（除权日跳变，其余恒定）
        close_hfq = close × F(t)             ← 除权日连续（不复权价跌多少，因子补多少）

    与 Tushare 的 `adj_factor` 同语义（基准不同，收益率一致）。
    """
    off = out["close"] - out["close_qfq"]
    # 分红额：off 在除权日**变小**（累计未来分红减少），所以取负 diff
    div = (-off.diff()).fillna(0.0)
    div = div.where(div > 1e-6, 0.0)
    prev = out["close"].shift(1)
    ratio = (div / prev).fillna(0.0).clip(upper=0.9)   # 防御：异常值不让因子爆掉
    f = (1.0 / (1.0 - ratio)).cumprod()
    out["factor"] = f
    out["close_hfq"] = out["close"] * f
    out["div_offset"] = off
    return out




# ------------------------------------------------------------------ Tushare


def _calendar_days(since: str, until: str) -> list[str]:
    """取 [since, until] 里的交易日：优先本地日历，覆盖不到就退化到「工作日」。

    ⚠ 本地 `calendars/day.txt` 只到数据更新的那天（本项目实测到 2026-10-30），
    抓「最近几天」时区间会完全落在日历之外 → 必须退化，否则一天都抓不到（真踩过）。
    退化用周一~周五，节假日自然由 Tushare 返回空表兜住。
    """
    from tushare_common import CALENDAR_FILE

    try:
        cal = CALENDAR_FILE.read_text(encoding="utf-8").split()
    except OSError:
        cal = []
    days = [d for d in cal if since <= d <= until]
    if days:
        return days

    from datetime import date, timedelta

    d0 = _d(since)
    d1 = _d(until)
    out = []
    d = d0
    while d <= d1:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    print(f"    （本地日历不覆盖 {since}~{until}，退化为工作日：{len(out)} 天）")
    return out


def fetch_prices_tushare(symbols: list[str], since: str, until: str, pro,
                         batch: str = "date", max_days: int = 60) -> pd.DataFrame:
    """Tushare `pro.daily` 抓 + `pro.adj_factor` 复权。

    ## 两种批量方式（默认按「交易日」）
    | 方式 | 调用 | 实测（2026-11-13，120 积分档） |
    |---|---|---|
    | `ts_code="600519.SH,000001.SZ"` | 一次多只 | ❌ **静默返回空表**（原图那套写法就踩这个） |
    | `trade_date="20261110"` | 一次一天 | ✅ 一次拿全市场 **5573 行**（<6000 上限） |

    所以默认 `batch="date"`：按交易日逐天抓，再筛出要的标的。
    单次 6000 行上限天然满足（一天全市场也就 5~6 千行），且**调用数 = 交易日数**，
    不管要多少只股票——想抓 5000 只和抓 5 只的成本一样。

    `batch="code"` 保留给「单只票 + 长区间」的场景（多只时会被合并成逗号串，慎用）。

    `max_days` 是防呆：低积分档 `daily` 有分钟级限频，一天一调不能一次排 600 天。
    """
    ts_since, ts_until = to_ts_date(since), to_ts_date(until)
    want = {s.upper() for s in symbols}

    if batch == "date":
        days = _calendar_days(since, until)
        if len(days) > max_days:
            print(f"    ⚠ 区间内 {len(days)} 个交易日 > max_days={max_days}，"
                  f"只抓最近 {max_days} 天（要更多请显式调大 --ts-max-days）")
            days = days[-max_days:]
        print(f"    按交易日抓：{len(days)} 天 × 1 次调用（每天全市场）")
        frames = []
        for i, d in enumerate(days, 1):
            df = call_with_retry(pro.daily, trade_date=to_ts_date(d))
            if df is None or df.empty:
                print(f"    [{i}/{len(days)}] {d} 空")
                continue
            df = df.copy()
            df["ts_code"] = df["ts_code"].astype(str).str.strip()
            frames.append(df)
            if i % 5 == 0 or i == len(days) or len(days) <= 10:
                print(f"    [{i}/{len(days)}] {d} → {len(df)} 行（全市场）")
        if not frames:
            return pd.DataFrame()
        price = pd.concat(frames, ignore_index=True)
        price["qlib_symbol"] = price["ts_code"].map(ts_code_to_qlib)
        price = price[price["qlib_symbol"].isin(want)]
        print(f"    筛出目标 {price['qlib_symbol'].nunique()} 只 / {len(price)} 行")
        fac_batches = [sorted(price["qlib_symbol"].unique())]
    else:
        n_days = trading_day_count(since, until)
        batches = chunk_by_row_budget(symbols, rows_per_item=n_days, limit=DAILY_ROW_LIMIT)
        print(f"区间 {since}~{until} 约 {n_days} 个交易日 → 每批 {DAILY_ROW_LIMIT // n_days} 只，"
              f"共 {len(batches)} 批")
        frames = []
        for i, one in enumerate(batches, 1):
            ts_codes = ",".join(qlib_to_ts_code(s) for s in one)
            df = call_with_retry(pro.daily, ts_code=ts_codes, start_date=ts_since,
                                 end_date=ts_until)
            if df is None or df.empty:
                print(f"    [{i}/{len(batches)}] 空（多代码串可能被这个档位拒绝，试 --ts-batch date）")
                continue
            df = df.copy()
            df["ts_code"] = df["ts_code"].astype(str).str.strip()
            frames.append(df)
            print(f"    [{i}/{len(batches)}] {len(one)} 只 → {len(df)} 行")
        if not frames:
            return pd.DataFrame()
        price = pd.concat(frames, ignore_index=True)
        price["qlib_symbol"] = price["ts_code"].map(ts_code_to_qlib)
        fac_batches = batches

    price = price.rename(columns={"vol": "volume"})
    price["trade_date"] = pd.to_datetime(price["trade_date"], format="%Y%m%d", errors="coerce")

    # ---- 复权因子 ----
    fac_frames = []
    for i, one in enumerate(fac_batches, 1):
        ts_codes = ",".join(qlib_to_ts_code(s) for s in one)
        try:
            df = call_with_retry(pro.adj_factor, ts_code=ts_codes, start_date=ts_since,
                                 end_date=ts_until, retries=2)
        except RuntimeError as e:
            print(f"    ⚠ adj_factor 不可用（{str(e)[:90]}…）→ 放弃复权，只输出不复权价")
            break
        if df is None or df.empty:
            continue
        fac_frames.append(df)
        print(f"    adj_factor [{i}/{len(fac_batches)}] → {len(df)} 行")
    if not fac_frames:
        # adj_factor 在低积分档是「1 次/小时」，批量抓时基本拿不到；
        # 此时**不要抛**——把 daily 拿到的原始价交出去，复权列留 NaN，并说清怎么补。
        print("    ⚠ 没拿到 adj_factor（限频/无权限）→ 只输出不复权价，复权列留 NaN")
        print("      补法：等配额，或用 --source tencent（qfq 阶梯可反推乘权因子）")
        df = price.copy()
        for c in ("factor", "close_qfq", "close_hfq", "div_offset"):
            df[c] = np.nan
        if "amount" not in df.columns:
            df["amount"] = np.nan
        return df

    fac = pd.concat(fac_frames, ignore_index=True)
    fac["trade_date"] = pd.to_datetime(fac["trade_date"], format="%Y%m%d", errors="coerce")
    fac = fac.rename(columns={"ts_code": "ts_code", "adj_factor": "factor"})
    fac = fac[["ts_code", "trade_date", "factor"]].drop_duplicates(["ts_code", "trade_date"])

    df = price.merge(fac, on=["ts_code", "trade_date"], how="left")
    # ⚠ ffill/bfill 必须按股票分组做——整表 ffill 会把上一只票的因子串到下一只
    df["factor"] = df.groupby("ts_code")["factor"].ffill()
    df["factor"] = df.groupby("ts_code")["factor"].bfill()
    if df["factor"].isna().any():
        bad = df.loc[df["factor"].isna(), "ts_code"].unique()[:5]
        print(f"    ⚠ {bad} 等缺复权因子，对应行将被剔除")
        df = df.dropna(subset=["factor"])

    # 口径（Tushare 的 adj_factor 是**乘权**因子，与腾讯的等额复权不同源但数学自洽）：
    #   前复权 close_qfq = close × factor / factor(区间最后一天)   ← 基准=区间末日
    #   后复权 close_hfq = close × factor / factor(区间首日)       ← 基准=区间首日
    g = df.groupby("ts_code")["factor"]
    last_fac = g.transform("last")
    first_fac = g.transform("first")
    df["close_qfq"] = df["close"] * df["factor"] / last_fac
    df["close_hfq"] = df["close"] * df["factor"] / first_fac
    if "amount" not in df.columns:
        df["amount"] = np.nan
    # 等额口径的累计分红额（与腾讯路径同名列，方便两条源横向比）
    df["div_offset"] = df["close"] - df["close_qfq"]
    return df


# ------------------------------------------------------------------ main


def main() -> int:
    global TENCENT_SLEEP, USE_CACHE
    ap = argparse.ArgumentParser(description="获取股票历史收盘价（含复权）")
    ap.add_argument("--source", choices=["tushare", "tencent"], default="tencent",
                    help="tushare=图片原版（需 token）；tencent=腾讯前复权（免 token）")
    ap.add_argument("--token", default=None, help="Tushare token（默认读环境变量 TUSHARE_TOKEN）")
    ap.add_argument("--symbols", default="", help="逗号分隔的 qlib 代码；留空则用本地 all.txt 全量")
    ap.add_argument("--universe-file", default=_ROOT + r"/qlib_data/cn_data_2026/instruments/all.txt")
    ap.add_argument("--since", default="2020-01-01")
    ap.add_argument("--until", default=None, help="默认取今天")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--limit", type=int, default=0, help=">0 时只取前 N 只（调试用）")
    ap.add_argument("--no-qfq", action="store_true",
                    help="腾讯源只取不复权价（不做复权，复权列留 NaN）；被限频时用")
    ap.add_argument("--sleep", type=float, default=TENCENT_SLEEP,
                    help=f"腾讯源两次请求的最小间隔秒数（默认 {TENCENT_SLEEP}）")
    ap.add_argument("--no-cache", action="store_true", help="不读写响应缓存")
    ap.add_argument("--resume", action="store_true",
                    help="已存在输出文件时只在末尾补缺失的股票（限频中断后接着跑）")
    ap.add_argument("--ts-batch", choices=["date", "code"], default="date",
                    help="Tushare 批量方式：date=按交易日（默认，一次一天全市场）；"
                         "code=按代码（多只会拼成逗号串，这个档位会静默返回空）")
    ap.add_argument("--ts-max-days", type=int, default=60,
                    help="--ts-batch date 时最多抓多少个交易日（防呆，默认 60）")
    args = ap.parse_args()

    TENCENT_SLEEP = args.sleep
    USE_CACHE = not args.no_cache
    if args.no_qfq:
        _QFQ_BLOCKED[0] = True

    until = args.until or pd.Timestamp.today().strftime("%Y-%m-%d")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        uf = Path(args.universe_file)
        if not uf.exists():
            print(f"找不到 universe 文件: {uf}，请用 --symbols 指定")
            return 1
        symbols = [l.split("\t")[0].strip() for l in uf.read_text(encoding="utf-8").splitlines()
                   if l.strip()]
    if args.limit:
        symbols = symbols[:args.limit]
    print(f"== 股票历史收盘价 | 源={args.source} | {len(symbols)} 只 | {args.since}~{until} ==")

    t0 = time.time()
    aborted = None
    if args.source == "tushare":
        pro = make_pro(args.token)
        try:
            df = fetch_prices_tushare(symbols, args.since, until, pro,
                                      batch=args.ts_batch, max_days=args.ts_max_days)
        except RuntimeError as e:
            # 积分/权限问题：把话说透，别让人对着"重试 4 次仍失败"猜
            print(f"\n❌ Tushare 路径失败：{e}")
            print("   免 token 的替代：加 `--source tencent` 再跑一次。")
            return 2
    else:
        # --resume：已有输出里已经有复权价的股票直接跳过
        done = set()
        old = pd.DataFrame()
        out_path = out_dir / f"daily_{args.source}.parquet"
        if args.resume and out_path.exists():
            old = pd.read_parquet(out_path)
            old["trade_date"] = pd.to_datetime(old["trade_date"])
            has_qfq = old.dropna(subset=["close_qfq"]) if "close_qfq" in old else old.iloc[:0]
            done = set(has_qfq["qlib_symbol"].astype(str).str.upper().unique())
            if done:
                print(f"    续传：{len(done)} 只已有复权价，跳过")
            symbols = [s for s in symbols if s.upper() not in done]
            print(f"    待抓 {len(symbols)} 只")

        frames = []
        for i, sym in enumerate(symbols, 1):
            try:
                one = fetch_tencent_one(sym, args.since, until)
            except TencentRateLimited as e:
                aborted = str(e)
                print(f"\n  ❌ 腾讯限频，第 {i}/{len(symbols)} 只（{sym}）中止：{e}")
                print("     已抓到的部分会照常落盘；冷却几分钟后加 --resume 接着跑即可。")
                break
            if not one.empty:
                frames.append(one)
            if i % 20 == 0 or i == len(symbols):
                print(f"    [{i}/{len(symbols)}] 已取 {len(frames)} 只")
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if not old.empty:
            df = pd.concat([old, df], ignore_index=True) if not df.empty else old

    if df.empty:
        print("没有取到任何数据")
        return 1
    if aborted:
        print(f"  （本轮被限频中止，写出部分结果）")

    df["qlib_symbol"] = df["qlib_symbol"].astype(str).str.upper()
    if "ts_code" not in df.columns:
        df["ts_code"] = df["qlib_symbol"].map(qlib_to_ts_code)
    for c in OUT_COLS:
        if c not in df.columns:
            df[c] = np.nan
    df = df[OUT_COLS]
    df = df.sort_values(["qlib_symbol", "trade_date"]).reset_index(drop=True)

    out_path = out_dir / f"daily_{args.source}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n产出 {out_path}")
    print(f"  {len(df):,} 行 | {df['qlib_symbol'].nunique()} 只 | "
          f"{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()} | {time.time()-t0:.1f}s")
    n_no_qfq = int(df["close_qfq"].isna().sum())
    if n_no_qfq:
        print(f"  ⚠ {n_no_qfq:,} 行没有复权价（--no-qfq 或该股无分红数据）")
    return 0 if not aborted else 3


if __name__ == "__main__":
    raise SystemExit(main())
