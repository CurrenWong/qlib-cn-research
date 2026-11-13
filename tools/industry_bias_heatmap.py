"""申万一级行业「乖离率」热力图。

## 指标定义
乖离率（BIAS）衡量收盘价相对均线的偏离程度：

    BIAS_n = (close − MA_n) / MA_n × 100%

- `BIAS > 0`：价格在 n 日均线**之上**（超买/强势）
- `BIAS < 0`：价格在均线**之下**（超卖/弱势）
- 绝对值越大越极端。行业之间比 BIAS 比比涨幅更有意义——它把「不同点位」标准化了。

## 出图
| 图 | 内容 | 用途 |
|---|---|---|
| `bias_cross_section.png` | 31 行业 × 4 个周期（6/20/60/120）**当前**乖离率 | 一眼看出当下谁超买谁超卖 |
| `bias_timeline.png` | 31 行业 × 最近 N 个交易日 的 BIAS20 | 看这轮行情的**轮动路径** |
| `bias_percentile.png` | 当前 BIAS20 在近 3 年里的分位 | 剔除「不同行业波动率不同」的干扰 |

## 数据
- 指数日线：akshare `index_hist_sw`（上游是申万宏源研究 `index_publish` 接口，已验证到 1999 年）
- 行业清单：`data/sw_industry/industries.parquet`（31 个一级行业，来自 `fetch_sw_industry.py`）
- 日线**落盘缓存**到 `data/sw_industry/index_daily/<code>.parquet`，重跑不再打接口

## 用法
```cmd
cd /d D:\\Project\\qlib
.venv\\Scripts\\python.exe tools\\industry_bias_heatmap.py
.venv\\Scripts\\python.exe tools\\industry_bias_heatmap.py --periods 6,20,60,120 --days 60
.venv\\Scripts\\python.exe tools\\industry_bias_heatmap.py --refresh          :: 忽略缓存重抓
.venv\\Scripts\\python.exe tools\\industry_bias_heatmap.py --end 2026-06-30   :: 回看某天
```
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
QLIB_ROOT = HERE.parent
DATA_DIR = QLIB_ROOT / "data" / "sw_industry"
INDEX_DIR = DATA_DIR / "index_daily"
OUT_DIR = DATA_DIR / "bias"

sys.path.insert(0, str(HERE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# ---------------------------------------------------------------- 中文字体

CJK_FONTS = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC", "SimSun"]


def setup_font() -> str:
    """挑一个系统里真实存在的中文字体，否则图里的中文全是方块。"""
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_FONTS:
        if name in have:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False  # 负号别画成方块
            return name
    print("⚠ 没找到中文字体，图里中文会变方块")
    return ""


# ---------------------------------------------------------------- 数据


def load_industries() -> pd.DataFrame:
    f = DATA_DIR / "industries.parquet"
    if not f.exists():
        raise SystemExit(f"找不到 {f}，先跑 tools/fetch_sw_industry.py")
    df = pd.read_parquet(f)
    df["code6"] = df["index_code"].astype(str).str.replace(".SI", "", regex=False)
    return df.sort_values("industry_name").reset_index(drop=True)


def _fetch_akshare(code6: str) -> pd.DataFrame:
    import akshare as ak

    df = ak.index_hist_sw(symbol=code6, period="day")
    df = df.rename(columns={"日期": "date", "收盘": "close"})
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "close"]].dropna().sort_values("date").reset_index(drop=True)


def _fetch_sws_direct(code6: str) -> pd.DataFrame:
    """akshare 不顺时的兜底：直接打申万官网接口（同源，同域已验证可达）。"""
    import requests

    r = requests.get("https://www.swsresearch.com/institute-sw/api/index_publish/trend/",
                     params={"swindexcode": code6, "period": "DAY"},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    j = r.json()
    rows = j.get("data") or []
    df = pd.DataFrame([{"date": x.get("bargaindate"), "close": x.get("closeindex")} for x in rows])
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.dropna().sort_values("date").reset_index(drop=True)


def load_index_daily(code6: str, refresh: bool = False) -> pd.DataFrame:
    """取单个行业指数的日线，带磁盘缓存。"""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    f = INDEX_DIR / f"{code6}.parquet"
    if f.exists() and not refresh:
        df = pd.read_parquet(f)
        df["date"] = pd.to_datetime(df["date"])
        return df
    try:
        df = _fetch_akshare(code6)
    except Exception as e:  # noqa: BLE001
        print(f"      akshare 失败（{type(e).__name__}: {str(e)[:50]}）→ 直连申万")
        df = _fetch_sws_direct(code6)
    if not df.empty:
        df.to_parquet(f, index=False)
    time.sleep(0.3)
    return df


def build_panel(industries: pd.DataFrame, refresh: bool) -> pd.DataFrame:
    """拼出 [date × industry] 的收盘价面板。"""
    cols = {}
    for i, row in enumerate(industries.itertuples(), 1):
        name = row.industry_name
        try:
            df = load_index_daily(row.code6, refresh=refresh)
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ [{i}/{len(industries)}] {name} 取数失败: {type(e).__name__}: {str(e)[:60]}")
            continue
        cols[name] = df.set_index("date")["close"]
        if i % 5 == 0 or i == len(industries):
            print(f"  [{i}/{len(industries)}] {name} {len(df)} 行 "
                  f"({df['date'].min():%Y-%m-%d} ~ {df['date'].max():%Y-%m-%d})")
    if not cols:
        raise SystemExit("一个行业都没取到")
    panel = pd.DataFrame(cols).sort_index()
    return panel


# ---------------------------------------------------------------- 指标


def bias(series: pd.Series, n: int) -> pd.Series:
    ma = series.rolling(n, min_periods=max(5, n // 2)).mean()
    return (series - ma) / ma * 100.0


def bias_matrix(panel: pd.DataFrame, periods: list[int]) -> dict[int, pd.DataFrame]:
    return {n: panel.apply(bias, n=n) for n in periods}


def percentile_rank(s: pd.Series, window: int) -> float:
    """最新值在过去 window 个交易日里的分位（0~100）。"""
    tail = s.dropna().tail(window)
    if len(tail) < 30:
        return np.nan
    return float((tail <= tail.iloc[-1]).mean() * 100)


# ---------------------------------------------------------------- 画图


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  → {path}")


def plot_cross_section(snap: pd.DataFrame, out: Path, title: str = "") -> None:
    """31 行 × 周期列 的截面热力图，数值直接标在格子里。"""
    mat = snap.values
    vmax = float(np.nanmax(np.abs(mat))) or 1.0
    fig, ax = plt.subplots(figsize=(7.2, 10.5))
    im = ax.imshow(mat, cmap="RdYlBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(snap.columns)), [f"BIAS{c}" for c in snap.columns], fontsize=10)
    ax.set_yticks(range(len(snap.index)), snap.index, fontsize=9)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                continue
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(v) > vmax * 0.6 else "#333333")
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("乖离率 %（红=在均线上方）", fontsize=9)
    ax.set_title(title or "申万一级行业乖离率（当前）", fontsize=13, pad=12)
    ax.set_xlabel("均线周期（交易日）", fontsize=9)
    _save(fig, out)


def plot_timeline(mat: pd.DataFrame, out: Path, n: int, title: str = "") -> None:
    """行业 × 日期 的热力图，看轮动路径。"""
    data = mat.values.astype(float)
    vmax = float(np.nanpercentile(np.abs(data), 98)) or 1.0
    fig, ax = plt.subplots(figsize=(14, 9))
    im = ax.imshow(data, cmap="RdYlBu_r", vmin=-vmax, vmax=vmax, aspect="auto",
                   interpolation="nearest")
    ax.set_yticks(range(len(mat.index)), mat.index, fontsize=9)
    ncols = len(mat.columns)
    step = max(1, ncols // 12)
    idx = list(range(0, ncols, step))
    ax.set_xticks(idx, [mat.columns[i].strftime("%m-%d") for i in idx], fontsize=9,
                  rotation=45, ha="right")
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.015)
    cb.set_label(f"BIAS{n} %", fontsize=9)
    ax.set_title(title or f"申万一级行业 BIAS{n} 近 {ncols} 个交易日", fontsize=13, pad=12)
    _save(fig, out)


def plot_percentile(pct: pd.Series, out: Path, n: int, title: str = "") -> None:
    """分位柱状图：当前偏离在历史中的位置（横向，按分位排序）。"""
    s = pct.dropna().sort_values()
    colors = plt.cm.RdYlBu_r(s.values / 100.0)
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.barh(range(len(s)), s.values, color=colors, edgecolor="white", height=0.72)
    ax.set_yticks(range(len(s)), s.index, fontsize=9)
    ax.set_xlim(0, 100)
    ax.axvline(50, color="#666", lw=0.8, ls="--")
    ax.axvline(80, color="#c0392b", lw=0.8, ls=":")
    ax.axvline(20, color="#2471a3", lw=0.8, ls=":")
    for i, v in enumerate(s.values):
        ax.text(v + 1.2, i, f"{v:.0f}", va="center", fontsize=8, color="#333")
    ax.set_xlabel(f"当前 BIAS{n} 在近 3 年的分位（%）", fontsize=10)
    ax.set_title(title or f"行业乖离率历史分位（BIAS{n}）", fontsize=13, pad=12)
    ax.grid(axis="x", alpha=0.25)
    _save(fig, out)


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description="申万一级行业乖离率热力图")
    ap.add_argument("--periods", default="6,20,60,120", help="均线周期，逗号分隔")
    ap.add_argument("--days", type=int, default=60, help="时间热力图的交易日窗口")
    ap.add_argument("--end", default=None, help="截止日（默认最新），如 2026-06-30")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--refresh", action="store_true", help="忽略缓存重新抓指数日线")
    args = ap.parse_args()

    periods = [int(x) for x in args.periods.split(",") if x.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    font = setup_font()
    print(f"== 申万一级行业乖离率 | 周期 {periods} | 字体 {font or '无'} ==")

    inds = load_industries()
    print(f"行业 {len(inds)} 个，取指数日线…")
    panel = build_panel(inds, refresh=args.refresh)
    if args.end:
        panel = panel.loc[:args.end]
    print(f"面板 {panel.shape[0]} 交易日 × {panel.shape[1]} 行业 | "
          f"{panel.index.min():%Y-%m-%d} ~ {panel.index.max():%Y-%m-%d}")

    bm = bias_matrix(panel, periods)
    snap = pd.DataFrame({n: bm[n].iloc[-1] for n in periods}, index=panel.columns)
    snap = snap.sort_values(periods[1] if len(periods) > 1 else periods[0], ascending=False)

    asof = panel.index.max()
    print(f"\n最新交易日 {asof:%Y-%m-%d}")
    key = periods[1] if len(periods) > 1 else periods[0]
    print(f"\nBIAS{key} 最超买 5 个：")
    for name, row in snap.head(5).iterrows():
        print(f"  {name:<8} " + "  ".join(f"BIAS{n}={row[n]:+6.2f}%" for n in periods))
    print(f"\nBIAS{key} 最超卖 5 个：")
    for name, row in snap.tail(5).iterrows():
        print(f"  {name:<8} " + "  ".join(f"BIAS{n}={row[n]:+6.2f}%" for n in periods))

    print("\n出图：")
    plot_cross_section(snap, out_dir / "bias_cross_section.png",
                       title=f"申万一级行业乖离率（{asof:%Y-%m-%d}）")

    tl = bm[key].tail(args.days).T  # 行=行业，列=日期
    plot_timeline(tl, out_dir / "bias_timeline.png", key,
                  title=f"申万一级行业 BIAS{key} 近 {len(tl.columns)} 个交易日")

    pct = pd.Series({name: percentile_rank(bm[key][name], 750) for name in panel.columns})
    plot_percentile(pct, out_dir / "bias_percentile.png", key)

    snap.to_csv(out_dir / "bias_snapshot.csv", encoding="utf-8-sig")
    bm[key].tail(args.days).T.to_csv(out_dir / "bias_timeline.csv", encoding="utf-8-sig")
    print(f"  → {out_dir / 'bias_snapshot.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
