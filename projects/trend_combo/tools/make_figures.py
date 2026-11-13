"""出图（matplotlib，风格与 csi300_lgbm 报告一致）。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\make_figures.py
产出：report\\img\\fig*.png
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
RESULTS = PROJ / "results"
IMG = PROJ / "report" / "img"
IMG.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["grid.linestyle"] = "--"

ORANGE, TEAL, RED, GREY, BLUE = "#E8833A", "#2F7E8C", "#C94C4C", "#9AA1A9", "#4A6FA5"


def style_ax(ax, title=None, ylabel=None):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#D8DCE0")
    ax.tick_params(colors="#5B6470", labelsize=9)
    if title:
        ax.set_title(title, fontsize=11.5, color="#1F2933", loc="left", pad=9)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9.5, color="#5B6470")


def main():
    res = json.loads((RESULTS / "ic_results.json").read_text(encoding="utf-8"))
    V = res["variants"]
    sel = res["selected"]
    yearly = pd.DataFrame(res["yearly"])
    fdf = pd.read_csv(RESULTS / "factor_ic.csv")
    grid = pd.read_csv(RESULTS / f"weight_grid_{sel['wmode']}.csv")

    # ---------- fig1: 三单域 + 选中组合，分期 IC ----------
    names = ["price_only", "fund_only", "event_only", "mix_selected"]
    labels = ["纯价量", "纯基本面", "纯事件", "混合(选中)"]
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.0))
    for ax, lname, ttl in zip(axes, ["fwd5", "fwd20"],
                              ["对未来 5 日收益的 RankIC", "对未来 20 日收益的 RankIC"]):
        w = 0.2
        x = np.arange(len(names))
        for i, (sp, c) in enumerate([("train", GREY), ("valid", BLUE), ("test", ORANGE)]):
            vals = [V[n][lname][sp].get("ic_mean", np.nan) for n in names]
            ax.bar(x + (i - 1) * w, vals, w, label={"train": "训练 16-19",
                                                    "valid": "验证 20-22",
                                                    "test": "测试 23-26"}[sp],
                   color=c, alpha=0.92)
        ax.axhline(0, color="#B0B6BD", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        style_ax(ax, ttl, "RankIC")
        ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
    fig.savefig(IMG / "fig1_ic_compare.png")
    plt.close(fig)

    # ---------- fig2: 分年 RankIC ----------
    fig, ax = plt.subplots(figsize=(11.4, 4.0))
    for n, c, lb in [("price_only", GREY, "纯价量"), ("fund_only", TEAL, "纯基本面"),
                     ("mix_selected", ORANGE, "混合(选中)")]:
        sub = yearly[(yearly["variant"] == n) & (yearly["label"] == "fwd5")].sort_values("year")
        ax.plot(sub["year"], sub["ic_mean"], marker="o", ms=4.5, lw=1.9, color=c, label=lb)
    ax.axhline(0, color="#B0B6BD", lw=0.8)
    ax.legend(frameon=False, fontsize=9)
    style_ax(ax, "分年度 RankIC（对未来 5 日收益）", "RankIC")
    fig.savefig(IMG / "fig2_ic_yearly.png")
    plt.close(fig)

    # ---------- fig3: 权重敏感性 ----------
    g = grid[grid["we"] == 0.0].sort_values("wf")
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    ax.plot(g["wf"], g["valid_icir_f5"], marker="o", ms=5, color=BLUE, label="验证期 ICIR（选权重用）")
    ax.plot(g["wf"], g["test_icir_f5"], marker="s", ms=5, color=ORANGE, label="测试期 ICIR（只看一次）")
    ax.plot(g["wf"], g["test_icir_f20"], marker="^", ms=5, color=TEAL, ls="--", label="测试期 ICIR（fwd20）")
    ax.axvline(sel["wf"], color=RED, ls=":", lw=1.3, label=f"验证期选中基本面权重 {sel['wf']:.2f}")
    ax.axhline(0, color="#B0B6BD", lw=0.8)
    ax.legend(frameon=False, fontsize=8.5)
    style_ax(ax, "基本面权重敏感性：加多少基本面最划算", "ICIR")
    fig.savefig(IMG / "fig3_weight_sens.png")
    plt.close(fig)

    # ---------- fig4: 测试期分档收益 ----------
    b = res.get("buckets_test_fwd20", {})
    if b:
        fig, ax = plt.subplots(figsize=(7.4, 3.8))
        ks = sorted(b.keys())
        vals = [b[k]["mean"] * 100 for k in ks]
        colors = [RED if v < 0 else TEAL for v in vals]
        bars = ax.bar([f"Q{int(k)}" for k in ks], vals, color=colors, alpha=0.92)
        for i, v in enumerate(vals):
            ax.text(bars[i].get_x() + bars[i].get_width() / 2, v, f"{v:+.2f}%",
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=9, color="#39424E")
        ax.axhline(0, color="#B0B6BD", lw=0.8)
        style_ax(ax, "测试期 2023-2026：按混合分五档的未来 20 日平均收益", "平均收益 %")
        fig.savefig(IMG / "fig4_buckets.png")
        plt.close(fig)

    # ---------- fig5: 当前持仓打分分解 ----------
    hp = RESULTS / "holdings_score.json"
    if hp.exists():
        h = json.loads(hp.read_text(encoding="utf-8"))
        rows = pd.DataFrame(h["rows"]).sort_values("total")
        rows = rows[rows["total"].notna()]
        fig, ax = plt.subplots(figsize=(9.8, 6.4))
        y = np.arange(len(rows))
        p = rows["price_score"].fillna(0).to_numpy()
        f = rows["fund_score"].fillna(0).to_numpy()
        e = rows["event_score"].fillna(0).to_numpy()
        ax.barh(y, p, color=TEAL, alpha=0.88, label="价量分")
        ax.barh(y, f, left=p, color=ORANGE, alpha=0.9, label="基本面分")
        ax.barh(y, e, left=p + f, color=BLUE, alpha=0.7, label="事件分")
        ax.set_yticks(y)
        ax.set_yticklabels(rows["name"], fontsize=9)
        ax.axvline(0, color="#B0B6BD", lw=0.8)
        ax.legend(frameon=False, fontsize=9, loc="lower right")
        style_ax(ax, f"当前持仓的混合分拆解（截面 {h['as_of']}，权重 "
                      f"{h['weights']['price']:.2f}/{h['weights']['fund']:.2f}/"
                      f"{h['weights']['event']:.2f}）", "分数（-1 ~ +1）")
        fig.savefig(IMG / "fig5_holdings.png")
        plt.close(fig)

    # ---------- fig6: 因子覆盖度 ----------
    ps = RESULTS / "panel_stats.json"
    if ps.exists():
        st = json.loads(ps.read_text(encoding="utf-8"))
        cov = st["coverage"]
        items = sorted(cov.items(), key=lambda kv: kv[1]["notna"])
        fig, ax = plt.subplots(figsize=(8.6, 5.4))
        y = np.arange(len(items))
        ax.barh(y, [v["notna"] * 100 for _, v in items], color=BLUE, alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels([k for k, _ in items], fontsize=8.5)
        for i, (_, v) in enumerate(items):
            ax.text(v["notna"] * 100 + 1, i, f"{v['notna']*100:.0f}%",
                    va="center", fontsize=8, color="#5B6470")
        ax.set_xlim(0, 110)
        style_ax(ax, "基本面因子在 2014-2026 面板上的覆盖率", "覆盖率 %")
        fig.savefig(IMG / "fig6_coverage.png")
        plt.close(fig)

    # ---------- fig7: 因子级 IC（训练/验证/测试）----------
    top = fdf.reindex(fdf["fwd5_train_ic"].abs().sort_values(ascending=False).index).head(18)
    top = top.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10.4, 6.4))
    y = np.arange(len(top))
    ax.barh(y - 0.26, top["fwd5_train_ic"], 0.26, color=GREY, label="训练 16-19")
    ax.barh(y, top["fwd5_valid_ic"], 0.26, color=BLUE, label="验证 20-22")
    ax.barh(y + 0.26, top["fwd5_test_ic"], 0.26, color=ORANGE, label="测试 23-26")
    ax.set_yticks(y)
    ax.set_yticklabels(top["factor"], fontsize=8.5)
    ax.axvline(0, color="#B0B6BD", lw=0.8)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    style_ax(ax, "因子级 RankIC（按训练期绝对值排序，取前 18）", "RankIC")
    fig.savefig(IMG / "fig7_factor_ic.png")
    plt.close(fig)

    # ---------- fig8: 先验方向 vs 自动定向 ----------
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    idx = np.arange(3)
    prior_v = [V["price_prior_dir"]["fwd5"][sp]["ic_mean"] for sp in ("train", "valid", "test")]
    auto_v = [V["price_only"]["fwd5"][sp]["ic_mean"] for sp in ("train", "valid", "test")]
    w = 0.35
    ax.bar(idx - w / 2, prior_v, w, color=RED, alpha=0.88, label="教科书先验方向")
    ax.bar(idx + w / 2, auto_v, w, color=TEAL, alpha=0.9, label="训练期 IC 自动定向")
    ax.axhline(0, color="#B0B6BD", lw=0.8)
    ax.set_xticks(idx)
    ax.set_xticklabels(["训练 16-19", "验证 20-22", "测试 23-26"])
    ax.legend(frameon=False, fontsize=9)
    style_ax(ax, "价量块：方向定错了，整块信号就是反的", "RankIC")
    fig.savefig(IMG / "fig8_direction.png")
    plt.close(fig)

    # ================= 策略回测部分 =================
    bt_path = RESULTS / "backtest.json"
    if not bt_path.exists():
        print("（无 backtest.json，跳过策略图）")
        return
    bt = json.loads(bt_path.read_text(encoding="utf-8"))
    navs = pd.read_parquet(RESULTS / "nav_curves.parquet")
    runs = bt["runs"]
    cfg = bt["config"]

    # ---------- fig9: 测试期净值曲线 ----------
    order = ["策略(验证期选参) top50", "同上(零成本对照)", "默认 top20 月调(参照)",
             "纯价量分 top20 月调", "纯基本面分 top20 月调", "池内等权300只", "沪深300买入持有"]
    colors = {"策略(验证期选参) top50": ORANGE, "同上(零成本对照)": "#F0B27A",
              "默认 top20 月调(参照)": BLUE, "纯价量分 top20 月调": GREY,
              "纯基本面分 top20 月调": "#C4CBD2", "池内等权300只": TEAL,
              "沪深300买入持有": "#39424E"}
    labels = {"策略(验证期选参) top50": f"策略(验证期选参) top{cfg['K']}",
              "同上(零成本对照)": "同上(零成本)", "默认 top20 月调(参照)": "默认 top20 月调",
              "纯价量分 top20 月调": "纯价量分 top20", "纯基本面分 top20 月调": "纯基本面分 top20",
              "池内等权300只": "池内等权300只", "沪深300买入持有": "沪深300买入持有"}
    fig, ax = plt.subplots(figsize=(11.4, 4.6))
    for name in order:
        if name not in navs.columns:
            continue
        s = navs[name].dropna()
        s = s / s.iloc[0]
        ax.plot(s.index, s.to_numpy(), lw=1.9 if "策略(验证期选参)" in name else 1.3,
                color=colors.get(name, GREY),
                ls="--" if "零成本" in name else "-", label=labels.get(name, name))
    ax.set_yscale("log")
    ax.axhline(1.0, color="#C9CFD6", lw=0.8)
    ax.legend(frameon=False, fontsize=8.8, ncol=2, loc="upper left")
    style_ax(ax, "测试期 2023-01 ~ 2026-10 净值曲线（含成本，对数刻度）", "净值（起点=1）")
    fig.savefig(IMG / "fig9_nav_test.png")
    plt.close(fig)

    # ---------- fig10: 全区间净值 ----------
    fig, ax = plt.subplots(figsize=(11.4, 4.4))
    for name, c, lw, ls in [("策略(选参)@全区间", ORANGE, 2.0, "-"),
                            ("沪深300@全区间", "#39424E", 1.4, "-")]:
        if name in navs.columns:
            s = navs[name].dropna()
            s = s / s.iloc[0]
            ax.plot(s.index, s.to_numpy(), lw=lw, color=c, ls=ls,
                    label="混合分策略(验证期选参)" if "策略" in name else "沪深300")
    ax.axhline(1.0, color="#C9CFD6", lw=0.8)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    style_ax(ax, "全区间 2016-2026 净值曲线（同一套参数，只换时间）", "净值（起点=1）")
    fig.savefig(IMG / "fig10_nav_full.png")
    plt.close(fig)

    # ---------- fig11: 分年收益 ----------
    ydf = pd.read_csv(RESULTS / "backtest_yearly.csv")
    main_run = f"策略(验证期选参) top{cfg['K']}"
    sub = ydf[ydf["run"].isin([main_run, "沪深300买入持有", "默认 top20 月调(参照)"])]
    if len(sub):
        piv = sub.pivot_table(index="year", columns="run", values="ret") * 100
        fig, ax = plt.subplots(figsize=(10.4, 4.2))
        x = np.arange(len(piv.index))
        w = 0.27
        for i, c in enumerate([main_run, "默认 top20 月调(参照)", "沪深300买入持有"]):
            if c in piv.columns:
                vals = piv[c].to_numpy()
                ax.bar(x + (i - 1) * w, vals, w,
                       color=[ORANGE, BLUE, "#39424E"][i],
                       alpha=0.92, label=labels.get(c, c))
        ax.axhline(0, color="#B0B6BD", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([str(y) for y in piv.index], fontsize=9)
        ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left")
        style_ax(ax, "测试期分年收益（策略 vs 沪深300）", "年收益 %")
        fig.savefig(IMG / "fig11_yearly.png")
        plt.close(fig)

    # ---------- fig12: 调仓频率 → 收益/换手/成本 ----------
    sens = pd.DataFrame(bt["sensitivity"])
    if len(sens):
        fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.0))
        for freq, g in sens.groupby("freq"):
            g = g.sort_values("K")
            axes[0].plot(g["K"], g["ann_return"] * 100, marker="o", ms=5,
                          label=f"每 {freq} 日调仓")
            axes[1].plot(g["K"], g["cost_per_year_pct"], marker="s", ms=5,
                         label=f"每 {freq} 日调仓")
        for ax, t, yl in zip(axes, ["年化收益：调仓越频繁越被成本吃掉", "年化交易成本"],
                             ["年化收益 %", "成本 %/年"]):
            ax.axhline(0, color="#B0B6BD", lw=0.8)
            ax.legend(frameon=False, fontsize=8.5)
            style_ax(ax, t, yl)
        fig.savefig(IMG / "fig12_freq_cost.png")
        plt.close(fig)

    # ---------- fig13: 分期对比 ----------
    pp = bt["per_period"]
    fig, ax = plt.subplots(figsize=(7.8, 3.9))
    names = ["train_2016_2019", "valid_2020_2022", "test_2023_2026"]
    strat = [pp[n]["ann_return"] * 100 for n in names]
    ax.bar(np.arange(3) - 0.2, strat, 0.4, color=ORANGE, alpha=0.92, label="混合分策略")
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(["训练 2016-19", "验证 2020-22", "测试 2023-26"], fontsize=9)
    ax.axhline(0, color="#B0B6BD", lw=0.8)
    ax.legend(frameon=False, fontsize=9)
    style_ax(ax, "同一套参数，分期年化（测试期只跑一次）", "年化 %")
    for i, v in enumerate(strat):
        ax.text(i - 0.2, v, f"{v:+.2f}%", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=9, color="#39424E")
    fig.savefig(IMG / "fig13_periods.png")
    plt.close(fig)

    print("图已生成:", sorted(p.name for p in IMG.glob("*.png")))


if __name__ == "__main__":
    main()
