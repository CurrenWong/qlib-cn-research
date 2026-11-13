"""画图：2026 年 600418 实际成交价 + 归因事件。

结构刻意做成上下两栏：
  上栏 = 价格走线 + 编号圆点（不放任何文字，保证走线绝对干净）
  下栏 = 事件卡片（文字全部在这里，带编号与日期，方便和上栏圆点对应）

用**实际成交价**（不是 qlib 的前复权价）——新闻里报的也是成交价，对得上。
"""

import warnings
from pathlib import Path

import matplotlib

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

# ---------------------------------------------------------------- 取数据
START, END = "2026-03-25", "2026-10-29"


def load_prices():
    if CACHE.exists():
        px = pd.read_csv(CACHE, parse_dates=["date"]).set_index("date").sort_index()
        if px.index[0] <= pd.Timestamp(START) and px.index[-1] >= pd.Timestamp(END):
            print(f"用缓存 {CACHE.name}（{px.index[0].date()} ~ {px.index[-1].date()}）")
            return px.loc[START:END]
    import akshare as ak

    px = ak.stock_zh_a_daily(symbol="sh600418", adjust="").copy()
    px["date"] = pd.to_datetime(px["date"])
    px = px.set_index("date").sort_index()
    px.to_csv(CACHE, encoding="utf-8-sig")
    print(f"已拉取并缓存 {CACHE.name}")
    return px.loc[START:END]


def load_bench():
    """基准：沪深300，必须先切到与个股同一区间再做起点对齐。"""
    path = HERE / "bench_cache.csv"
    if path.exists():
        bench = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    else:
        import akshare as ak

        bench = ak.stock_zh_index_daily(symbol="sh000300").copy()
        bench["date"] = pd.to_datetime(bench["date"])
        bench = bench.set_index("date").sort_index()
        bench.to_csv(path, encoding="utf-8-sig")
    return bench.loc[px.index[0]: px.index[-1]]


px = load_prices()
bench = load_bench()

# ---------------------------------------------------------------- 事件
# (编号, 日期, 当日涨跌, 说明, 方向)
EVENTS = [
    (1, "2026-04-27", "+10.0%", "4 月底冲高", +1, 0),
    (2, "2026-06-26", "-6.7%", "5–6 月连续阴跌，回调约 47%", -1, 0),
    (3, "2026-07-09", "+10.0%", "半年度业绩预亏公告（次日涨停）", +1, 0),
    (4, "2026-09-22", "+10.0%", "赛力斯模式生变 + Stellantis / 华为合作传闻", +1, 0),
    (5, "2026-09-28", "+10.0%", "鸿蒙智行发布会，尊界 SUV 2027 年上市", +1, 0),
    (6, "2026-10-08", "-10.0%", "尊界 V800 刹车踏板支架断裂，两天蒸发 106 亿", -1, 0),
    (7, "2026-10-14", "-8.6%", "9 月产销快报，销量同比 -18.7%", -1, 0),
    (8, "2026-10-16", "+10.0%", "工信部等三部门联合调查落地", +1, 26),
]

UP_C, DN_C = "#e67e22", "#c0392b"
UP_F, DN_F = "#fdf6e3", "#fdecea"

# ---------------------------------------------------------------- 画布
fig = plt.figure(figsize=(13.8, 9.6))
gs = fig.add_gridspec(2, 1, height_ratios=[5.4, 3.6], hspace=0.18,
                      left=0.075, right=0.975, top=0.945, bottom=0.05)
ax = fig.add_subplot(gs[0])
axk = fig.add_subplot(gs[1])

# ---- 上栏：走线
ax.plot(px.index, px["close"], color="#1f3b73", lw=1.7,
        label="江淮汽车 600418（实际成交价）", zorder=3)
ax.plot(bench.index, bench["close"] / bench["close"].iloc[0] * px["close"].iloc[0],
        color="#c4c4c4", lw=1.3, ls="--", label="沪深300（起点对齐）", zorder=2)

ymin, ymax = float(px["close"].min()), float(px["close"].max())
ax.set_ylim(ymin * 0.74, ymax * 1.10)
ax.set_xlim(px.index[0] - pd.Timedelta(days=12), px.index[-1] + pd.Timedelta(days=18))

# 编号圆点：上栏只出现编号，不出现文字
for num, d, pct, _desc, sign, dy in EVENTS:
    ts = pd.Timestamp(d)
    if ts not in px.index:
        continue
    y = float(px.loc[ts, "close"])
    col = UP_C if sign > 0 else DN_C
    # 极淡的竖虚线，便于把圆点对应到下栏卡片
    ax.axvline(ts, color=col, lw=0.8, ls=":", alpha=0.30, zorder=1)
    if dy:
        # 圆点挤在一起时把编号圈往上挪，并用细线连回真实位置
        ax.annotate("", xy=(ts, y), xytext=(0, dy), textcoords="offset points",
                    arrowprops=dict(arrowstyle="-", color=col, lw=1.0,
                                    shrinkA=0, shrinkB=0, alpha=0.75), zorder=5)
        ax.scatter([ts], [y], s=42, color=col, zorder=6,
                   edgecolors="white", linewidths=1.2)
    # 编号圈（圆角 bbox 跟着文字走，偏移时不会掉出圈外）
    ax.annotate(f"{num}", xy=(ts, y), xytext=(0, dy), textcoords="offset points",
                ha="center", va="center", fontsize=10.5, color="white",
                weight="bold", zorder=7,
                bbox=dict(boxstyle="circle,pad=0.32", fc=col, ec="white", lw=2.0))

ax.set_title("江淮汽车 600418（2026 年 3–10 月实际成交价）：每一根大波动都能对上新闻",
             fontsize=15.5, pad=14, weight="bold")
ax.set_ylabel("收盘价（元）", fontsize=11)
ax.legend(loc="lower left", frameon=False, fontsize=10.5)
ax.grid(alpha=0.2, ls=":")
ax.tick_params(labelsize=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

# ---- 下栏：事件卡片（2 列 × 4 行），文字全部在这里
axk.set_xlim(0, 1)
axk.set_ylim(0, 1)
axk.axis("off")

COLS, ROWS = 2, 4
GAP_X, GAP_Y = 0.018, 0.030
TOP, BOT = 0.88, 0.02
cw = (1 - GAP_X * (COLS - 1)) / COLS
ch = (TOP - BOT - GAP_Y * (ROWS - 1)) / ROWS

axk.text(0.0, 0.995, "事件对照表（编号对应上图圆点）", fontsize=12, weight="bold",
         color="#1f3b73", transform=axk.transAxes, va="top")

for i, (num, d, pct, desc, sign, _dy) in enumerate(EVENTS):
    r, c = divmod(i, COLS)
    x0 = c * (cw + GAP_X)
    y0 = TOP - (r + 1) * ch - r * GAP_Y
    col = UP_C if sign > 0 else DN_C
    fc = UP_F if sign > 0 else DN_F

    card = FancyBboxPatch((x0, y0), cw, ch,
                          boxstyle="round,pad=0.004,rounding_size=0.010",
                          transform=axk.transAxes, fc=fc, ec=col, lw=1.1, alpha=0.97,
                          zorder=1)
    axk.add_patch(card)
    # 左侧竖条
    axk.add_patch(plt.Rectangle((x0, y0), 0.0045, ch, transform=axk.transAxes,
                                fc=col, ec="none", zorder=2))
    # 编号圆（用 scatter，保证是正圆而不是被拉扁的椭圆）
    bx, by = x0 + 0.030, y0 + ch / 2
    axk.scatter([bx], [by], s=330, transform=axk.transAxes,
                fc=col, ec="white", lw=1.6, zorder=3, clip_on=False)
    axk.text(bx, by, f"{num}", transform=axk.transAxes,
             ha="center", va="center", fontsize=10, color="white", weight="bold", zorder=4)
    # 第一行：日期 + 涨跌
    axk.text(x0 + 0.058, y0 + ch * 0.70, f"{d[5:]}   {pct}", transform=axk.transAxes,
             ha="left", va="center", fontsize=10.5, color="#222", weight="bold", zorder=4)
    # 第二行：说明
    axk.text(x0 + 0.058, y0 + ch * 0.29, desc, transform=axk.transAxes,
             ha="left", va="center", fontsize=9.6, color="#444", zorder=4)

fig.savefig(HERE / "fig_news_attribution.png", bbox_inches="tight", facecolor="white")
print(f"已保存 {HERE / 'fig_news_attribution.png'}")
for num, d, pct, _desc, sign, _dy in EVENTS:
    ts = pd.Timestamp(d)
    if ts in px.index:
        print(f"  #{num} {d} {pct}  close={float(px.loc[ts, 'close']):.2f}")
