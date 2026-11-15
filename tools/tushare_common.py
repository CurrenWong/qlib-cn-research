"""Tushare 数据接口的公共封装：token 解析、代码互转、批量切分、重试。

## 来历
图片里的代码来自一篇公众号文章，作者把聚宽（JoinQuant）的
`get_industry_stock` / 历史行情抓取改写成了 Tushare 版。原样搬过来有 8 处硬伤，
本模块把它们修掉并抽出共用部分：

| 原图代码 | 问题 | 本仓库做法 |
|---|---|---|
| `s.industry['index_code'] = s.industry['index_code'].drop(columns='index_code')` | 语法/语义都不成立 | 删除，改为规整的 DataFrame |
| `s.industry.loc['999999'] = '全市场'` | 索引是 int，赋 str 会错 | 用显式的哨兵常量 |
| `for stk in stock_list: df = df_all[df_all['ts_code']==stk]` | O(N×M)，5000 只股票要扫 5000 次 | `drop_duplicates` 向量化 |
| `stk_num = int(6000 / (count * 20) ** 0.99)` | `count` 未定义 | `chunk_by_row_budget()` 按行数预算切批 |
| `joined_str = ','.join(stock_list[i:idx_end])` | `idx_end` 未定义 | 切批函数直接返回分片 |
| `for j, pro.daily(...)` | 语法错 | `df = pro.daily(...)` |
| `df[date] = df.index` / `if i == price_all.index[0]` | OCR 残缺，逻辑不通 | 复权用 `adj_factor` 正规算法 |
| 代码风格是 `s.xxx` 全局命名空间 | 容易互相污染 | 全部改成函数 + 返回值 |

## 共用约定
- **token**：读环境变量 `TUSHARE_TOKEN`；没有就读 `%USERPROFILE%\\.tushare_token`；
  都没有则报错退出（不硬编码任何密钥）。
- **代码风格**：落盘一律用本项目的 qlib 风格（`SH600519` / `SZ000001` / `BJ430017`），
  Tushare 风格（`600519.SH`）只在边界处互转。
- **批量**：Tushare `pro.daily` 单次最多 6000 行、`index_member_all` 最多 2000 行，
  所有批量接口统一按「行数预算」切分，而不是按固定只数。
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, Iterable, List, Sequence

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

# ---------------------------------------------------------------- 路径 / 常量

QLIB_ROOT = Path(_ROOT)
QLIB_DATA = QLIB_ROOT / "qlib_data" / "cn_data_2026"
CALENDAR_FILE = QLIB_DATA / "calendars" / "day.txt"

#: Tushare `pro.daily` 单次返回上限（官方限制）
DAILY_ROW_LIMIT = 6000
#: Tushare `pro.index_member_all` 单次返回上限（官方限制）
MEMBER_ROW_LIMIT = 2000
#: 聚宽口径的哨兵行业代码：全市场 / 合计
PSEUDO_INDUSTRY_ALL = "999999"
PSEUDO_INDUSTRY_TOTAL = "999998"


# ---------------------------------------------------------------- token / 客户端


def resolve_token(explicit: str | None = None) -> str:
    """按 显式参数 > 环境变量 > 用户目录文件 的顺序找 Tushare token。"""
    if explicit:
        return explicit.strip()
    env = os.environ.get("TUSHARE_TOKEN", "").strip()
    if env:
        return env
    f = Path.home() / ".tushare_token"
    if f.exists():
        v = f.read_text(encoding="utf-8").strip()
        if v:
            return v
    raise RuntimeError(
        "没有找到 Tushare token。设置环境变量 TUSHARE_TOKEN，"
        "或把 token 写进 %USERPROFILE%\\.tushare_token，或用 --token 传入。"
    )


def make_pro(token: str | None = None):
    """建一个已登录的 tushare pro 客户端。"""
    import tushare as ts  # 延迟导入：没 token 时不必先装

    tok = resolve_token(token)
    ts.set_token(tok)
    return ts.pro_api(tok)


#: Tushare 的**限频**错误特征：可以重试，但间隔得按它的口径来（低积分档 1 次/分钟）
RATE_LIMIT_HINTS = ("频率超限", "每分钟", "每小时", "每天最多", "最多访问")

#: Tushare 的**永久性**错误特征：重试没有意义，必须立刻失败并说清原因
PERMANENT_HINTS = (
    "没有接口",      # code 40203：账号积分/权限不足
    "权限",
    "积分不足",
    "token不对",
    "TOKEN 不对",
    "token无效",
    "您的token",
)


def _is_permanent(err: BaseException) -> bool:
    s = str(err)
    if any(h in s for h in RATE_LIMIT_HINTS):   # 限频优先判定：它长得也像"拒绝"
        return False
    return any(h in s for h in PERMANENT_HINTS)


def _is_rate_limited(err: BaseException) -> bool:
    return any(h in str(err) for h in RATE_LIMIT_HINTS)


def _rate_limit_seconds(err: BaseException) -> float | None:
    """从「频率超限(1次/小时)」里解析出该等多久；解析不出来就给 65 秒。

    ⚠ 小时级/天级的限频**不要等**（等一小时等于卡死），返回 None 让上层立刻放弃并降级。
    """
    import re

    s = str(err)
    m = re.search(r"超限\((\d+)\s*次\s*/\s*(分钟|小时|天)\)", s)
    if not m:
        return 65.0
    n, unit = int(m.group(1)), m.group(2)
    secs = {"分钟": 60.0, "小时": 3600.0, "天": 86400.0}[unit]
    wait = secs / max(1, n)
    return None if wait > 600 else wait + 5


def call_with_retry(fn: Callable, *, retries: int = 4, base_delay: float = 2.0, **kwargs):
    """调 Tushare 接口，失败按指数退避重试（限频/网络抖动常见）。

    ⚠ **限频错误按它自己声明的口径等**：低积分档常见 `1 次/分钟`，
    用 2/4/8 秒的普通退避会连撞 4 次全部失败、还让人以为是权限问题（2026-11-13 实测）；
    而 `1 次/小时` 这种**直接放弃**——等一小时没意义，交给调用方降级。

    ⚠ **权限/积分/token 错误不重试**：`code 40203 抱歉，您没有接口(xxx)访问权限`
    是账号层面的永久拒绝，重试只会白等 14 秒再抛一句"重试 4 次仍失败"，
    把真正的原因埋掉。
    """
    last = None
    for attempt in range(retries):
        try:
            return fn(**kwargs)
        except Exception as e:  # noqa: BLE001
            last = e
            if _is_rate_limited(e):
                wait = _rate_limit_seconds(e)
                if wait is None:
                    raise RuntimeError(
                        f"Tushare 限频（长周期）：{str(e)[:140]}\n"
                        f"  → 该接口在这个账号档位是小时/天级限频，批量抓不可行；"
                        f"请改用 --source tencent（复权因子可由 qfq 阶梯反推）"
                    ) from e
                if attempt == retries - 1:
                    break
                print(f"    接口限频（第 {attempt+1}/{retries} 次）：{str(e)[:70]}"
                      f" → {wait:.0f}s 后重试")
                time.sleep(wait)
                continue
            if _is_permanent(e):
                raise RuntimeError(
                    f"Tushare 拒绝访问（{type(e).__name__}）：{str(e)[:160]}\n"
                    f"  → 这是账号积分/权限问题，重试无用。"
                    f"需要 120 积分才能用 pro.daily/adj_factor；"
                    f"临时方案：改用 --source tencent（免 token）"
                ) from e
            if attempt == retries - 1:
                break
            wait = base_delay * (2 ** attempt)
            print(f"    接口失败（第 {attempt+1}/{retries} 次）：{type(e).__name__}: {str(e)[:120]}"
                  f" → {wait:.0f}s 后重试")
            time.sleep(wait)
    raise RuntimeError(f"Tushare 接口重试 {retries} 次仍失败: {type(last).__name__}: {last}")


# ---------------------------------------------------------------- 代码互转


def ts_code_to_qlib(ts_code: str) -> str:
    """`600519.SH` → `SH600519`（本项目 qlib 风格）。"""
    ts_code = ts_code.strip().upper()
    if "." not in ts_code:
        return bare_code_to_qlib(ts_code)
    code, mkt = ts_code.split(".", 1)
    return ("SH" if mkt == "SH" else "SZ" if mkt == "SZ" else "BJ") + code


def qlib_to_ts_code(symbol: str) -> str:
    """`SH600519` → `600519.SH`（Tushare 风格）。"""
    symbol = symbol.strip().upper()
    if "." in symbol:
        return symbol
    mkt, code = symbol[:2], symbol[2:]
    return f"{code}.{mkt}"


def bare_code_to_qlib(code: str) -> str:
    """裸 6 位代码 → qlib 风格，按号段判交易所。

    60xxxx/68xxxx → 上交所；00xxxx/30xxxx → 深交所；4xxxxx/8xxxxx → 北交所。
    """
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if not code:
        raise ValueError(f"无法解析的代码: {code!r}")
    if code.startswith(("60", "68", "9")):
        return "SH" + code
    if code.startswith(("00", "30", "2")):
        return "SZ" + code
    return "BJ" + code


# ---------------------------------------------------------------- 批量切分


def to_ts_date(d: str) -> str:
    """`2024-01-02` → `20240102`。

    Tushare 的所有日期参数（`start_date` / `end_date` / `trade_date`）都只吃
    紧凑格式；传带横杠的日期**不报错、直接返回空表**——比报错更难查。
    """
    return str(d).replace("-", "").strip()


def chunk_by_row_budget(items: Sequence[str], rows_per_item: int,
                         limit: int = DAILY_ROW_LIMIT) -> List[List[str]]:
    """按「行数预算」把标的切成多批。

    Tushare 的批量接口限制的是**返回行数**而不是只数：
    `pro.daily` 一次最多 6000 行、`pro.index_member_all` 一次最多 2000 行。
    所以一批能塞多少只，取决于每只要占几行（历史区间长度 × 命中条数）。

    ⚠ 注意：如果**单个标的**就要占满超过 ``limit`` 行（例如一年以上的日线区间），
    切批救不了，只能改成 1 只/批 并缩短区间——这是接口硬限制，不是本函数的 bug。

    Parameters
    ----------
    items : 待切分的标的列表
    rows_per_item : 每个标的预计占用的行数（算保守一点）
    limit : 单次调用的行数上限

    Returns
    -------
    List[List[str]]：分片后的标的列表，每片满足 ``len(片) * rows_per_item <= limit``
    """
    rows_per_item = max(1, int(rows_per_item))
    size = max(1, limit // rows_per_item)
    return [list(items[i:i + size]) for i in range(0, len(items), size)]


def trading_day_count(start: str, end: str) -> int:
    """区间内的交易日数（优先用本地 qlib 日历，取不到就按 243 天/年估）。"""
    try:
        if CALENDAR_FILE.exists():
            cal = CALENDAR_FILE.read_text(encoding="utf-8").split()
            n = sum(1 for d in cal if start <= d <= end)
            if n:
                return n
    except OSError:
        pass
    from datetime import date

    y0, m0, d0 = (int(x) for x in start.split("-"))
    y1, m1, d1 = (int(x) for x in end.split("-"))
    days = (date(y1, m1, d1) - date(y0, m0, d0)).days
    return max(1, int(days / 365 * 243))


def iter_chunks(items: Iterable[str], size: int) -> Iterable[List[str]]:
    """把序列按固定块长切开（用于 2000 行上限这类「按条数」的接口）。"""
    buf: List[str] = []
    for it in items:
        buf.append(it)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


# ---------------------------------------------------------------- 本地 qlib bin


def read_bin(path: Path):
    """读 qlib 的 `.bin`：首 4 字节是**起始日历下标**，其后是 float32 序列。"""
    import numpy as np

    arr = np.fromfile(path, dtype=np.float32)
    if arr.size == 0:
        return 0, arr
    return int(arr[0]), arr[1:]


def load_qlib_series(symbol: str, field: str = "close") -> "pd.Series":
    """读本地 qlib bin 的一路字段，按交易日历对齐（停牌日不在序列里）。

    ⚠ 必须按 `.bin` 里的起始下标切日历：qlib 只存**有行情的日子**，
    直接 `zip(calendar, values)` 会把停牌后的价格错位到后面的交易日上。
    """
    import pandas as pd

    path = QLIB_DATA / "features" / symbol.lower() / f"{field}.day.bin"
    start, vals = read_bin(path)
    cal = CALENDAR_FILE.read_text(encoding="utf-8").split()
    dates = cal[start:start + len(vals)]
    s = pd.Series(vals, index=pd.to_datetime(dates), name=field, dtype="float64")
    return s[~s.index.duplicated(keep="last")]
