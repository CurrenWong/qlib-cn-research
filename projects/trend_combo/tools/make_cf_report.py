"""把 counterfactual 结果做成报告（markdown + PNG 图）。"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJ = Path(__file__).resolve().parent.parent
RESULTS = PROJ / "results"
REPORT = PROJ / "report"
REPORT.mkdir(exist_ok=True)

J = json.loads((RESULTS / "counterfactual_oct30.json").read_text(encoding="utf-8"))
variants = J["variants"]
live = J["live"]
bench = J["benchmark"]

# ---------------- markdown ----------------
L = []
L.append("# 对照实验：基本面加权策略 vs 实盘 20 只（2026-10-30 选股 → 11-02 开盘买 → 11-05 收盘卖）\n")
L.append(f"- 信号日：**{J['signal_date']}**（趋势打分面板的最后一个截面）")
L.append(f"- 建仓：{J['entry']} 开盘 ｜ 平仓：{J['exit']} 收盘 ｜ 成本："
         f"买 {J['cost_model']['buy']*100:.2f}% / 卖 {J['cost_model']['sell']*100:.2f}% / "
         f"每笔最低 {J['cost_model']['min_fee']:.0f} 元")
L.append(f"- 仓位：**等权 + 单票上限 {J['cost_model']['max_weight']*100:.0f}%**（按实际投入计），"
         f"名义总预算 {J['cost_model']['total_capital']:,.0f} 元，整手向下取整；"
         f"一手就超上限的票直接剔除")
L.append(f"- 权重：推荐 {J['weights']['recommended']}；验证期选参 {J['weights']['valid_selected']}\n")

L.append("## 一、总账\n")
L.append("| 组合 | 只数 | 投入(元) | 单票最大权重 | 11-05 市值 | 分红 | 费用 | 净收益 | **净收益率** |")
L.append("|---|---|---|---|---|---|---|---|---|")
for v in variants + [live]:
    mw = v.get("max_weight_pct")
    mw_s = f"{mw:.2f}%" if mw is not None else "—"
    L.append(f"| {v['label']} | {v['n']} | {v['total_cost']:,.0f} | {mw_s} | "
             f"{v['market_value']:,.0f} | {v['cash_div']:,.0f} | {v['fee']:,.0f} | "
             f"{v['pnl_net']:,.0f} | **{v['ret_net_pct']:+.2f}%** |")
L.append(f"| 沪深300（同期） | | | | | | | | **{bench['ret_pct']:+.2f}%** |\n")

L.append("## 二、逐日净值（相对投入成本）\n")
L.append("| 组合 | " + " | ".join(
    p["date"][5:] for p in variants[0]["day_path"]) + " |")
L.append("|---|" + "---|" * len(variants[0]["day_path"]))
for v in variants + [live]:
    if "day_path" in v:
        L.append(f"| {v['label'].split('（')[0]} | " +
                 " | ".join(f"{p['ret_pct'] - 100:+.2f}%" for p in v["day_path"]) + " |")
L.append("")

L.append("## 三、与实盘 20 只的重叠\n")
L.append("| 策略组合 | 重合只数 | 仅策略 | 仅实盘 |")
L.append("|---|---|---|---|")
for v in variants:
    o = J["overlap"][v["label"]]
    L.append(f"| {v['label']} | {o['n_overlap']} | {o['n_only_variant']} | {o['n_only_live']} |")
L.append("")

L.append("实盘 20 只在混合分（637 只池）里的排名：\n")
ranks = J["live_mix_rank"]
L.append("```")
L.append("  ".join(f"{r['rank']}:{r['symbol']}" for r in ranks))
L.append("```\n")
L.append("> 中位数排名 423 / 637；只有豪威集团 SH603501 进过前 5（并列第 5）。")
L.append("> 说明两套框架选出来的东西几乎不重叠。\n")

L.append("## 五、过程中挖出来的三个数据问题（都已在 2026-11-05 修完）\n")
L.append("""**① 本地面板 10-30 只有 299/637 只有收盘价 → 已修。**
根因：本地 qlib 最近一次 bar 追加（备份 `20261102_100058`）只喂了**当时沪深300 的 300 只成分**，
其余 316 只历史成分票的 bin 还停在上一次全量更新的 **2026-10-27**。
修法：`tools/append_latest_bars.py --symbols-file <338 只名单> --until 2026-10-30`（分 4 块跑完，
自带 `_backup`），随后重建 `build_dataset → build_panel → composite`。
**补完 10-30 有收盘价的从 299 只变成 615 只**，只剩 22 只真停牌/退市（最后交易 2017-01 ~ 2026-09-14）。

**② 22 只死票霸占 price_score 上限 → 已修（`composite.py`）。**
根因：`build_dataset` 的 `close.pct_change()` 默认前向填充，停牌股的价格被填成一条平线，
于是 `price_pos_250` 等因子取到极端值，z-score 后挤到上限。
修法：**当日没有收盘价的票，price_score 一律置 NaN**（没有收盘价 = 当天不可交易，本来就不该有价量分）。
效果：`price_score` 最大值从「20 只并列 0.5694」变成「1 只独占 0.4342」，分布连续无断档；
死票再也进不了纯价量排名。回测重跑后测试期年化 +5.87% → **+5.84%**（基本不变），
训练 +1.47% → +1.91%、验证 +1.24% → +1.61%，**已发布文章的数字依然站得住**。

**③ 仓位规则「每只 1 万 + 零头补一手」在高价股上失控 → 已修（`counterfactual_oct.py`）。**
旧规则：寒武纪 907 元/股 → 1 手就是 9.07 万，权重冲到 **39%**。
新规则：**等权 + 单票上限 10%（按实际投入计）+ 整手向下取整**，两遍执行：
第一遍按名义预算等权买，第二遍按实际投入重算上限、超限的按整手裁掉、裁到 0 就剔除，
迭代到收敛（剔除后分母变小，权重会反弹，所以要反复）。
效果：各组合单票最大权重全部 ≤ 10%（本轮 6.2%~9.96%）。
""")

L.append("## 六、结论\n")
L.append("""- **修完两处代码后，混合分 top20 +2.11%（C 组行业≤3 +3.70%）**，
  纯基本面 +5.57%、纯价量 +0.51%、策略正式参数（top50+行业≤3）+2.75%，
  实盘 LGBM 20 只 +0.58%，沪深300 同期 +2.68%。
  **纯价量仍然最差**——这跟回测里「纯价量单独不行」的结论一致；
  纯基本面这 4 天数字最好，但只有 15 只（5 只因一手超上限被剔除），样本更小、更集中，不能当结论。
- **这仍然只有 4 个交易日，不能当上线依据。** 同样的方法换一天就可能翻脸
  （同一天、同一批因子，修代码前后从 +3.84% 变成 +2.11%）。真正的证据是 2016-2026 回测
  （测试期年化 +5.84%、超额 +5.3% 左右、三段为正）。
- **两套框架几乎不重叠**（20 只里重合 0~1 只）。基本面加权更像**风格分散/换仓节奏工具**，
  不是 LGBM 的替代选股器；想降相关性，两者搭配比二选一更合理。
- **实盘那 20 只还是按旧规则（每只 1 万零头补一手）建的仓**，已经买了不能改；
  **下一次调仓（11-30）开始用新规则**：等权 + 单票 10% 上限 + 整手向下取整。
- **下一步**：等 **11-30 调仓日**，用补齐后的数据做一次全窗口对照再决定是否调仓。
""")

for key, title in [("A", "A 混合分 top20（策略原样全池）"), ("B", "B 混合分 top20（干净池）")]:
    v = next(x for x in variants if x["label"].startswith(key))
    L.append(f"## 四、{title} 逐只明细\n")
    L.append("| # | 名称 | 代码 | 买入(11-02开) | 卖出(11-05收) | 收益% | 投入 | 盈亏 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(v["rows"], 1):
        L.append(f"| {i} | {r['name']} | {r['symbol']} | {r['buy_open']} | {r['sell_close']} | "
                 f"{r['ret_pct']:+.2f}% | {r['cost']:,.0f} | {r['pnl']:+,.0f} |")
    L.append("")

(REPORT / "counterfactual_oct30.md").write_text("\n".join(L), encoding="utf-8")
print("已写出", REPORT / "counterfactual_oct30.md")

# ---------------- PNG ----------------
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

names = [v["label"].split("（")[0] for v in variants] + ["实盘20只", "沪深300"]
rets = [v["ret_net_pct"] for v in variants] + [live["ret_net_pct"], bench["ret_pct"]]

fig, axes = plt.subplots(1, 2, figsize=(19, 8), dpi=110,
                         gridspec_kw={"width_ratios": [1.25, 1]})
ax = axes[0]
colors = ["#E67E22" if n.startswith(("A", "B", "C", "D", "G")) else
          ("#5D6D7E" if n.startswith(("E", "F")) else "#C0392B") for n in names]
ax.barh(names, rets, color=colors)
for i, r in enumerate(rets):
    ax.text(r + (0.05 if r >= 0 else -0.05), i, f"{r:+.2f}%", va="center",
            ha="left" if r >= 0 else "right", fontsize=11)
ax.axvline(0, color="#333", lw=1)
ax.set_title("净收益率对照（11-02 开盘 → 11-05 收盘，已扣成本）", fontsize=15)
ax.set_xlim(min(rets) - 0.6, max(rets) + 0.9)
ax.grid(axis="x", alpha=0.25)
ax.set_xlabel("%")

ax2 = axes[1]
for v in variants + [live]:
    if "day_path" not in v:
        continue
    x = [p["date"][5:] for p in v["day_path"]]
    y = [p["ret_pct"] - 100 for p in v["day_path"]]
    lbl = v["label"].split("（")[0]
    ax2.plot(x, y, marker="o", lw=2.2 if lbl in ("A", "B", "实盘20只") else 1.2,
             alpha=0.95 if lbl in ("A", "B", "G", "实盘20只") else 0.5,
             label=lbl)
ax2.axhline(0, color="#333", lw=1)
ax2.set_title("逐日净值路径（相对投入成本，0% = 成本线）", fontsize=15)
ax2.legend(fontsize=9, ncol=2)
ax2.grid(alpha=0.25)
ax2.set_ylabel("%")

fig.suptitle("基本面加权策略（2026-10-30 选股）vs 实盘 20 只 LGBM 组合 · 4 个交易日对照",
             fontsize=16, y=0.99)
fig.tight_layout()
out = REPORT / "counterfactual_oct30.png"
fig.savefig(out, facecolor="white")
plt.close(fig)
print("已写出", out, f"{out.stat().st_size/1024:.0f} KB")
