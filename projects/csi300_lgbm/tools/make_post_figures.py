"""一稿多发用的 3 张新图 + 封面（风格与 make_figures.py 一致，150dpi）。

fig9  持仓只数 × 调仓频率：验证期 / 测试期
fig10 缓冲带规则对比
fig11 调整后的 20 只：近 20 日涨跌 vs 模型预测
cover 公众号/知乎封面（1080×864）
"""

import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent.parent
RES = HERE / "results"
POST = HERE / "docs" / "post"
IMG = POST / "img"
IMG.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 150

INK = "#1F2933"
GRAY = "#8A9099"
ORANGE = "#E8833A"
TEAL = "#2F7E8C"
RED = "#C94C4C"
GRID = "#E4E7EB"
BG = "#FFFFFF"


def style(ax, title=None, sub=None):
    ax.set_facecolor(BG)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#C8CDD3")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=13, color=INK, loc="left", pad=24, fontweight="bold")
    if sub:
        ax.text(0, 1.035, sub, transform=ax.transAxes, fontsize=9.5, color=GRAY)


def save(fig, name):
    p = IMG / name
    fig.savefig(p, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ", p.name, f"{p.stat().st_size/1024:.0f}KB")


def load():
    wide = json.loads((RES / "wide_portfolio.json").read_text(encoding="utf-8"))
    buf = json.loads((RES / "wide_buffer.json").read_text(encoding="utf-8"))
    picks = json.loads((RES / "picks_K20.json").read_text(encoding="utf-8"))
    return wide, buf, picks


def fig_wide(wide):
    grid = wide["grid"]
    base = wide["baselines"]
    ks = sorted({r["K"] for r in grid})
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.8))
    for ax, key, ttl, blabel, bval in (
            (axes[0], "valid", "验证期 2020-2022（选型只看这段）", "沪深300", base["valid"]["index_buyhold"]["ann_return"]),
            (axes[1], "test", "测试期 2023-2026（冻结后一次性评估）", "沪深300", base["test"]["index_buyhold"]["ann_return"])):
        style(ax, ttl, "左：月度调仓　中：季度　右：半年　｜　虚线＝沪深300")
        x = np.arange(len(ks))
        for j, (freq, color, lbl) in enumerate([(20, ORANGE, "月度"), (60, TEAL, "季度"), (120, GRAY, "半年")]):
            ys = [next(r[key]["ann_return"] for r in grid if r["K"] == k and r["freq"] == freq) * 100
                  for k in ks]
            ax.plot(x, ys, "-o", color=color, lw=2, ms=5, label=lbl)
            for xi, yi in zip(x, ys):
                ax.annotate(f"{yi:+.1f}", (xi, yi), textcoords="offset points",
                            xytext=(0, (9 if freq == 20 else -15) if yi >= 0 else -15),
                            ha="center",
                            fontsize=8.5, color=color)
        ax.axhline(bval * 100, color="#B9B4AC", ls="--", lw=1)
        ax.annotate(f"{blabel} {bval*100:+.2f}%", (-0.35, bval * 100),
                    fontsize=8.8, color="#8F8A84", ha="left", va="bottom")
        ax.set_xticks(x)
        ax.set_xticklabels([f"top{k}" for k in ks], fontsize=9.5)
        ax.set_ylabel("年化收益（%）", fontsize=9.5, color=GRAY)
        ax.legend(frameon=False, fontsize=9.5, ncol=3, loc="upper center",
                  bbox_to_anchor=(0.5, -0.10))
        ax.set_xlim(-0.4, len(ks) - 0.6)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    save(fig, "fig9_wide_grid.png")


def fig_buffer(buf):
    rows = [r for r in buf if r["mult"] in (1.0, 2.0, 3.0, 4.0, 5.0)]
    labels, valid, test, repl = [], [], [], []
    for r in rows:
        labels.append(f"top{r['n_hold']}" + ("" if r["mult"] == 1.0 else f" ×{r['mult']:.0f}"))
        valid.append(r["valid"]["ann_return"] * 100)
        test.append(r["test"]["ann_return"] * 100)
        repl.append(r["test"]["replace_ratio"] * 50)
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(13.2, 4.8))
    style(ax, "缓冲带：老仓位跌出 top-M 才换（橙色＝选定）",
          "缓冲带越大→换手越低→成本越低；但信号会被拖钝，两头都有代价")
    b1 = ax.bar(x - 0.19, valid, 0.38, color=TEAL, label="验证期年化")
    b2 = ax.bar(x + 0.19, test, 0.38, color=ORANGE, label="测试期年化")
    for bars in (b1, b2):
        for b in bars:
            v = b.get_height()
            ax.annotate(f"{v:+.1f}", (b.get_x() + b.get_width() / 2, v),
                        textcoords="offset points", xytext=(0, 3 if v >= 0 else -11),
                        ha="center", fontsize=8.6, color=INK)
    sel = [i for i, r in enumerate(rows) if r["n_hold"] == 20 and r["mult"] == 2.0]
    for i in sel:
        for b in (b1[i], b2[i]):
            b.set_edgecolor(ORANGE)
            b.set_linewidth(2.2)
    ax2 = None
    ax.set_xticks(x)
    ax.set_xticklabels([f"{l}\n换手 {r:.0f}%" for l, r in zip(labels, repl)], fontsize=9.5)
    ax.set_ylabel("年化收益（%）", fontsize=9.5, color=GRAY)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left", ncol=2)
    ax.set_ylim(min(min(valid), min(test)) - 6, max(max(valid), max(test)) + 9)
    fig.tight_layout()
    save(fig, "fig10_buffer.png")


def fig_basket(picks):
    ps = picks["picks"]
    y = np.arange(len(ps))[::-1]
    ret = [(p["ret_20"] or 0) * 100 for p in ps]
    pred = [(p["pred"] or 0) * 100 for p in ps]
    colors = [ORANGE if i < 10 else TEAL for i in range(len(ps))]
    fig, ax = plt.subplots(figsize=(11.6, 6.2))
    style(ax, "调整后的 20 只：模型分前 10 / 后 10，近 20 日实际涨跌",
          "橙色＝原 top10（都是高波动超跌票）；青色＝新补进来的 10 只；11/20 近 20 日跌超 20%")
    ax.barh(y, ret, color=colors, height=0.62)
    for yy, r, p_, ps_ in zip(y, ret, pred, ps):
        ax.annotate(f"{r:+.1f}%", (r, yy), textcoords="offset points",
                    xytext=(6 if r >= 0 else -6, 0), va="center",
                    ha="left" if r >= 0 else "right", fontsize=8.8, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{p['name']} {p['symbol'][2:]}" for p in ps], fontsize=9.5)
    ax.axvline(0, color="#C8CDD3", lw=1)
    ax.set_xlabel("近 20 日实际涨跌（%）", fontsize=9.5, color=GRAY)
    ax.set_xlim(min(ret) - 14, max(ret) + 14)
    fig.tight_layout()
    save(fig, "fig11_basket.png")


def make_cover():
    fig = plt.figure(figsize=(10.8, 8.64), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, color="#111A26"))
    ax.add_patch(plt.Rectangle((0.08, 0.775), 0.055, 0.006, color="#E8833A"))
    ax.text(0.08, 0.72, "验证期年化 +20.86%", fontsize=33, color="#FFFFFF",
            fontweight="bold", va="top")
    ax.text(0.08, 0.60, "测试期年化 -2.13%", fontsize=33, color="#FFFFFF",
            fontweight="bold", va="top")
    ax.text(0.08, 0.475, "然后我把组合改了：", fontsize=21, color="#E8833A", va="top")
    ax.text(0.08, 0.405, "top20 + 缓冲带 → 测试期 +6.11%", fontsize=21,
            color="#BDC3C7", va="top")
    ax.text(0.08, 0.10, "沪深300 × LightGBM 选股复盘", fontsize=15,
            color="#7F8C8D", va="bottom")
    ax.text(0.92, 0.10, "2026.11", fontsize=15, color="#7F8C8D", va="bottom", ha="right")
    fig.savefig(POST / "cover.png", facecolor="#111A26")
    plt.close(fig)
    print("   cover.png", f"{(POST / 'cover.png').stat().st_size/1024:.0f}KB")


def copy_report_figs():
    src = HERE / "report" / "img"
    for f in src.glob("*.png"):
        shutil.copy2(f, IMG / f.name)
    print(f"  复制原报告配图 {len(list(src.glob('*.png')))} 张 → {IMG}")


def main():
    wide, buf, picks = load()
    print("生成一稿多发配图 →", IMG)
    copy_report_figs()
    fig_wide(wide)
    fig_buffer(buf)
    fig_basket(picks)
    make_cover()


if __name__ == "__main__":
    main()
