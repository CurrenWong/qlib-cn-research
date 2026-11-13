"""公众号文章配图：新闻归因方法 + 两个标的结果（6 张图）。

数据：
  - 价格：qlib cn_data_2026 的 adjclose（归一化对比用）
  - 归因：projects/jac_600418/news_attribution 与 projects/iflytek_002230/news_attribution
  - 对比：docs/wechat_attrib/comparison.json

输出：docs/wechat_attrib/img/*.png
"""

from __future__ import annotations

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
DATA = ROOT / "qlib_data" / "cn_data_2026"
JAC = ROOT / "projects" / "jac_600418" / "news_attribution"
IFLY = ROOT / "projects" / "iflytek_002230" / "news_attribution"
OUT = ROOT / "docs" / "wechat_attrib" / "img"
OUT.mkdir(parents=True, exist_ok=True)

NAVY, ORANGE, GREY, RED = "#1F3B73", "#E67E22", "#B0B0B0", "#C0392B"
W = 7.2  # 图宽（英寸），150dpi → 1080px


def cal():
    return [x.strip() for x in (DATA / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load(sym, field="adjclose"):
    c = cal()
    arr = np.fromfile(DATA / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    s = int(arr[0])
    return pd.Series(arr[1:], index=pd.to_datetime(c[s: s + len(arr) - 1]), dtype="float64")


CMP = json.loads((ROOT / "docs" / "wechat_attrib" / "comparison.json").read_text(encoding="utf-8"))
JAC_D, IFLY_D = CMP["600418"], CMP["002230"]


# ============================================================ 图0：方法流水线
def fig0():
    fig, ax = plt.subplots(figsize=(W, 3.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    steps = [
        ("① 事件识别", "L1 绝对涨跌 ≥ 5%\nL2 超额 ≥ 4%\nL3 涨跌停 ≥ 9.5%\n（超额均相对沪深300）", NAVY),
        ("② 数据校验", "qlib 前复权 vs\n新浪前复权逐日对账\n剔掉除权造成的假事件", "#2C3E50"),
        ("③ 候选池", "T-1 / T 日公告\nT 盘前 / T 盘中新闻\n（巨潮 + 东财）", "#3D5A80"),
        ("④ 因果判定", "区分「事前证据」\n与「事后报道」\n按类别打分排序", ORANGE),
    ]
    w, gap = 0.212, 0.038
    for i, (t, d, col) in enumerate(steps):
        x = 0.019 + i * (w + gap)
        ax.add_patch(mpatches.FancyBboxPatch((x, 0.42), w, 0.44,
                                             boxstyle="round,pad=0.006,rounding_size=0.012",
                                             fc="white", ec=col, lw=2.0, zorder=2))
        ax.add_patch(mpatches.FancyBboxPatch((x, 0.78), w, 0.085,
                                             boxstyle="round,pad=0.004,rounding_size=0.010",
                                             fc=col, ec=col, zorder=3))
        ax.text(x + w / 2, 0.822, t, ha="center", va="center", color="white",
                fontsize=12, weight="bold", zorder=4)
        ax.text(x + w / 2, 0.635, d, ha="center", va="center", color="#333",
                fontsize=8.6, linespacing=1.75, zorder=4)
        if i < 3:
            ax.annotate("", xy=(x + w + gap - 0.006, 0.64), xytext=(x + w + 0.006, 0.64),
                        arrowprops=dict(arrowstyle="-|>", color="#999", lw=1.8))

    ax.add_patch(mpatches.FancyBboxPatch((0.012, 0.10), 0.976, 0.26,
                                         boxstyle="round,pad=0.006,rounding_size=0.012",
                                         fc="#FFF8F0", ec="#E8D5BE", lw=1.2, zorder=1))
    ax.text(0.028, 0.315, "三个关键设计", fontsize=11.5, weight="bold", color=ORANGE, va="center")
    notes = [
        "① 事后报道 ≠ 原因：收盘后/T+1 的新闻单列，不参与归因打分",
        "② 证据强度排序：标题点名「江淮/讯飞」的强于列表类点名文章，泛行业综述降权",
        "③ 交叉校验：除权日会造出「假跌停」，必须用第二个行情源逐日对账后再进归因",
    ]
    for i, n in enumerate(notes):
        ax.text(0.028, 0.245 - i * 0.062, n, fontsize=10, color="#555", va="center")

    ax.set_title("新闻归因流水线：把「为什么涨了」拆成可复核的四步",
                 fontsize=14, weight="bold", pad=8, color="#111")
    fig.tight_layout()
    fig.savefig(OUT / "fig0_pipeline.png", facecolor="white")
    plt.close(fig)


# ============================================================ 图1：两标的全景
def fig1():
    fig, ax = plt.subplots(figsize=(W, 3.9))
    pj, pi = load("sh600418"), load("sz002230")
    b = load("sh000300", "close")
    start = "2008-05-13"
    pj, pi, b = pj.loc[start:], pi.loc[start:], b.loc[start:]
    df = pd.DataFrame({"j": pj, "i": pi, "b": b}).dropna()
    df = df / df.iloc[0] * 100

    ev_j = pd.read_csv(JAC / "events.csv")
    ev_i = pd.read_csv(IFLY / "events.csv")
    ev_j["date"] = pd.to_datetime(ev_j["date"])
    ev_i["date"] = pd.to_datetime(ev_i["date"])

    ax.plot(df.index, df["b"], color=GREY, lw=1.3, ls="--", label="沪深300")
    ax.plot(df.index, df["i"], color=ORANGE, lw=1.6, label="科大讯飞 002230")
    ax.plot(df.index, df["j"], color=NAVY, lw=1.6, label="江淮汽车 600418")
    for e, c in [(ev_i, ORANGE), (ev_j, NAVY)]:
        up, dn = e[e["ret"] > 0], e[e["ret"] < 0]
        for sub, col in [(up, "#F0A05A"), (dn, RED)]:
            sub = sub[(sub["date"] >= start)]
            ax.scatter(sub["date"], df["i" if c == ORANGE else "j"].reindex(sub["date"]).values,
                       s=4.5, color=col, alpha=0.6, linewidths=0, zorder=4)

    ax.set_yscale("log")
    ax.set_yticks([50, 100, 200, 500, 1000])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _p: f"{v:.0f}"))
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_ylabel("归一化净值（2008-05 = 100，对数轴）", fontsize=10.5)
    ax.set_title("同一套流水线、两个标的：18 年的相对强弱一目了然", fontsize=13.5,
                 weight="bold", pad=30, color="#111")
    handles = [plt.Line2D([], [], color=NAVY, lw=1.8, label="江淮汽车 600418"),
               plt.Line2D([], [], color=ORANGE, lw=1.8, label="科大讯飞 002230"),
               plt.Line2D([], [], color=GREY, lw=1.4, ls="--", label="沪深300"),
               mpatches.Patch(color="#F0A05A", label="上涨事件"),
               mpatches.Patch(color=RED, label="下跌事件")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.10),
              frameon=False, fontsize=9.4, ncol=5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=9.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_panorama.png", facecolor="white")
    plt.close(fig)


# ============================================================ 图2：证据率
def fig2():
    eras = ["2001-2019(仅公告)", "2020-2026(仅公告)", "2026-04起(有新闻)"]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.9))
    for ax, rec, col, name in [(axes[0], JAC_D, NAVY, "江淮汽车 600418"),
                               (axes[1], IFLY_D, ORANGE, "科大讯飞 002230")]:
        rates = [rec["分时期证据率"][e]["有证据率%"] for e in eras]
        ns = [rec["分时期证据率"][e]["n"] for e in eras]
        xs = np.arange(3)
        bars = ax.bar(xs, rates, width=0.56, color=col, alpha=0.9)
        for b, r, n in zip(bars, rates, ns):
            ax.text(b.get_x() + b.get_width() / 2, r + 2, f"{r}%",
                    ha="center", fontsize=10, weight="bold", color=col)
            ax.text(b.get_x() + b.get_width() / 2, 3, f"n={n}", ha="center",
                    fontsize=8.6, color="white")
        ax.set_xticks(xs)
        ax.set_xticklabels(["2001-2019\n仅公告", "2020-2026\n仅公告", "2026-04 起\n有新闻"],
                           fontsize=9.2)
        ax.set_ylim(0, 108)
        ax.set_title(f"{name}\n有事前证据率 {rec['有证据率%']}%", fontsize=11.5, weight="bold",
                     color=col, pad=8)
        ax.grid(axis="x", visible=False)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("能找到事前证据的事件占比", fontsize=9.8)
    fig.suptitle("「找不到理由」多半是「没地方找」：新闻源只回溯到 2026-04",
                 fontsize=13.5, weight="bold", y=1.04, color="#111")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_evidence.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


# ============================================================ 图3：类别事件研究
def fig3():
    cats = ["分红派息", "业绩/财报", "股东行为", "资本运作", "人事治理",
            "风险/监管", "合作/新产品", "股权激励"]
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.3), sharey=True)
    for ax, rec, col, name in [(axes[0], JAC_D, NAVY, "江淮汽车 600418"),
                               (axes[1], IFLY_D, ORANGE, "科大讯飞 002230")]:
        st = rec["类别事件研究"]
        ys = np.arange(len(cats))[::-1]
        tick_labels = []
        for y, c in zip(ys, cats):
            if c not in st:
                tick_labels.append(c)
                continue
            t1 = st[c]["T1"]
            n = st[c]["n"]
            tick_labels.append(f"{c} (n={n})")
            ax.barh(y, t1, height=0.56, color=col, alpha=0.88)
            if t1 >= 0:
                ax.text(t1 + 0.05, y, f"{t1:+.2f}%", va="center", ha="left",
                        fontsize=9.2, weight="bold", color=col)
            else:
                ax.text(t1 - 0.05, y, f"{t1:+.2f}%", va="center", ha="right",
                        fontsize=9.2, weight="bold", color=col)
        ax.axvline(0, color="#666", lw=1.0)
        ax.set_yticks(ys)
        ax.set_yticklabels(tick_labels, fontsize=9.2)
        ax.set_xlim(-1.35, 1.35)
        ax.set_title(name, fontsize=11.5, weight="bold", color=col, pad=8)
        ax.grid(axis="y", visible=False)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_xlabel("公告后次日（T+1）相对沪深300 超额收益 %", fontsize=9.8)
    fig.suptitle("同一类公告，两个标的的次日超额：都不稳定，方向还常常相反",
                 fontsize=13.5, weight="bold", y=1.03, color="#111")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_categories.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


# ============================================================ 图4：涨跌停赚钱效应
def fig4():
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.3))
    for ax, rec, col, name in [(axes[0], JAC_D, NAVY, "江淮汽车 600418"),
                               (axes[1], IFLY_D, ORANGE, "科大讯飞 002230")]:
        lim = rec["涨跌停"]
        t1 = [lim["涨停"]["T1超额%"], lim["跌停"]["T1超额%"]]
        t5 = [lim["涨停"]["T5超额%"], lim["跌停"]["T5超额%"]]
        t20 = [lim["涨停"]["T20超额%"], lim["跌停"]["T20超额%"]]
        w1 = [lim["涨停"]["T1胜率%"], lim["跌停"]["T1胜率%"]]
        w20 = [lim["涨停"]["T20胜率%"], lim["跌停"]["T20胜率%"]]
        labels = [f"涨停 n={lim['涨停']['n']}\nT+1 胜率 {w1[0]}%\nT+20 胜率 {w20[0]}%",
                  f"跌停 n={lim['跌停']['n']}\nT+1 胜率 {w1[1]}%\nT+20 胜率 {w20[1]}%"]
        x = np.arange(2)
        w = 0.26
        ax.bar(x - w, t1, w, color=col, alpha=0.95, label="T+1 超额%")
        ax.bar(x, t5, w, color=col, alpha=0.6, label="T+5 超额%")
        ax.bar(x + w, t20, w, color=col, alpha=0.32, label="T+20 超额%")
        for xi, (a, c) in enumerate(zip(t1, t20)):
            ax.text(xi - w, a + (0.08 if a >= 0 else -0.08), f"{a:+.2f}", ha="center",
                    va="bottom" if a >= 0 else "top", fontsize=8.8, weight="bold", color=col)
            ax.text(xi + w, c + (0.08 if c >= 0 else -0.08), f"{c:+.2f}", ha="center",
                    va="bottom" if c >= 0 else "top", fontsize=8.8, color="#888")
        ax.axhline(0, color="#666", lw=1.0)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8.8)
        ax.set_ylim(-2.75, 2.9)
        ax.set_title(name, fontsize=11.5, weight="bold", color=col, pad=8)
        ax.grid(axis="x", visible=False)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("相对沪深300 超额收益 %", fontsize=9.8)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=9.0, frameon=False, loc="upper center",
               bbox_to_anchor=(0.5, 1.0), ncol=3)
    fig.suptitle("涨停的动量活不过 20 天，跌停的杀伤力两个标的都成立",
                 fontsize=13.5, weight="bold", y=1.07, color="#111")
    fig.tight_layout()
    fig.savefig(OUT / "fig4_limit.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


# ============================================================ 图5：利好出尽时间线
def fig5():
    ev = pd.read_csv(IFLY / "events.csv")
    mt = pd.read_csv(IFLY / "news_matches.csv")
    mt["event_date"] = mt["event_date"].astype(str)
    ev["date"] = ev["date"].astype(str)
    m = ev.merge(mt[["event_date", "primary_title", "primary_relation", "primary_category"]],
                 left_on="date", right_on="event_date", how="left")

    picks = [
        ("2023-01-30", "业绩预告", "当日涨停"),
        ("2023-04-21", "年报披露", "当天跌 9.2%"),
        ("2023-08-16", "星火发布会", "次日跌 8.6%"),
        ("2023-10-24", "1024 开发者节", "节前跌停"),
        ("2026-01-29", "业绩预告", "当日涨 6.4%"),
    ]
    fig, ax = plt.subplots(figsize=(W, 2.9))
    ax.set_xlim(-0.62, len(picks) - 0.38)
    ax.set_ylim(-0.92, 0.92)
    ax.axis("off")
    ax.plot([-0.42, len(picks) - 0.58], [0, 0], color="#D5D5D5", lw=2.4, zorder=1)

    for i, (d, title, note) in enumerate(picks):
        row = m[m["date"] == d]
        ret = float(row["ret"].iloc[0]) if len(row) else 0.0
        col = ORANGE if ret > 0 else RED
        sgn = 1 if ret > 0 else -1
        va = "bottom" if sgn > 0 else "top"
        ax.plot([i, i], [0, 0.10 * sgn], color=col, lw=1.4, zorder=2)
        ax.scatter([i], [0], s=85, color=col, zorder=3, edgecolors="white", linewidths=1.6)
        ax.text(i, 0.12 * sgn, title, ha="center", va=va, fontsize=8.8, color="#444", zorder=4)
        ax.text(i, 0.23 * sgn, d, ha="center", va=va, fontsize=8.0, color="#999", zorder=4)
        ax.text(i, 0.34 * sgn, f"{ret:+.1f}%", ha="center", va=va, fontsize=13.5,
                color=col, weight="bold", zorder=4)
        ax.text(i, 0.60 * sgn, note, ha="center", va=va, fontsize=9.0,
                color=col, weight="bold", zorder=4)
    ax.set_title("科大讯飞「利好出尽」实录：好公告在预期打满之后，就变成了利空",
                 fontsize=13.5, weight="bold", pad=16, color="#111")
    fig.tight_layout()
    fig.savefig(OUT / "fig5_goodnews.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


# ============================================================ 图6：江淮事件走势图
def fig6_jac():
    """江淮汽车 2018-2026 实际成交价 + 8 个带归因的关键事件（编号圆 + 事件卡片）。"""
    d = ROOT / "projects" / "jac_600418" / "news_attribution"
    px = pd.read_csv(d / "price_cache.csv", parse_dates=["date"]).set_index("date").sort_index()
    px = px.loc["2018-01-01": "2026-10-29"]

    ev = pd.read_csv(d / "events.csv")
    ev["date"] = ev["date"].astype(str)
    mt = pd.read_csv(d / "news_matches.csv")
    mt["event_date"] = mt["event_date"].astype(str)
    m = ev.merge(mt[["event_date", "primary_title", "primary_category"]],
                 left_on="date", right_on="event_date", how="left")

    # (编号, 日期, 卡片事由)
    picks = [
        (1, "2018-03-23", "控股股东增持计划进展"),
        (2, "2020-06-12", "大众中国投资协议"),
        (3, "2020-11-04", "江淮大众合资进展"),
        (4, "2020-11-26", "江淮大众进展（同措辞）"),
        (5, "2020-12-03", "江淮大众交割完成"),
        (6, "2024-07-10", "半年度业绩预增"),
        (7, "2025-04-08", "控股股东拟增持"),
        (8, "2026-07-07", "首次回购 86 万股"),
    ]

    fig = plt.figure(figsize=(W, 8.2))
    gs = fig.add_gridspec(2, 1, height_ratios=[3.6, 3.2], hspace=0.30,
                          left=0.075, right=0.975, top=0.93, bottom=0.03)
    ax = fig.add_subplot(gs[0])
    axk = fig.add_subplot(gs[1])

    ax.plot(px.index, px["close"], color=NAVY, lw=1.5, zorder=3)
    # 偏移：③ ④ 相隔三周且价格几乎相同，圈会叠在一起
    OFF = {"2020-11-04": (12, 16), "2020-11-26": (-26, -18)}
    for num, dt, _ in picks:
        ts = pd.Timestamp(dt)
        if ts not in px.index:
            continue
        row = m[m["date"] == dt]
        ret = float(row["ret"].iloc[0]) if len(row) else 0.0
        col = ORANGE if ret > 0 else RED
        y = float(px.loc[ts, "close"])
        dx, dy = OFF.get(dt, (0, 0))
        ax.annotate(f"{num}", xy=(ts, y), xytext=(dx, dy), textcoords="offset points",
                    ha="center", va="center", fontsize=10.5, color="white", weight="bold",
                    zorder=7, bbox=dict(boxstyle="circle,pad=0.30", fc=col, ec="white", lw=2.0),
                    arrowprops=(dict(arrowstyle="-", color=col, lw=1.0, shrinkA=2, shrinkB=7)
                                if (dx or dy) else None))
        if not (dx or dy):
            ax.scatter([ts], [y], s=26, color=col, zorder=6, edgecolors="white", linewidths=1.2)

    ax.set_yscale("log")
    ax.set_yticks([5, 10, 20, 40, 60])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _p: f"{v:.0f}"))
    ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_ylabel("收盘价（元，对数轴）", fontsize=10.5)
    ax.set_title("江淮汽车 600418（2018-01 ~ 2026-10 实际成交价）：八个带消息的日子",
                 fontsize=14.5, weight="bold", pad=12, color="#111")
    ax.grid(alpha=0.25, ls=":", which="major")
    ax.tick_params(labelsize=9.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.text(0.995, 0.03, "橙=上涨  红=下跌", transform=ax.transAxes, ha="right",
            fontsize=9, color="#888")

    # ---- 事件卡片（2 列 × 4 行）----
    axk.set_xlim(0, 1)
    axk.set_ylim(0, 1)
    axk.axis("off")
    axk.text(0.0, 0.985, "事件对照表（编号对应上图圆点）", fontsize=11.5, weight="bold",
             color=NAVY, transform=axk.transAxes, va="top")
    COLS, ROWS = 2, 4
    GAP_X, GAP_Y = 0.016, 0.028
    TOP, BOT = 0.90, 0.01
    cw = (1 - GAP_X * (COLS - 1)) / COLS
    ch = (TOP - BOT - GAP_Y * (ROWS - 1)) / ROWS
    for i, (num, dt, note) in enumerate(picks):
        r, c = divmod(i, COLS)
        x0 = c * (cw + GAP_X)
        y0 = TOP - (r + 1) * ch - r * GAP_Y
        row = m[m["date"] == dt]
        ret = float(row["ret"].iloc[0]) if len(row) else 0.0
        exc = float(row["excess"].iloc[0]) if len(row) else 0.0
        col = ORANGE if ret > 0 else RED
        fc = "#FDF6E3" if ret > 0 else "#FDECEA"
        axk.add_patch(mpatches.FancyBboxPatch(
            (x0, y0), cw, ch, boxstyle="round,pad=0.004,rounding_size=0.008",
            transform=axk.transAxes, fc=fc, ec=col, lw=1.1, alpha=0.97, zorder=1))
        axk.add_patch(mpatches.Rectangle((x0, y0), 0.0035, ch, transform=axk.transAxes,
                                         fc=col, ec="none", zorder=2))
        bx, by = x0 + 0.024, y0 + ch / 2
        axk.scatter([bx], [by], s=250, transform=axk.transAxes, fc=col, ec="white",
                    lw=1.5, zorder=3, clip_on=False)
        axk.text(bx, by, f"{num}", transform=axk.transAxes, ha="center", va="center",
                 fontsize=9.5, color="white", weight="bold", zorder=4)
        axk.text(x0 + 0.046, y0 + ch * 0.70, f"{dt}   {ret:+.2f}%   超额{exc:+.2f}%",
                 transform=axk.transAxes, ha="left", va="center", fontsize=10.2,
                 color="#222", weight="bold", zorder=4)
        axk.text(x0 + 0.046, y0 + ch * 0.28, note, transform=axk.transAxes,
                 ha="left", va="center", fontsize=9.6, color="#444", zorder=4)

    fig.savefig(OUT / "fig6_jac_events.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)


# ============================================================ 封面
def cover():
    fig, ax = plt.subplots(figsize=(W, 4.8))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, fc="#0E2340"))
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 0.012, fc=ORANGE))
    ax.text(0.5, 0.80, "两家公司 · 1347 次大波动 · 同一套方法", ha="center", va="center",
            color="#F0A05A", fontsize=15, weight="bold")
    ax.text(0.5, 0.60, "新闻归因实验", ha="center", va="center", color="white",
            fontsize=42, weight="bold")
    ax.text(0.5, 0.44, "江淮汽车 600418  ×  科大讯飞 002230", ha="center", va="center",
            color="#C9D4E4", fontsize=16)
    ax.plot([0.30, 0.70], [0.355, 0.355], color="#3A5175", lw=1.2)
    for i, (t, s) in enumerate([
            ("1347 次事件", "逐条匹配公告与新闻"),
            ("22%~30%", "能抓到事前证据的比例"),
            ("48%~50%", "事后胜率就这么高")]):
        x = 0.17 + i * 0.33
        ax.text(x, 0.255, t, ha="center", va="center", color="#F0A05A", fontsize=21,
                weight="bold")
        ax.text(x, 0.155, s, ha="center", va="center", color="#8FA3BF", fontsize=11.5)
    ax.text(0.5, 0.06, "qlib · 巨潮公告 · 东财新闻 · 新浪行情｜全部数字可复现",
            ha="center", va="center", color="#5D7characters"[:7] if False else "#5D7396",
            fontsize=10.5)
    fig.savefig(OUT / "cover.png", facecolor="white")
    plt.close(fig)


for f in (fig0, fig1, fig2, fig3, fig4, fig5, fig6_jac, cover):
    f()
    print("已生成", f.__name__)
print("输出目录:", OUT)
