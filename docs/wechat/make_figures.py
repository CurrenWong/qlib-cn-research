"""生成公众号文章配图（6 张）。

数据来源：
  - 价格：D:\\Project\\qlib\\qlib_data\\cn_data_2026（直接读 .bin，不经 qlib）
  - 回测结果：projects/jac_600418/results_A|B|C 的 metrics.csv / summary.json / nav_test.csv

输出：docs/wechat/img/*.png
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["axes.edgecolor"] = "#BBBBBB"
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.color"] = "#E8E8E8"
plt.rcParams["grid.linewidth"] = 0.8

ROOT = Path(r"D:\Project\qlib")
PROJ = ROOT / "projects" / "jac_600418"
DATA = ROOT / "qlib_data" / "cn_data_2026"
OUT = ROOT / "docs" / "wechat" / "img"
OUT.mkdir(parents=True, exist_ok=True)

C_STRAT, C_ZERO, C_BENCH, C_STOCK = "#C0392B", "#E67E22", "#2C3E50", "#27AE60"


def read_close(code: str) -> pd.Series:
    cal = [x.strip() for x in (DATA / "calendars" / "day.txt").read_text().splitlines() if x.strip()]
    arr = np.fromfile(DATA / "features" / code / "close.day.bin", dtype=np.float32)
    si, vals = int(arr[0]), arr[1:]
    idx = pd.to_datetime(cal[si: si + len(vals)])
    return pd.Series(vals, index=idx).loc["2002-01-01":]


# ---------------------------------------------------------------- fig0 价格全景
stock = read_close("sh600418")
bench = read_close("sh000300")
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.plot(stock.index, stock.values, lw=1.1, color=C_STOCK, label="江淮汽车 600418（前复权）")
ax.set_yscale("log")
ax.set_ylabel("收盘价（对数轴）")
ax.set_title("江淮汽车 2002–2026：三套切分的测试期落在哪些区间", fontsize=14, pad=12)
spans = [("2020-01-01", "2026-10-26", "方案 A 测试期", 0.55),
         ("2023-01-01", "2026-10-26", "方案 B", 0.28),
         ("2021-01-01", "2026-10-26", "方案 C", 0.05)]
for s, e, lbl, y in spans:
    a = ax.axvspan(pd.Timestamp(s), pd.Timestamp(e), color=C_STRAT, alpha=0.07 + 0.03 * y, lw=0)
ax.annotate("2019–2020\n原测试期", xy=(pd.Timestamp("2019-06-01"), 3.2), fontsize=9,
            color="#7F8C8D", ha="center")
ax.annotate("2020–2026\n方案 A 测试期（6.5 年）", xy=(pd.Timestamp("2023-06-01"), 12),
            fontsize=10, color=C_STRAT, ha="center", fontweight="bold")
ax.annotate("期间涨约 3 倍", xy=(pd.Timestamp("2026-01-01"), 4.6), fontsize=10, color=C_STOCK)
ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
fig.tight_layout()
fig.savefig(OUT / "fig0_stock_path.png")
plt.close(fig)
print("fig0 ok")

# ---------------------------------------------------------------- fig1 qlib 五层架构
fig, ax = plt.subplots(figsize=(11, 5.8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")
ax.grid(False)

layers = [
    ("① 数据层 Data", "二进制 .bin + 交易日历 + 标的表\nD.features() 一次取全价量", "#34495E"),
    ("② 特征层 Expression", "表达式引擎 + Handler\n21 个因子一条表达式算完", "#16A085"),
    ("③ 模型层 Model", "Ridge / LightGBM / LSTM…\n统一 fit / predict 接口", "#2980B9"),
    ("④ 策略层 Strategy", "分数 → 目标权重\n本策略：分数阈值 + MA20 趋势", "#8E44AD"),
    ("⑤ 回测执行层 Executor", "撮合、成本、涨跌停、停牌\n输出 report + 持仓明细", "#C0392B"),
]
top, h, gap = 9.7, 1.45, 0.35
for i, (name, desc, color) in enumerate(layers):
    y = top - i * (h + gap)
    ax.add_patch(mpatches.FancyBboxPatch((0.3, y - h), 6.0, h,
                                         boxstyle="round,pad=0.05", fc=color, ec="none", alpha=0.93))
    ax.text(0.55, y - 0.30, name, fontsize=12.5, color="white", fontweight="bold", va="center")
    ax.text(0.55, y - 0.95, desc, fontsize=9.5, color="#ECF0F1", va="center")
    if i < len(layers) - 1:
        ax.annotate("", xy=(3.3, y - h - gap + 0.04), xytext=(3.3, y - h - 0.04),
                    arrowprops=dict(arrowstyle="-|>", color="#7F8C8D", lw=1.5))

ax.text(3.3, 0.45, "一次 import，从 .bin 一路走到成交明细", fontsize=10,
        color="#7F8C8D", ha="center", style="italic")

# 右侧：数据目录
ax.add_patch(mpatches.FancyBboxPatch((6.8, 1.1), 3.0, 8.6,
                                     boxstyle="round,pad=0.08", fc="#F8F9F9", ec="#D5DBDB"))
ax.text(7.0, 9.35, "cn_data_2026 目录结构", fontsize=10.5, fontweight="bold", color="#2C3E50")
rows = [
    ("calendars/day.txt", "6497 个交易日", 0),
    ("instruments/all.txt", "6172 条标的", 0),
    ("features/sh600418/", "每个字段一个 .bin", 0),
    ("close.day.bin", "收盘（已复权）", 1),
    ("volume.day.bin", "成交量", 1),
    ("factor.day.bin", "复权因子", 1),
]
yy = 8.85
for path, note, ind in rows:
    ax.text(7.05 + ind * 0.18, yy, path, fontsize=8.4, va="center",
            family="DejaVu Sans", color="#34495E", fontweight="bold" if ind == 0 else "normal")
    ax.text(8.62, yy, "· " + note, fontsize=8.2, va="center", color="#7F8C8D")
    yy -= 0.52
ax.text(7.05, 5.4, ".bin 的格式：float32 数组，\n首元素是起始下标，其后才\n是数据——不对齐日历就会\n把停牌日的价格错位。",
        fontsize=8.6, va="top", color="#566573", linespacing=1.5)
ax.text(7.05, 3.35, "复权因子单独一个文件：\n所有价格 = 原始价 × factor。\n这是 qlib 最容易被误解、\n也最容易踩坑的地方。",
        fontsize=8.6, va="top", color="#7F8C8D", linespacing=1.5)
fig.tight_layout()
fig.savefig(OUT / "fig1_qlib_arch.png")
plt.close(fig)
print("fig1 ok")

# ---------------------------------------------------------------- 读三方案结果
splits, metas = {}, {}
for k in "ABC":
    d = PROJ / f"results_{k}"
    m = pd.read_csv(d / "metrics.csv")
    splits[k] = m[m["区间"] == "测试集"].set_index("标的")
    metas[k] = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    metas[k]["choice"] = json.loads((d / "strategy_choice.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- fig2 方案A 净值
nav = pd.read_csv(PROJ / "results_A" / "nav_test.csv", index_col=0, parse_dates=True)
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.plot(nav.index, nav["买入持有江淮"], lw=1.4, color=C_STOCK, label="买入持有江淮汽车")
ax.plot(nav.index, nav["沪深300"], lw=1.4, color=C_BENCH, label="沪深300")
ax.plot(nav.index, nav["策略"], lw=1.8, color=C_STRAT, label="择时策略（含成本）")
ax.axhline(1.0, color="#999999", lw=0.9, ls="--")
ax.set_ylabel("净值（起点 = 1）")
ax.set_title("方案 A 测试期 2020-01 ~ 2026-10（6.5 年）：股票涨 3 倍，策略原地踏步", fontsize=13, pad=12)
ax.legend(loc="upper left", fontsize=10, framealpha=0.92)
for col, c in [("策略", C_STRAT), ("买入持有江淮", C_STOCK), ("沪深300", C_BENCH)]:
    ax.annotate(f"{nav[col].iloc[-1]:.2f}", xy=(nav.index[-1], nav[col].iloc[-1]),
                xytext=(6, 0), textcoords="offset points", fontsize=9.5, color=c, va="center")
fig.tight_layout()
fig.savefig(OUT / "fig2_nav_A.png")
plt.close(fig)
print("fig2 ok")

# ---------------------------------------------------------------- fig3 三方案年化对比
labels = ["策略\n（含成本）", "策略\n（零成本对照）", "沪深300", "买入持有江淮"]
keys = ["策略（择时）", "策略（零成本对照）", "沪深300", "买入持有江淮汽车"]
colors = [C_STRAT, C_ZERO, C_BENCH, C_STOCK]
x = np.arange(len(labels))
w = 0.26
fig, ax = plt.subplots(figsize=(11, 5.2))
for i, (k, name) in enumerate(zip("ABC", ["方案 A（2020–2026，6.5 年）",
                                          "方案 B（2023–2026，3.7 年）",
                                          "方案 C（2021–2026，5.6 年）"])):
    vals = [splits[k].loc[kk, "年化收益"] * 100 for kk in keys]
    bars = ax.bar(x + (i - 1) * w, vals, w, label=name, edgecolor="white", lw=0.6,
                  color=["#C0392B", "#E74C3C", "#EC7063"][i])
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:+.1f}", xy=(b.get_x() + b.get_width() / 2, v),
                    xytext=(0, 3 if v >= 0 else -11), textcoords="offset points",
                    ha="center", fontsize=8.2,
                    color="#2C3E50" if v >= 0 else "#922B21")
ax.axhline(0, color="#666666", lw=1)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel("年化收益（%）")
ax.set_title("三套切分的测试期年化收益：策略 vs 零成本 vs 指数 vs 买入持有", fontsize=13, pad=12)
ax.legend(fontsize=9.5, framealpha=0.92, loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "fig3_three_splits.png")
plt.close(fig)
print("fig3 ok")

# ---------------------------------------------------------------- fig4 成本拖累
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
xs = np.arange(3)
zero = [splits[k].loc["策略（零成本对照）", "年化收益"] * 100 for k in "ABC"]
cost = [splits[k].loc["策略（择时）", "年化收益"] * 100 for k in "ABC"]
ax.bar(xs - 0.19, zero, 0.36, label="零成本对照", color=C_ZERO, edgecolor="white")
ax.bar(xs + 0.19, cost, 0.36, label="含成本（实际）", color=C_STRAT, edgecolor="white")
for i, (z, c) in enumerate(zip(zero, cost)):
    ax.annotate(f"{z:+.2f}%", xy=(i - 0.19, z), xytext=(0, 3), textcoords="offset points",
                ha="center", fontsize=9, color="#935116")
    ax.annotate(f"{c:+.2f}%", xy=(i + 0.19, c), xytext=(0, -12), textcoords="offset points",
                ha="center", fontsize=9, color="#7B241C")
    ax.annotate(f"成本拖累\n{z - c:.2f}pct/年", xy=(i, -11.5), ha="center", fontsize=9,
                color="#7F8C8D", linespacing=1.4)
ax.set_ylim(-13, 7.5)
ax.axhline(0, color="#666666", lw=1)
ax.set_xticks(xs)
ax.set_xticklabels(["方案 A", "方案 B", "方案 C"], fontsize=10)
ax.set_ylabel("年化收益（%）")
ax.set_title("同一策略、同一信号，只把交易成本设为 0", fontsize=11.5)

ax = axes[1]
turn = [splits[k].loc["策略（择时）", "年化换手"] for k in "ABC"]
expense = [splits[k].loc["策略（择时）", "总成本"] / 1e6 * 100 for k in "ABC"]
b = ax.bar(xs, turn, 0.45, color="#5D6D7E", edgecolor="white")
for bb, t, e in zip(b, turn, expense):
    ax.annotate(f"{t:.1f}x", xy=(bb.get_x() + bb.get_width() / 2, t), xytext=(0, 3),
                textcoords="offset points", ha="center", fontsize=10, color="#2C3E50")
    ax.annotate(f"累计成本\n{e:.0f}% 本金", xy=(bb.get_x() + bb.get_width() / 2, t * 0.5),
                ha="center", fontsize=8.5, color="white")
ax.set_xticks(xs)
ax.set_xticklabels(["方案 A", "方案 B", "方案 C"], fontsize=10)
ax.set_ylabel("年化换手（倍 / 年）")
ax.set_title("三套方案都选出「不平滑」，换手都是 49 倍", fontsize=11.5)
_h, _l = axes[0].get_legend_handles_labels()
fig.legend(_h, _l, loc="lower center", ncol=2, frameon=False, fontsize=10)
fig.tight_layout(rect=[0, 0.055, 1, 1])
fig.savefig(OUT / "fig4_cost_drag.png")
plt.close(fig)
print("fig4 ok")

# ---------------------------------------------------------------- fig5 IC 衰减
fig, ax = plt.subplots(figsize=(9.5, 4.6))
stages = ["训练集", "验证集", "测试集"]
ic_colors = ["#5DADE2", "#F5B041", "#C0392B"]
w = 0.24
for i, k in enumerate("ABC"):
    vals = [metas[k]["ic"][s]["IC"] for s in ["train", "valid", "test"]]
    bars = ax.bar(np.arange(3) + (i - 1) * w, vals, w, label=f"方案 {k}", edgecolor="white",
                  color=["#85C1E9", "#F8C471", "#E6B0AA"][i])
    for bb, v in zip(bars, vals):
        ax.annotate(f"{v:+.4f}", xy=(bb.get_x() + bb.get_width() / 2, v),
                    xytext=(0, 3 if v >= 0 else -12), textcoords="offset points",
                    ha="center", fontsize=8, color="#34495E")
ax.axhline(0, color="#666666", lw=1.2)
ax.set_xticks(np.arange(3))
ax.set_xticklabels(stages, fontsize=11)
ax.set_ylabel("IC（分数与次日收益的相关系数）")
ax.set_title("样本内 IC +0.10 ~ +0.12，出了样本全部归零", fontsize=13, pad=12)
ax.legend(fontsize=9.5, framealpha=0.92, loc="lower left")
fig.tight_layout()
fig.savefig(OUT / "fig5_ic_decay.png")
plt.close(fig)
print("fig5 ok")

print("\n输出目录:", OUT)
for p in sorted(OUT.glob("*.png")):
    print(f"  {p.name}  {p.stat().st_size / 1024:.0f} KB")
