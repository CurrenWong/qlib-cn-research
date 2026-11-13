"""生成报告配图（8 张，150dpi）。

数据来源全部来自 results/*.json / *.parquet，不重新计算策略。
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
RES = HERE / "results"
IMG = HERE / "report" / "img"
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
        ax.set_title(title, fontsize=13, color=INK, loc="left", pad=16, fontweight="bold")
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9.5, color=GRAY)


def save(fig, name):
    p = IMG / name
    fig.savefig(p, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print("  ", p.name, f"{p.stat().st_size/1024:.0f}KB")


def fig_nav():
    navs = pd.read_parquet(RES / "nav_curves.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.6))
    for ax, key, ttl in zip(axes, ["valid_2020_2022", "test_2023_2026"],
                            ["验证期 2020-2022（选型只用这段）", "测试期 2023-2026（一次性评估）"]):
        cols = [c for c in navs.columns if c.startswith(key + "|")]
        sub = navs[cols].dropna()
        style(ax, ttl, "起点=1.00；策略=LightGBM 选股 top10 月度调仓（已扣成本）")
        order = [("strategy", "策略（含成本）", ORANGE, 2.0),
                 ("strategy_zero_cost", "策略（零成本对照）", "#F2C79B", 1.4),
                 ("equal_pool", "池内等权 300 只", TEAL, 1.6),
                 ("index", "沪深300", GRAY, 1.6),
                 ("ma20", "MA20 趋势过滤", "#C9A0DC", 1.2)]
        for name, lab, c, lw in order:
            col = f"{key}|{name}"
            if col in sub:
                s = sub[col].dropna()
                ax.plot(s.index, s / s.iloc[0], color=c, lw=lw, label=lab)
        ax.legend(frameon=False, fontsize=9, loc="upper left")
        ax.set_ylabel("净值", fontsize=9, color=GRAY)
        ax.tick_params(labelsize=8.5, colors=GRAY)
    fig.suptitle("策略 vs 基线：验证期赚钱，测试期跑输等权池", fontsize=14.5,
                 color=INK, x=0.005, ha="left", y=1.04, fontweight="bold")
    save(fig, "fig1_nav.png")


def fig_ic():
    ic = pd.read_csv(RES / "ic_by_year.csv")
    fig, ax = plt.subplots(figsize=(9.4, 3.9))
    style(ax, "分年度样本外 RankIC（walk-forward，每折只用折前数据训练）",
          "柱高=该年日均秩相关；灰字=该年交易日数；2021 与 2026 已弱到统计不显著")
    colors = [TEAL if v > 0 else RED for v in ic["ic_mean"]]
    bars = ax.bar(ic["year"].astype(str), ic["ic_mean"], color=colors, width=0.55)
    top = float(ic["ic_mean"].max())
    ax.set_ylim(0, top * 1.42)                      # 给柱顶数字留空间，别压到副标题
    for b, v, n in zip(bars, ic["ic_mean"], ic["n_days"]):
        ax.text(b.get_x() + b.get_width() / 2, v + top * 0.03,
                f"{v:.4f}\n{n}天", ha="center", va="bottom", fontsize=8.6, color=INK)
    ax.axhline(0, color="#C8CDD3", lw=1)
    ax.set_ylabel("RankIC", fontsize=9, color=GRAY)
    ax.tick_params(labelsize=9, colors=GRAY)
    save(fig, "fig2_ic.png")


def fig_buckets():
    d = json.loads((RES / "signal_diag.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(9.4, 3.9))
    style(ax, "信号分档：预测越靠前，未来 5 日收益越高（单调）",
          "横轴=当日预测值的百分位分档；纵轴=该档未来 5 日平均收益")
    labels = ["后3%", "3-10%", "10-20%", "20-35%", "35-65%", "65-80%", "80-90%", "90-97%", "前3%"]
    x = np.arange(len(labels))
    for period, c, off in (("valid", TEAL, -0.19), ("test", ORANGE, 0.19)):
        b = d[period]["buckets"]
        vals = [b[l]["mean_fwd5"] * 100 for l in labels]
        ax.bar(x + off, vals, width=0.36, color=c,
               label="验证期 2020-2022" if period == "valid" else "测试期 2023-2026")
    pool = [d[p]["pool_mean"] * 100 for p in ("valid", "test")]
    ax.axhline(pool[0], color=TEAL, ls="--", lw=1,
               label=f"验证期池内均值 {pool[0]:+.3f}%")
    ax.axhline(pool[1], color=ORANGE, ls="--", lw=1,
               label=f"测试期池内均值 {pool[1]:+.3f}%")
    ax.set_xlim(-0.75, len(labels) - 0.25)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("未来 5 日平均收益（%）", fontsize=9, color=GRAY)
    ax.legend(frameon=False, fontsize=8.6, loc="upper left", ncol=2)
    ax.tick_params(labelsize=8.5, colors=GRAY)
    save(fig, "fig3_buckets.png")


def fig_configs():
    v = json.loads((RES / "variants.json").read_text(encoding="utf-8"))
    va = pd.DataFrame(v["appendix"]["valid_2020_2022"])
    te = pd.DataFrame(v["appendix"]["test_2023_2026"])
    m = va.merge(te, on=["K", "freq"], suffixes=("_v", "_t"))
    m["label"] = m.apply(lambda r: f"K={r['K']} 月调" if r["freq"] == 20 else f"K={r['K']} 周调", axis=1)
    m = m.sort_values("ir_v", ascending=False)
    fig, ax = plt.subplots(figsize=(9.4, 4.0))
    style(ax, "同一套模型，验证期挑出来的配置在测试期不灵",
          "左=验证期 IR（选型依据）；右=测试期 IR（冻结后一次性评估）；橙=被选中的配置")
    x = np.arange(len(m))
    sel = (m["K"] == 10) & (m["freq"] == 20)
    ax.bar(x - 0.19, m["ir_v"], width=0.36, color=[ORANGE if s else TEAL for s in sel],
           label="验证期 IR")
    ax.bar(x + 0.19, m["ir_t"], width=0.36, color=[ORANGE if s else "#C7D6DD" for s in sel],
           label="测试期 IR")
    ax.axhline(0, color="#C8CDD3", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(m["label"], fontsize=9)
    ax.set_ylabel("信息比率 IR", fontsize=9, color=GRAY)
    ax.legend(frameon=False, fontsize=9)
    ax.tick_params(labelsize=8.5, colors=GRAY)
    save(fig, "fig4_configs.png")


def fig_picks(picks):
    fig, ax = plt.subplots(figsize=(9.4, 4.6))
    style(ax, "2026-10-30 模型排序 Top 10（观察名单，非买入建议）",
          "左=模型预测未来 5 日收益；右=该股近 20 日实际涨跌（红=跌）")
    y = np.arange(len(picks))[::-1]
    names = [f"{p['name']} {p['symbol'][2:]}" for p in picks]
    ax.barh(y + 0.19, [p["pred"] * 100 for p in picks], height=0.36, color=ORANGE,
            label="模型预测 5 日收益")
    ax.barh(y - 0.19, [p["ret_20"] * 100 for p in picks], height=0.36,
            color=[RED if p["ret_20"] < 0 else TEAL for p in picks], label="近 20 日实际涨跌")
    ax.axvline(0, color="#C8CDD3", lw=1)
    ax.set_xlim(-62, 26)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9.5)
    ax.set_xlabel("（%）", fontsize=9, color=GRAY)
    ax.legend(frameon=False, fontsize=9, loc="center right",
              bbox_to_anchor=(1.0, 0.42))
    ax.tick_params(labelsize=8.5, colors=GRAY)
    save(fig, "fig5_picks.png")


def fig_importance(picks):
    imp = picks["feature_importance"][:14][::-1]
    fig, ax = plt.subplots(figsize=(9.4, 4.2))
    style(ax, "最终模型特征重要性（分裂次数）",
          "30 个价量特征，LightGBM 选出的 top14；数据源无基本面字段")
    ax.barh([f["cn"] for f in imp], [f["imp"] for f in imp], color=TEAL, height=0.62)
    ax.tick_params(labelsize=9, colors=INK)
    ax.set_xlabel("分裂次数", fontsize=9, color=GRAY)
    save(fig, "fig6_importance.png")


def fig_cost():
    v = json.loads((RES / "variants.json").read_text(encoding="utf-8"))
    te = pd.DataFrame(v["appendix"]["test_2023_2026"])
    fig, ax = plt.subplots(figsize=(9.4, 3.9))
    style(ax, "换手成本：测试期各配置的成本拖累",
          "柱=测试期累计交易成本（100 万本金）；周调=每月调仓")
    te = te.sort_values("cost", ascending=False)
    cols = [RED if f == 5 else ORANGE for f in te["freq"]]
    bars = ax.bar([f"K={r['K']} {'周调' if r['freq']==5 else '月调'}" for _, r in te.iterrows()],
                  te["cost"] / 10000, color=cols, width=0.55)
    for b, v_ in zip(bars, te["cost"] / 10000):
        ax.text(b.get_x() + b.get_width() / 2, v_ + 0.4, f"{v_:.1f} 万",
                ha="center", fontsize=9, color=INK)
    ax.set_ylabel("累计成本（万元）", fontsize=9, color=GRAY)
    ax.tick_params(labelsize=9, colors=GRAY)
    save(fig, "fig7_cost.png")


def fig_price(curves):
    fig, axes = plt.subplots(2, 5, figsize=(15.5, 5.2))
    for ax, (sym, s) in zip(axes.ravel(), curves.items()):
        ax.plot(s.index, s.values, color=ORANGE, lw=1.3)
        ax.fill_between(s.index, s.values, s.values.min(), color=ORANGE, alpha=0.10)
        ax.set_title(sym, fontsize=9.5, color=INK)
        ax.grid(color=GRID, lw=0.7)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(labelsize=7.5, colors=GRAY)
        ax.set_xticklabels([])
    fig.suptitle("Top 10 近 6 个月走势（qlib 前复权价）", fontsize=13.5, color=INK,
                 x=0.005, ha="left", y=1.02, fontweight="bold")
    fig.tight_layout()
    save(fig, "fig8_price.png")


def main():
    bt = json.loads((RES / "backtest.json").read_text(encoding="utf-8"))
    picks = json.loads((RES / "picks.json").read_text(encoding="utf-8"))
    print("生成配图 →", IMG)
    fig_nav()
    fig_ic()
    fig_buckets()
    fig_configs()
    fig_picks(picks["picks"])
    fig_importance(picks)
    fig_cost()
    # 个股走势
    import model_core as mc
    ctx = mc.load_all()
    close = ctx["close"]
    dates = ctx["dates"]
    curves = {}
    for p in picks["picks"]:
        j = ctx["symbols"].index(p["symbol"])
        s = pd.Series(close[:, j], index=dates).dropna().iloc[-120:]
        curves[f"{p['name']} {p['symbol']}"] = s / s.iloc[0] * 100
    fig_price(curves)
    print("完成")


if __name__ == "__main__":
    main()
