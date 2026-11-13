# -*- coding: utf-8 -*-
"""画 6 张配图 + 封面（150dpi，中文雅黑）。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = Path(r"D:\Project\qlib\projects\q3_2026")
IMG = HERE / "img"
IMG.mkdir(exist_ok=True)
D = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
IF, JAC = D["iflytek"], D["jac"]

INK = "#1A1A1A"
GRAY = "#8A8A8A"
LGRAY = "#D8D4CE"
BG = "#FAF9F6"
ORANGE = "#E67E22"
TEAL = "#2D7F8C"
RED = "#B03A2E"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def style(ax, ygrid=True):
    ax.set_facecolor(BG)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LGRAY)
    ax.tick_params(colors=GRAY, labelsize=9)
    if ygrid:
        ax.yaxis.grid(True, color=LGRAY, lw=0.6, alpha=0.7)
        ax.set_axisbelow(True)


def save(fig, name):
    p = IMG / name
    fig.savefig(p, dpi=150, facecolor=BG, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)
    print("  ", name, p.stat().st_size // 1024, "KB")


# ---------- fig1：六行并排 ----------
def fig1():
    np_delta = (JAC["9m"]["np"] - JAC["9m"]["np_prev"]) / 1e8
    adj_delta = (JAC["9m"]["np_adj"] - JAC["9m"]["np_adj_prev"]) / 1e8
    if_delta = (IF["9m"]["np_adj"] - IF["9m"]["np_adj_prev"]) / 1e8
    rows = [
        ("营业收入", f"{IF['9m']['rev'] / 1e8:.1f} 亿", "+7.05%",
         f"{JAC['9m']['rev'] / 1e8:.1f} 亿", "+11.33%"),
        ("归母净利", f"{IF['9m']['np'] / 1e8:.2f} 亿", "+132.83%",
         f"{JAC['9m']['np'] / 1e8:.2f} 亿", f"减亏 {abs(np_delta):.2f} 亿"),
        ("扣非净利", f"{IF['9m']['np_adj'] / 1e8:.2f} 亿",
         f"亏损扩大 {abs(if_delta):.2f} 亿",
         f"{JAC['9m']['np_adj'] / 1e8:.2f} 亿", f"亏损收窄 {abs(adj_delta):.2f} 亿"),
        ("非经常性损益", "+7.85 亿", "是归母净利 35.9 倍",
         "+3.25 亿", "其中政府补助 2.51 亿"),
        ("经营现金流", f"{IF['9m']['ocf'] / 1e8:.2f} 亿", "+115.28%",
         f"{JAC['9m']['ocf'] / 1e8:.2f} 亿", "去年 -24.48 亿"),
        ("研发费用", f"{IF['pl']['rd'][0] / 1e8:.2f} 亿", "占营收 21.2%",
         f"{JAC['pl']['rd'][0] / 1e8:.2f} 亿", "占营收 3.8%"),
    ]
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, len(rows) + 1.7)
    ax.axis("off")
    ax.set_facecolor(BG)
    LBL, V1, C1, V2, C2 = 0.10, 3.30, 3.55, 7.35, 7.60
    ax.text((V1 + C1) / 2 + 0.5, len(rows) + 0.95, "科大讯飞", ha="center",
            va="center", fontsize=13, color=ORANGE, fontweight="bold")
    ax.text((V2 + C2) / 2 + 0.5, len(rows) + 0.95, "江淮汽车", ha="center",
            va="center", fontsize=13, color=TEAL, fontweight="bold")
    ax.text(LBL, len(rows) + 0.95, "2026 年前三季度", ha="left", va="center",
            fontsize=9.5, color=GRAY)
    for i, (k, v1, c1, v2, c2) in enumerate(rows):
        y = len(rows) - i - 0.15
        ax.text(LBL, y, k, ha="left", va="center", fontsize=10.5, color=INK)
        ax.plot([LBL, 9.95], [y - 0.42, y - 0.42], color=LGRAY, lw=0.7)
        ax.text(V1, y, v1, ha="right", va="center", fontsize=13, color=INK)
        ax.text(C1, y, c1, ha="left", va="center", fontsize=8.5, color=GRAY)
        ax.text(V2, y, v2, ha="right", va="center", fontsize=13, color=INK)
        ax.text(C2, y, c2, ha="left", va="center", fontsize=8.5, color=GRAY)
    save(fig, "fig1_six_lines.png")


# ---------- fig2：讯飞 利润桥 ----------
def fig2():
    steps = [("营业利润", -2.16, "total"), ("营业外收支", 0.003, "delta"),
             ("利润总额", -2.15, "total"), ("所得税\n（收益）", 1.93, "delta"),
             ("净利润", -0.23, "total"), ("少数股东\n分担亏损", 0.45, "delta"),
             ("归母净利", 0.22, "total")]
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    style(ax)
    xs = np.arange(len(steps))
    cur = 0.0
    for i, (name, v, kind) in enumerate(steps):
        if kind == "total":
            lo, hi = min(0, v), max(0, v)
            color = INK if i == 0 else "#4A4A4A"
            cur = v
        else:
            lo, hi = (cur, cur + v) if v >= 0 else (cur + v, cur)
            color = ORANGE if v > 0 else RED
            cur = cur + v
        ax.bar(xs[i], hi - lo if hi > lo else 0.015, bottom=lo, width=0.52,
               color=color, alpha=0.95)
        lab = f"{v:+.2f}" if kind == "delta" else f"{v:.2f}"
        if v >= 0:
            ax.text(xs[i], hi + 0.07, lab, ha="center", va="bottom",
                    fontsize=10.5, color=INK)
        else:
            ax.text(xs[i], lo - 0.07, lab, ha="center", va="top",
                    fontsize=10.5, color=INK)
    ax.set_ylim(-2.75, 1.15)
    ax.set_xticks(xs)
    ax.set_xticklabels([s[0] for s in steps], fontsize=9.5, color=INK)
    ax.set_ylabel("亿元", fontsize=9, color=GRAY)
    ax.axhline(0, color=GRAY, lw=1.1)
    ax.set_title("科大讯飞：从 -2.16 亿营业利润到 +0.22 亿归母净利",
                 fontsize=12, color=INK, pad=30, loc="left")
    ax.text(0.99, 0.045, "所得税为负数 = 确认递延所得税资产，属于「未来的钱」",
            transform=ax.transAxes, ha="right", fontsize=8.5, color=GRAY)
    save(fig, "fig2_iflytek_bridge.png")


# ---------- fig3：研发 vs 非经营收益 ----------
def fig3():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.8, 4.0),
                                 gridspec_kw={"width_ratios": [1.55, 1]})
    style(a1)
    xs = np.arange(2)
    w = 0.34
    rd = [IF["pl"]["rd"][1] / 1e8, IF["pl"]["rd"][0] / 1e8]
    no = [IF["nonop_sum"][1], IF["nonop_sum"][0]]
    b1 = a1.bar(xs - w / 2, rd, w, color=ORANGE, label="研发费用")
    b2 = a1.bar(xs + w / 2, no, w, color="#5D6D7E",
                label="补助＋投资收益＋公允价值")
    for bs in (b1, b2):
        for r in bs:
            a1.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.7,
                    f"{r.get_height():.2f}", ha="center", fontsize=10, color=INK)
    a1.set_xticks(xs)
    a1.set_xticklabels(["2025 年前三季度", "2026 年前三季度"], fontsize=9.5, color=INK)
    a1.set_ylabel("亿元", fontsize=9, color=GRAY)
    a1.set_ylim(0, 46)
    a1.legend(frameon=False, fontsize=8.5, loc="upper left")
    a1.set_title("绝对额", fontsize=10.5, color=INK, loc="left")

    style(a2)
    names = ["研发费用", "非经营收益"]
    vals = [rd[1] - rd[0], no[1] - no[0]]
    bars = a2.barh(names, vals, height=0.42, color=[ORANGE, "#5D6D7E"])
    for r, v in zip(bars, vals):
        a2.text(v + 0.12, r.get_y() + r.get_height() / 2, f"+{v:.2f} 亿",
                va="center", fontsize=11, color=INK)
    a2.set_xlim(0, 8.6)
    a2.set_xlabel("同比增加（亿元）", fontsize=9, color=GRAY)
    a2.set_title("增量", fontsize=10.5, color=INK, loc="left")
    a2.invert_yaxis()
    fig.suptitle("多花的 6.62 亿研发，被多来的 6.07 亿「非经营收益」几乎等额补上",
                 fontsize=12, color=INK, x=0.02, ha="left", y=1.04)
    save(fig, "fig3_rd_vs_nonop.png")


# ---------- fig4：江淮 收入/毛利率/亏损 ----------
def fig4():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.9),
                                 gridspec_kw={"width_ratios": [1, 1.5]})
    style(a1, ygrid=False)
    rev = [JAC["pl"]["rev"][1] / 1e8, JAC["pl"]["rev"][0] / 1e8]
    bars = a1.bar(["2025", "2026"], rev, width=0.5, color=["#AFC7CC", TEAL])
    for b, v in zip(bars, rev):
        a1.text(b.get_x() + b.get_width() / 2, v + 8, f"{v:.0f}", ha="center",
                fontsize=11, color=INK)
    a1.set_ylim(0, 420)
    a1.set_title("营业收入（亿元）", fontsize=10.5, color=INK, loc="left")
    a1.text(1, rev[1] - 60, "+11.33%", ha="center", color="white", fontsize=10)

    style(a2)
    xs = np.arange(2)
    gm = list(JAC["gm"][::-1])
    ax2 = a2
    b = ax2.bar(xs, gm, width=0.42, color=TEAL, alpha=0.9)
    for r, v in zip(b, gm):
        ax2.text(r.get_x() + r.get_width() / 2, v + 0.25, f"{v:.2f}%",
                 ha="center", fontsize=11, color=INK)
    ax2.set_ylim(0, 15)
    ax2.set_xticks(xs)
    ax2.set_xticklabels(["2025 前三季", "2026 前三季"], fontsize=10, color=INK)
    ax2.set_title("毛利率：+1.31 个百分点", fontsize=10.5, color=INK, loc="left")
    ax2.annotate("高端新能源乘用车销量同比增加", xy=(0.92, gm[1] + 0.32),
                 xytext=(0.10, 14.3), fontsize=8.5, color=GRAY,
                 arrowprops=dict(arrowstyle="->", color=LGRAY, lw=1,
                                 connectionstyle="arc3,rad=0.18"))
    save(fig, "fig4_jac_margin.png")


# ---------- fig5：江淮 现金流 ----------
def fig5():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 4.0))
    style(a1)
    xs = np.arange(2)
    ocf = [JAC["cf"]["ocf"][1] / 1e8, JAC["cf"]["ocf"][0] / 1e8]
    b = a1.bar(xs, ocf, width=0.5, color=[RED, "#8E2F26"])
    for r, v in zip(b, ocf):
        a1.text(r.get_x() + r.get_width() / 2, v - 1.4, f"{v:.2f}",
                ha="center", va="top", fontsize=11, color=INK)
    a1.set_ylim(-60, 6)
    a1.axhline(0, color=GRAY, lw=1)
    a1.set_xticks(xs)
    a1.set_xticklabels(["2025 前三季", "2026 前三季"], fontsize=9.5, color=INK)
    a1.set_ylabel("亿元", fontsize=9, color=GRAY)
    a1.set_title("经营活动现金流净额", fontsize=10.5, color=INK, loc="left")
    a1.set_xlabel("同比多流出 24.30 亿", fontsize=9, color=GRAY, labelpad=8)

    style(a2)
    buy = [JAC["cf"]["buy_goods"][1] / 1e8, JAC["cf"]["buy_goods"][0] / 1e8]
    b2 = a2.bar(xs, buy, width=0.5, color=["#AFC7CC", TEAL])
    for r, v in zip(b2, buy):
        a2.text(r.get_x() + r.get_width() / 2, v + 4, f"{v:.1f}",
                ha="center", fontsize=11, color=INK)
    a2.set_ylim(0, 370)
    a2.set_xticks(xs)
    a2.set_xticklabels(["2025 前三季", "2026 前三季"], fontsize=9.5, color=INK)
    a2.set_ylabel("亿元", fontsize=9, color=GRAY)
    a2.set_title("购买商品、接受劳务支付的现金", fontsize=10.5, color=INK, loc="left")
    a2.set_xlabel("同比多付 77.30 亿", fontsize=9, color=TEAL, labelpad=8)
    fig.suptitle("江淮汽车：多付了 77 亿货款，现金流从 -24.5 亿走到 -48.8 亿",
                 fontsize=12, color=INK, x=0.02, ha="left", y=1.03)
    save(fig, "fig5_jac_cash.png")


# ---------- fig6：归一化股价 ----------
def fig6():
    fig, ax = plt.subplots(figsize=(9.6, 4.7))
    style(ax)
    names = {"SZ002230": ("科大讯飞", ORANGE, 2.0),
             "SH600418": ("江淮汽车", TEAL, 2.0),
             "SH000300": ("沪深 300", "#9AA0A6", 1.6)}
    for code, (nm, c, lw) in names.items():
        s = D["series"][code]
        base = s[0][1]
        ax.plot([x[0] for x in s], [(x[1] / base - 1) * 100 for x in s],
                label=f"{nm} {D['price'][code]['chg_since_0915']:+.2f}%",
                color=c, lw=lw)
    ax.axhline(0, color=LGRAY, lw=0.9)
    ax.set_ylim(-14, 50)

    events = [("2026-10-20", "讯飞三季报 10-20", 45.0, "center"),
              ("2026-10-22", "星火发布会 10-22", 41.0, "left"),
              ("2026-10-30", "江淮三季报 10-31", 45.0, "right")]
    for dt, txt, y, ha in events:
        ax.axvline(dt, color="#C9C4BC", ls=":", lw=1)
        ax.text(dt, y, txt, fontsize=8.2, color=GRAY, ha=ha, va="center")

    peak = max(D["series"]["SH600418"], key=lambda x: x[1])
    ax.annotate(f"9-30 收 {peak[1]:.2f}（月内高点）", xy=(peak[0], 42.5),
                xytext=("2026-09-24", 47.5), fontsize=8.2, color=TEAL,
                arrowprops=dict(arrowstyle="->", color=TEAL, lw=0.9,
                                connectionstyle="arc3,rad=0.15"))

    ticks = [x[0] for x in D["series"]["SH000300"]][::4]
    ax.set_xticks(ticks)
    ax.set_xticklabels([t[5:] for t in ticks], fontsize=8.5)
    ax.set_ylabel("相对 9-15 收盘涨跌（%）", fontsize=9, color=GRAY)
    ax.legend(frameon=False, fontsize=9, loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=3, handlelength=1.6)
    ax.set_title("一个月里市场跌 10.4%：江淮先冲 42% 再全吐回去，讯飞贴着大盘走",
                 fontsize=11.5, color=INK, pad=14, loc="left")
    save(fig, "fig6_price.png")


# ---------- cover ----------
def cover():
    fig = plt.figure(figsize=(7.2, 5.76))
    fig.patch.set_facecolor("#141414")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#141414")
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.08, 0.90, "两份三季报", fontsize=30, color="white", fontweight="bold")
    ax.text(0.08, 0.79, "利润是「修」出来的，现金流是「花」出去的",
            fontsize=13.5, color="#B9B4AC")
    ax.plot([0.08, 0.92], [0.72, 0.72], color="#3A3A3A", lw=1)
    ax.text(0.08, 0.55, "+2190 万", fontsize=34, color="#F0A04B", fontweight="bold")
    ax.text(0.08, 0.47, "科大讯飞 前三季度归母净利", fontsize=10.5, color="#8F8A84")
    ax.text(0.56, 0.55, "-11.41 亿", fontsize=34, color="#7FB3BD", fontweight="bold")
    ax.text(0.56, 0.47, "江淮汽车 前三季度归母净利", fontsize=10.5, color="#8F8A84")
    ax.text(0.08, 0.32, "一个靠 7.85 亿非经常性收益把 -7.63 亿扣非抹平", fontsize=11.5,
            color="#D8D4CE")
    ax.text(0.08, 0.25, "一个靠高端车毛利把亏损收了 2.93 亿，代价是 48.8 亿现金流出",
            fontsize=11.5, color="#D8D4CE")
    ax.text(0.08, 0.12, "2026 年三季报 · 代码与数字均取自公告原文", fontsize=9,
            color="#6E6A66")
    fig.savefig(IMG / "cover.png", dpi=150, facecolor="#141414")
    plt.close(fig)
    print("   cover.png", (IMG / "cover.png").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    print("生成配图:")
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, cover):
        f()

