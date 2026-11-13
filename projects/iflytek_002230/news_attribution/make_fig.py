"""画图：科大讯飞 002230。

fig1 = 18 年全景（对数轴，574 个事件全标出来）
fig2 = AI 叙事周期事件链（2023-01 ~ 2026-10，双栏：上栏只走线+编号圈，下栏事件卡片）

用**实际成交价**（不复权），不是 qlib 的前复权价——新闻里报的也是成交价，对得上。
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

warnings.filterwarnings("ignore")
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150

HERE = Path(__file__).resolve().parent
CACHE = HERE / "price_cache.csv"
BCACHE = HERE / "bench_cache.csv"

UP_C, DN_C = "#e67e22", "#c0392b"
UP_F, DN_F = "#fdf6e3", "#fdecea"


def load():
    if CACHE.exists() and BCACHE.exists():
        px = pd.read_csv(CACHE, parse_dates=["date"]).set_index("date").sort_index()
        b = pd.read_csv(BCACHE, parse_dates=["date"]).set_index("date").sort_index()
        print(f"用缓存：个股 {px.index[0].date()} ~ {px.index[-1].date()}（{len(px)} 天）")
        return px, b
    import akshare as ak

    px = ak.stock_zh_a_daily(symbol="sz002230", adjust="").copy()
    px["date"] = pd.to_datetime(px["date"])
    px = px.set_index("date").sort_index()
    px.to_csv(CACHE, encoding="utf-8-sig")
    b = ak.stock_zh_index_daily(symbol="sh000300").copy()
    b["date"] = pd.to_datetime(b["date"])
    b = b.set_index("date").sort_index()
    b.to_csv(BCACHE, encoding="utf-8-sig")
    print(f"已拉取并缓存：个股 {px.index[0].date()} ~ {px.index[-1].date()}（{len(px)} 天）")
    return px, b


px, bench = load()
ev = pd.read_csv(HERE / "events.csv")
ev["date"] = pd.to_datetime(ev["date"])

# ------------------------------------------------------------------ 图1：全景
fig, ax = plt.subplots(figsize=(14.2, 7.0))
ax.plot(px.index, px["close"], color="#1f3b73", lw=1.5, label="科大讯飞 002230（实际成交价）", zorder=3)
b = bench.loc[px.index[0]: px.index[-1]]
ax.plot(b.index, b["close"] / b["close"].iloc[0] * px["close"].iloc[0],
        color="#c4c4c4", lw=1.2, ls="--", label="沪深300（起点对齐）", zorder=2)

up = ev[ev["ret"] > 0]
dn = ev[ev["ret"] < 0]
ax.scatter(up["date"], px["close"].reindex(up["date"]).values, s=11, color=UP_C,
           zorder=5, alpha=0.85, linewidths=0, label=f"上涨事件（{len(up)}）")
ax.scatter(dn["date"], px["close"].reindex(dn["date"]).values, s=11, color=DN_C,
           zorder=5, alpha=0.85, linewidths=0, label=f"下跌事件（{len(dn)}）")

NOTES = [
    ("2008-05-12", "上市首日收 30.31 元\n较发行价 12.66 涨 139%", 34, 40),
    ("2010-12-14", "2010 牛市顶 88 元", 46, 8),
    ("2015-06-26", "2015 股灾\n连续跌停", -20, -92),
    ("2015-07-08", "重大事项停牌\n（重组）三日零涨跌", 34, 58),
    ("2023-02-06", "ChatGPT 概念启动\n当日 +9.2%，超额 +10.5%", -44, 44),
    ("2025-02-05", "DeepSeek 行情\n当日 +7.4%，超额 +8.0%", -24, 54),
    ("2026-07-31", "2026 缩量阴跌\n现价 37.50 元", -30, -58),
]
for d, text, dx, dy in NOTES:
    ts = pd.Timestamp(d)
    if ts not in px.index:
        continue
    y = float(px.loc[ts, "close"])
    ax.annotate(text, xy=(ts, y), xytext=(dx, dy), textcoords="offset points",
                ha="center", fontsize=9.2, color="#333", linespacing=1.45, zorder=8,
                bbox=dict(boxstyle="round,pad=0.42", fc="#ffffff", ec="#999",
                          lw=0.9, alpha=0.94),
                arrowprops=dict(arrowstyle="-", color="#999", lw=0.8, shrinkA=3, shrinkB=5))

ax.set_yscale("log")
ax.yaxis.set_major_locator(matplotlib.ticker.LogLocator(
    base=10, subs=np.arange(1, 10) * 0.1, numticks=100))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _p: f"{v:.0f}"))
ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
ax.set_title("科大讯飞 002230（2008-05 上市 ~ 2026-10）：18 年 574 次大波动，AI 叙事的全部起落",
             fontsize=15.5, pad=14, weight="bold")
ax.set_ylabel("收盘价（元，对数轴）", fontsize=11)
ax.set_xlabel("2026 年", fontsize=10.5) if False else ax.set_xlabel("年份", fontsize=10.5, labelpad=6)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.085), ncol=4,
          frameon=False, fontsize=10)
ax.grid(alpha=0.2, ls=":", which="both")
ax.tick_params(labelsize=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.savefig(HERE / "fig_iflytek_panorama.png", bbox_inches="tight", facecolor="white")
print(f"已保存 {HERE / 'fig_iflytek_panorama.png'}")
plt.close(fig)

# ------------------------------------------------------------------ 图2：事件链
WIN = ("2023-01-03", "2026-10-29")
px2 = px.loc[WIN[0]: WIN[1]]
b2 = bench.loc[px2.index[0]: px2.index[-1]]

# (编号, 日期, 当日涨跌, 说明, 方向, 编号圈上移点数)
EVENTS = [
    (1, "2023-01-30", "+10.0%", "2022 年度业绩预告，当日涨停", +1, 0),
    (2, "2023-02-06", "+9.2%", "ChatGPT 概念启动，超额 +10.5%", +1, 0),
    (3, "2023-04-21", "-9.2%", "2022 年报披露当日大跌（利好出尽）", -1, 0),
    (4, "2023-08-16", "-8.6%", "星火大模型升级发布会次日", -1, 0),
    (5, "2023-10-24", "-10.0%", "全球 1024 开发者节前跌停", -1, 0),
    (6, "2024-09-30", "+10.0%", "9·24 政策行情，超额仅 +1.5%", +1, 0),
    (7, "2024-11-13", "+10.0%", "超额 +9.4%，普涨行情", +1, 0),
    (8, "2025-02-05", "+7.4%", "DeepSeek 行情启动，超额 +8.0%", +1, 0),
    (9, "2025-04-07", "-10.0%", "跌停，超额 -2.9%", -1, 0),
    (10, "2026-01-29", "+6.4%", "2025 年度业绩预告", +1, 0),
    (11, "2026-06-26", "-6.1%", "行业质疑扩产逻辑（弱归因）", -1, 0),
    (12, "2026-07-31", "+5.9%", "回购进展公告", +1, 0),
]

fig = plt.figure(figsize=(14.2, 11.4))
gs = fig.add_gridspec(2, 1, height_ratios=[5.2, 6.0], hspace=0.16,
                      left=0.07, right=0.975, top=0.945, bottom=0.035)
ax = fig.add_subplot(gs[0])
axk = fig.add_subplot(gs[1])

ax.plot(px2.index, px2["close"], color="#1f3b73", lw=1.6,
        label="科大讯飞 002230（实际成交价）", zorder=3)
ax.plot(b2.index, b2["close"] / b2["close"].iloc[0] * px2["close"].iloc[0],
        color="#c4c4c4", lw=1.3, ls="--", label="沪深300（起点对齐）", zorder=2)
ax.set_ylim(px2["close"].min() * 0.86, px2["close"].max() * 1.10)
ax.set_xlim(px2.index[0] - pd.Timedelta(days=14), px2.index[-1] + pd.Timedelta(days=14))

for num, d, pct, _desc, sign, dy in EVENTS:
    ts = pd.Timestamp(d)
    if ts not in px2.index:
        continue
    y = float(px2.loc[ts, "close"])
    col = UP_C if sign > 0 else DN_C
    ax.axvline(ts, color=col, lw=0.8, ls=":", alpha=0.28, zorder=1)
    if dy:
        ax.annotate("", xy=(ts, y), xytext=(0, dy), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", color=col, lw=1.0,
                                    shrinkA=0, shrinkB=0, alpha=0.75), zorder=5)
    ax.annotate(f"{num}", xy=(ts, y), xytext=(0, dy), textcoords="offset points",
                ha="center", va="center", fontsize=10.5, color="white", weight="bold",
                zorder=7, bbox=dict(boxstyle="circle,pad=0.32", fc=col, ec="white", lw=2.0))

ax.set_title("科大讯飞 002230（2023-01 ~ 2026-10 实际成交价）：AI 叙事的每一次起落",
             fontsize=15.5, pad=14, weight="bold")
ax.set_ylabel("收盘价（元）", fontsize=11)
ax.legend(loc="upper right", frameon=False, fontsize=10.5)
ax.annotate("沪深300 五个交易日 +25%（9·24 政策行情）",
            xy=(pd.Timestamp("2024-10-08"), 37.62),
            xytext=(16, -36), textcoords="offset points", ha="left", fontsize=8.8,
            color="#888", zorder=6)
ax.grid(alpha=0.2, ls=":")
ax.tick_params(labelsize=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

# ---- 卡片区：3 列 × 4 行
axk.set_xlim(0, 1)
axk.set_ylim(0, 1)
axk.axis("off")
axk.text(0.0, 0.995, "事件对照表（编号对应上图圆点）", fontsize=12, weight="bold",
         color="#1f3b73", transform=axk.transAxes, va="top")

COLS, ROWS = 3, 4
GAP_X, GAP_Y = 0.014, 0.026
TOP, BOT = 0.90, 0.01
cw = (1 - GAP_X * (COLS - 1)) / COLS
ch = (TOP - BOT - GAP_Y * (ROWS - 1)) / ROWS

for i, (num, d, pct, desc, sign, _dy) in enumerate(EVENTS):
    r, c = divmod(i, COLS)
    x0 = c * (cw + GAP_X)
    y0 = TOP - (r + 1) * ch - r * GAP_Y
    col = UP_C if sign > 0 else DN_C
    fc = UP_F if sign > 0 else DN_F
    axk.add_patch(FancyBboxPatch((x0, y0), cw, ch,
                                  boxstyle="round,pad=0.004,rounding_size=0.008",
                                  transform=axk.transAxes, fc=fc, ec=col, lw=1.1,
                                  alpha=0.97, zorder=1))
    axk.add_patch(plt.Rectangle((x0, y0), 0.0038, ch, transform=axk.transAxes,
                                fc=col, ec="none", zorder=2))
    bx, by = x0 + 0.026, y0 + ch / 2
    axk.scatter([bx], [by], s=290, transform=axk.transAxes, fc=col, ec="white",
                lw=1.6, zorder=3, clip_on=False)
    axk.text(bx, by, f"{num}", transform=axk.transAxes, ha="center", va="center",
             fontsize=9.5, color="white", weight="bold", zorder=4)
    axk.text(x0 + 0.050, y0 + ch * 0.70, f"{d[5:]}   {pct}", transform=axk.transAxes,
             ha="left", va="center", fontsize=10, color="#222", weight="bold", zorder=4)
    axk.text(x0 + 0.050, y0 + ch * 0.29, desc, transform=axk.transAxes,
             ha="left", va="center", fontsize=9.2, color="#444", zorder=4)

fig.savefig(HERE / "fig_iflytek_events.png", bbox_inches="tight", facecolor="white")
print(f"已保存 {HERE / 'fig_iflytek_events.png'}")
for num, d, pct, _desc, sign, _dy in EVENTS:
    ts = pd.Timestamp(d)
    if ts in px2.index:
        print(f"  #{num} {d} {pct}  close={float(px2.loc[ts, 'close']):.2f}")
