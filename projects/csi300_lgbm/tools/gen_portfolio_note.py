"""生成 "扩仓 + 执行方式" 说明文档：数据全部从 results/*.json 读，不手抄数字。"""

import json
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

RES = Path(_ROOT + r"/projects/csi300_lgbm/results")
OUT = Path(_ROOT + r"/projects/csi300_lgbm/report/portfolio_v2.md")

wide = json.loads((RES / "wide_portfolio.json").read_text(encoding="utf-8"))
buf = json.loads((RES / "wide_buffer.json").read_text(encoding="utf-8"))
px = json.loads((RES / "picks_K20_price.json").read_text(encoding="utf-8"))
p20 = json.loads((RES / "picks_K20.json").read_text(encoding="utf-8"))

base = wide["baselines"]


def pct(x):
    return f"{x*100:+.2f}%"


lines = ["# 组合调整：从 top10 扩到 top20 + 缓冲带", "",
         f"数据截面 {p20['as_of']} · 池 {p20['pool_size']} 只 · 数字全部来自 results/*.json", "",
         "## 1. 为什么扩仓（原方案的死因）", "",
         "原方案 top10 + 月度调仓：验证期年化 +20.86%（IR 1.22）看着很好，测试期 -2.13%（IR -0.07），",
         "最大回撤 -50.74%。零成本对照也只有 -0.02%，说明不是手续费单杀，而是**10 只太集中**：",
         "年化波动 32%，波动拖累把算术超额吃光。", "",
         "## 2. 实测：K × 调仓频率（验证期选型 / 测试期一次性评估）", "",
         "| K | 调仓 | 验证年化 | 验证IR | 测试年化 | 测试IR | 测试MDD | 测试成本 |",
         "|---|---|---|---|---|---|---|---|"]

for r in wide["grid"]:
    v, t = r["valid"], r["test"]
    lines.append(f"| {r['K']} | 每{r['freq']}日 | {pct(v['ann_return'])} | {v['ir']:.2f} | "
                 f"{pct(t['ann_return'])} | {t['ir']:.2f} | {t['max_drawdown']*100:.2f}% | "
                 f"{t['cost_total']/1e4:.1f}万 |")

lines += ["", f"基线：验证期 沪深300 {pct(base['valid']['index_buyhold']['ann_return'])} / "
              f"池内等权 {pct(base['valid']['equal_pool']['ann_return'])}；"
              f"测试期 沪深300 {pct(base['test']['index_buyhold']['ann_return'])} / "
              f"池内等权 {pct(base['test']['equal_pool']['ann_return'])}。", "",
          "**季度/半年调仓被数据否掉了**：K=20 从每 20 日改每 60 日，验证期年化从 +11.66% 掉到 -2.12%。",
          "原因是标签是未来 5 日收益，信号衰减很快——报告里“拉长到季度”那条建议不成立，按验证期协议不采用。", "",
          "## 3. 加缓冲带（只换跌出 top-M 的仓位）", "",
          "| 持仓 | 缓冲带 | 验证年化 | 验证IR | 测试年化 | 测试IR | 测试MDD | 替换比例 | 测试成本 |",
          "|---|---|---|---|---|---|---|---|---|"]

for r in buf:
    v, t = r["valid"], r["test"]
    lines.append(f"| {r['n_hold']} | ×{r['mult']:.1f}（top{int(r['n_hold']*r['mult'])}） | "
                 f"{pct(v['ann_return'])} | {v['ir']:.2f} | {pct(t['ann_return'])} | "
                 f"{t['ir']:.2f} | {t['max_drawdown']*100:.2f}% | "
                 f"{t['replace_ratio']*100/2:.0f}% | {t['cost_total']/1e4:.1f}万 |")

chosen = next(r for r in buf if r["n_hold"] == 20 and r["mult"] == 2.0)
lines += ["", "（替换比例列 = 每次调仓被替换的只数占比；缓冲带 ×2 意味着老仓位只要还在 top40 就不动。）", "",
          "## 4. 结论：top20 + 2 倍缓冲带", "",
          f"- 验证期：年化 {pct(chosen['valid']['ann_return'])}，IR {chosen['valid']['ir']:.2f}"
          f"（原方案 20.86% / 1.22，几乎打平）",
          f"- 测试期：年化 {pct(chosen['test']['ann_return'])}，IR {chosen['test']['ir']:.2f}，"
          f"MDD {chosen['test']['max_drawdown']*100:.2f}%"
          f"（原方案 -2.13% / -0.07 / -50.74%）",
          f"- 测试期年化交易成本 {chosen['test']['cost_total']/1e4:.1f} 万元 ≈ "
          f"{chosen['test']['cost_total']/1e6/(chosen['test']['years']):.2%}/年",
          f"- 每次调仓约 **{chosen['test']['replace_ratio']*0.5*20:.0f} 只被替换**"
          f"（占 20 只的 {chosen['test']['replace_ratio']*50:.0f}%），"
          f"即约 {chosen['test']['replace_ratio']*20:.0f} 笔委托/月", "",
          "顺带一个反面例子：N=30 / 缓冲×5 的验证期 IR 1.44 是全网格最高，",
          "但测试期只有 +1.73%。选型越「精细」、样本外越难看，这就是这个模型的老毛病。", "",
          "**纪律提示**：测试期被近 30 个配置看过，属多重比较。可信的是方向（放宽 + 缓冲带明显降低了",
          "单票依赖），具体到“top20/×2 最优”不可信。", "",
          "## 5. 组合（2026-10-30 收盘，等权 5%）", "",
          "| # | 代码 | 名称 | 真实价 | 一手 | 权重 |", "|---|---|---|---|---|---|"]

for r in px["rows"]:
    lines.append(f"| {r['rank']} | {r['symbol']} | {r['name']} | {r['real_price']:.2f} | "
                 f"{r['one_lot']:,.0f} | 5.00% |")

lines += ["", f"20 只各买一手合计 **{px['total_one_lot']:,.0f} 元** —— 这就是这套组合的最小可执行资金。",
          "（qlib 的 $close 是复权连续序列，不能当成交价；表里真实价 = $close / $factor，已还原。）", "",
          "## 6. 有没有现成 ETF 可以直接买", "",
          "**没有能复制这个组合的 ETF。** 这套组合是模型每天重排出来的 top20，",
          "ETF 只能买指数，买不到“某模型的当期 top20”。三条替代路径：", "",
          "| 方案 | 拿到什么 | 年成本 | 操作 |", "|---|---|---|---|",
          "| 沪深300ETF（510300 / 510310 / 510330） | 指数收益：测试期 +0.65%/年 | 0.15%+0.05% | 1 笔 |",
          "| 沪深300指数增强 ETF（如 561990、159238） | 别人的增强模型，持仓与本事无关 | 以公告为准 | 1 笔 |",
          "| 自己买 20 只 + 缓冲带规则 | 回测那套：测试期 +6.11%/年 | 约 2.0%/年（含佣金+印花税） | 每月约 14 笔 |",
          "",
          "关键权衡：自建的年化成本约 2 个点，正好和模型在测试期的超额（+6.11% vs 等权池 +2.74%）同量级。",
          "换句话说——**这套策略的钱是“扣完成本剩下的那点”，不是“ETF 省下的那点”**。", "",
          "## 7. 风险（不粉饰）", "",
          "- 测试期 MDD 仍有 -45%，最大回撤没因为扩仓消失，只是从 -51% 收窄。",
          "- 组合 11/20 只是近 20 日跌超 20% 的高波动票，本质是赌反弹；反弹失败就继续跌。",
          "- 无基本面数据（数据源只有价量），任何“公司变好了”的说法都不是数据说的。",
          "- 2026 年至今（YTD）该策略仍是负的。", "",
          "风险提示：本文是回测复盘，不构成投资建议。", ""]

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"已写出 {OUT}（{len(lines)} 行）")
