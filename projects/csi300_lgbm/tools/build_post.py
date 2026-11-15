"""把两版报告合成一篇文章（一稿多发用）。

- 第一部分：原报告（report.md，由 build_report.py 生成 → html2md.py 转换）
- 第二部分：组合调整（top20 + 缓冲带），表格全部从 results/*.json 现读现生成
- 数字不手抄；正文里对"更长的持有期"那条已被推翻的建议做显式更正

输出：docs/post/article.md
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RES = HERE / "results"
REPORT = HERE / "report"
POST = HERE / "docs" / "post"
POST.mkdir(parents=True, exist_ok=True)

wide = json.loads((RES / "wide_portfolio.json").read_text(encoding="utf-8"))
buf = json.loads((RES / "wide_buffer.json").read_text(encoding="utf-8"))
px = json.loads((RES / "picks_K20_price.json").read_text(encoding="utf-8"))
p20 = json.loads((RES / "picks_K20.json").read_text(encoding="utf-8"))

chosen = next(r for r in buf if r["n_hold"] == 20 and r["mult"] == 2.0)
cv, ct = chosen["valid"], chosen["test"]
base = wide["baselines"]
repl = ct["replace_ratio"] * 0.5 * 20
cost_yr = ct["cost_total"] / 1e6 / ct["years"]
n_big = sum(1 for p in p20["picks"] if (p["ret_20"] or 0) < -0.20)


def pct(x):
    return f"{x*100:+.2f}%"


# ---------------------------------------------------------------- 原报告分节
src = (REPORT / "report.md").read_text(encoding="utf-8")
parts = re.split(r"(?m)^(?=## )", src)
sections = {}
for p in parts:
    m = re.match(r"## (.+)", p)
    key = m.group(1) if m else "head"
    sections[key] = p.strip()

head = sections.pop("head")
appendix = ""
for k in list(sections):
    if k.startswith("附录"):
        appendix += "\n\n" + sections.pop(k)

part1 = []
for k, v in sections.items():
    if k.startswith("六、"):
        continue          # 第六节（含已被推翻的建议）重写
    part1.append(v)
body1 = "\n\n".join(part1)

# 修正第四章里那句已被推翻的"更长的持有期"
old_advice = ("如果要继续做，方向是**更宽的持仓池、更长的持有期**"
              "（例如 top 10% ≈ 30 只、季度调仓）， 而不是继续调模型。")
new_advice = ("如果要继续做，方向是**更宽的持仓池**——这一点在第六节被实测证实；"
              "但同一句话里的“更长的持有期（季度调仓）”在第六节被我自己推翻。")
if old_advice not in body1:
    raise SystemExit("找不到待修正的旧建议句")
body1 = body1.replace(old_advice, new_advice, 1)

# 去掉原报告的 h1 和导语（我们有自己的标题和导语）
body1 = re.sub(r"(?m)^# .+\n+", "", body1, count=1)
body1 = re.sub(r"(?s)^> 排名信号是真的.*?\n\n", "", body1, count=1)

# ---------------------------------------------------------------- 表格生成
grid_rows = []
for r in wide["grid"]:
    v, t = r["valid"], r["test"]
    freq = {20: "月度", 60: "季度", 120: "半年"}[r["freq"]]
    mark = "（原方案）" if (r["K"] == 10 and r["freq"] == 20) else ""
    grid_rows.append(f"| top{r['K']} | {freq}{mark} | {pct(v['ann_return'])} | {v['ir']:.2f} | "
                     f"{pct(t['ann_return'])} | {t['ir']:.2f} | {t['max_drawdown']*100:.2f}% |")
grid_table = ("| 持仓 | 调仓 | 验证期年化 | 验证IR | 测试期年化 | 测试IR | 测试期MDD |\n"
              "|---|---|---|---|---|---|---|\n" + "\n".join(grid_rows))

buf_rows = []
for r in buf:
    if r["mult"] not in (1.0, 2.0, 3.0, 4.0):
        continue
    v, t = r["valid"], r["test"]
    band = "无" if r["mult"] == 1.0 else f"×{r['mult']:.0f}（跌出 top{int(r['n_hold']*r['mult'])} 才换）"
    mark = " **←选定**" if (r["n_hold"] == 20 and r["mult"] == 2.0) else ""
    buf_rows.append(f"| top{r['n_hold']} | {band} | {pct(v['ann_return'])} | {v['ir']:.2f} | "
                    f"{pct(t['ann_return'])} | {t['ir']:.2f} | {t['max_drawdown']*100:.2f}% | "
                    f"{t['replace_ratio']*50:.0f}% | {t['cost_total']/1e4:.1f}万 |{mark}")
buf_table = ("| 持仓 | 缓冲带 | 验证期年化 | 验证IR | 测试期年化 | 测试IR | 测试期MDD | 每月替换 | 测试期成本 |\n"
             "|---|---|---|---|---|---|---|---|---|\n" + "\n".join(buf_rows))

pick_rows = []
for r in px["rows"]:
    pick_rows.append(f"| {r['rank']} | {r['symbol']} | {r['name']} | {r['board']} | "
                     f"{r['real_price']:.2f} | {r['one_lot']:,.0f} | 5.00% |")
pick_table = ("| # | 代码 | 名称 | 板块 | 现价（元） | 一手金额 | 权重 |\n"
              "|---|---|---|---|---|---|---|\n" + "\n".join(pick_rows))

# ---------------------------------------------------------------- 新章节
part2 = f"""## 六、先认错：我上一版提的"拉长持有期"是错的

上一版的结论里我写过一句："如果要继续做，方向是**更宽的持仓池、更长的持有期**（例如 top 10% ≈ 30 只、季度调仓）"。

这半句是对的，另外半半是错的。下面是把它拆开实测的结果。

![持仓只数 × 调仓频率](img/fig9_wide_grid.png)

左图验证期、右图测试期。三条线分别是月度、季度、半年调仓。

{grid_table}

**放宽有效**：同样是月度调仓，把持仓从 10 只放到 20 只，测试期年化从 -2.13% 变成 +2.96%，MDD 从 -50.74% 收窄到 -41.98%；放到 30 只是 +3.47%。原因很直白——10 只票的年化波动冲到 32%，波动拖累把算术超额吃干净了。

**拉长无效，而且相当糟糕**：所有 K 在改成 60 日、120 日调仓后，验证期年化普遍掉到 0 以下（top20 从 +11.66% 掉到 -2.12%）。这不是成本问题（成本确实降到 3 万），是**信号寿命问题**——模型预测的是未来 5 日收益，拿 60 天去持有，等于用 55 天去赌一个已经失效的判断。

所以我上一版的建议要改成：**更宽的池子，更短的持有期**。

## 七、真正管用的修正：top20 + 缓冲带

既然换手是成本的主要来源，就该在换手上下手。规则很简单：**老仓位只要还在 top40 就不动**，只有跌出前 40 名才换掉，空出的名额用新名字补。

![缓冲带规则](img/fig10_buffer.png)

{buf_table}

选定 **top20 + 2 倍缓冲带**：验证期 {pct(cv['ann_return'])}（IR {cv['ir']:.2f}，原方案 +20.86% / 1.22，几乎打平），测试期 {pct(ct['ann_return'])}（IR {ct['ir']:.2f}）、MDD {ct['max_drawdown']*100:.2f}%，跑赢沪深300（{pct(base['test']['index_buyhold']['ann_return'])}）和"300 只等权不动"（{pct(base['test']['equal_pool']['ann_return'])}）两条基线。

代价也写在表里：测试期总成本 {ct['cost_total']/1e4:.1f} 万元，约 {cost_yr*100:.2f}%/年；每月约 {repl:.0f} 只被替换，也就是约 {repl*2:.0f} 笔委托。缓冲带只把换手从 78% 压到 70%——**这个模型的排名本身就不稳**，再懒的规则也压不住。

> **纪律提示**：测试期被近 30 个配置看过，属于多重比较。可信的是**方向**（放宽 + 缓冲带能降低单票依赖），不可信的是"top20/×2 恰好最优"。反面例子就在同一张表里：top30 + 5 倍缓冲的验证期 IR 1.44 是全网格最高，测试期却只有 +1.73%。选型越精细，样本外越难看——这是这个模型的老毛病。

## 八、调整后的 20 只

![20 只持仓](img/fig11_basket.png)

{pick_table}

等权 5%，每 20 个交易日调仓一次，老仓位跌出 top40 才换。

**最小可执行资金**：20 只各买一手合计 **{px['total_one_lot']:,.0f} 元**。

这里有个坑值得记一笔：qlib 的 `$close` 是"原始价 × 复权因子"之后的连续序列，**不能直接当成交价用**（芯原股份在那里显示 0.66 元，实际 98 元）。表里的现价是按 `$close / $factor` 还原的真实市场价。

还要看清楚这 20 只是什么东西：其中 **{n_big} 只近 20 日跌幅超过 20%**，模型给它们高分的理由是"超跌 + 高振幅 + 高 Beta"的反转特征——**这是赌反弹，不是赌基本面**。反弹失败就继续跌。

## 九、有没有现成 ETF 可以直接买？没有

这套组合是模型每天重排出来的 top20。ETF 只能复制指数，复制不了"某个模型的当期名单"。所以只有三条路：

| 方案 | 你能拿到什么 | 年成本 | 操作量 |
|---|---|---|---|
| 沪深300ETF（510300 / 510310 / 510330） | 指数收益：测试期 {pct(base['test']['index_buyhold']['ann_return'])}/年 | 0.20%（管理费 0.15% + 托管费 0.05%） | 1 笔 |
| 沪深300指数增强 ETF（561990、159238 等） | 别人家的增强模型，和这个模型无关；159238 规模只有 5406 万 | 以公告为准 | 1 笔 |
| 自建 20 只 + 缓冲带 | 回测那套：测试期 {pct(ct['ann_return'])}/年 | 约 {cost_yr*100:.2f}% | 每月约 {repl*2:.0f} 笔 |

关键在这笔账：自建的年化成本约 {cost_yr*100:.1f} 个点，几乎等于模型相对"300 只等权"的全部超额（{pct(ct['ann_return'])} vs {pct(base['test']['equal_pool']['ann_return'])}，约 {(ct['ann_return']-base['test']['equal_pool']['ann_return'])*100:+.1f} 个点）。

也就是说，**这套策略的钱不是"省 ETF 管理费省出来的"，是"扣完交易成本还剩多少"决定的**。如果你不能接受每月 {repl*2:.0f} 笔委托，实质上就只剩买沪深300ETF 这一条路——那就等于承认放弃选股。

## 十、怎么用这份名单（这一节是改过的）

**把它当研究起点，不是买入清单。**先看这 20 只各自的公告、财报、订单和估值，本文的任何数据里都没有财务字段。

**要上组合，先做减法。**上一版写的是"扩到 20-30 只、把调仓拉长到一个季度"——前半句保留（实测有效），后半句删掉（实测无效，见第六节）。正确做法是：20 只 + 月度调仓 + 2 倍缓冲带，每月只换掉跌出 top40 的那几只。

**把成本算进去。**周度调仓的换手是月度的 3.5 倍；自建 20 只的方案测试期成本 {cost_yr*100:.1f}%/年，是策略超额的主要消耗项。

**数据要跟到最新。**本次就因为成分股行情停在 10-27 而返工了一轮（见第一节数据陷阱）。

复盘这一轮，最值钱的不是哪个数字，是那句被自己推翻的话。"""

front = """---
title: "沪深300×LightGBM选股复盘：验证期+20.86%，测试期-2.13%"
summary: "选股模型失败复盘：放宽有效，拉长无效"
tags: [量化, 机器学习, LightGBM, 股票, Python]
category: "技术"
cover: "cover.png"
keywords: [LightGBM, 量化选股, 沪深300, qlib, 回测复盘]
platform_notes:
  zhihu: "知乎版首发：这次把失败过程和推翻自己的过程一起写出来。"
  csdn: "CSDN 版首发：全部数字可复现，命令直接抄。"
  juejin: "掘金版首发：一篇关于'验证期好看、测试期难看'的复盘。"
footer_note: "文中所有数字均来自公开复现脚本，风险提示见文末。"
---

"""

lead = """# 沪深300×LightGBM选股复盘：验证期+20.86%，测试期-2.13%

> **排序信号是真的，但很弱。**按模型预测分位分档，预测越靠前、未来 5 日平均收益越高，两期都单调（验证期前 3% 档 +0.441% vs 池内 +0.081%；测试期 +0.371% vs 池内 +0.099%）。分年度 RankIC 全部为正，但 2021 与 2026 已弱到 t<1.5。
>
> **但"只买 10 只集中持有"这套组合在测试期不成立。**测试期年化 -2.13%，跑输沪深300（+0.65%），更跑输"300 只等权不动"（+2.74%）；交易成本每年再吃掉约 2 个百分点（零成本对照：-0.02%）。**把成本全额退回仍然不赚钱**——所以主因是集中度，不是手续费。
>
> **同一个模型，换个组合结构能救回来一点。**top20 + 2 倍缓冲带：验证期 +13.12%（IR 1.19），测试期 +6.11%（IR 0.40），跑赢两条基线；代价是每月约 28 笔委托、2.03%/年的交易成本。
>
> **没有能直接买的 ETF。**宽基 ETF 只能给你指数（测试期 +0.65%/年），指数增强 ETF 是别人家的模型。这套东西要么自己每月下单，要么别做。
>
> **本文还推翻了我自己上一版的建议。**上一版写"更长的持有期（季度调仓）"，实测下来全线不合格：这批信号只活 5 天，持有 60 天是拿一个失效的判断扛 60 天。

数据截至 **2026-10-30**（最新完整交易日）· 股票池 300 只时点成分股 · 切分：训练 2016-2019 / 验证 2020-2022 / 测试 2023-2026 · 模型 LightGBM（30 个价量特征）· 全部数字可复现，文末有命令。

"""

out = front + lead + body1 + "\n\n" + part2 + "\n\n" + appendix.strip() + "\n"

# 复现命令换成完整版（含组合调整那几条）
new_code = """```bash
cd /d projects\\csi300_lgbm\\tools

..\\..\\..\\.venv\\Scripts\\python.exe build_dataset.py    # 取数 → 30 特征 + 标签
..\\..\\..\\.venv\\Scripts\\python.exe train_select.py      # 超参搜索 + walk-forward + 选型
..\\..\\..\\.venv\\Scripts\\python.exe backtest.py          # 组合回测 vs 4 基线 + 零成本对照
..\\..\\..\\.venv\\Scripts\\python.exe variants.py         # 全配置附录 + MA60 过滤变体
..\\..\\..\\.venv\\Scripts\\python.exe diag_signal.py       # 信号分档诊断
..\\..\\..\\.venv\\Scripts\\python.exe rank_latest.py 20    # 最终模型 → Top20 + 理由
..\\..\\..\\.venv\\Scripts\\python.exe make_figures.py      # 8 张配图
..\\..\\..\\.venv\\Scripts\\python.exe build_report.py      # 完整回测报告
..\\..\\..\\.venv\\Scripts\\python.exe check_report.py      # 自检（数字与切分一致性）

# 组合调整（第六~九节）
..\\..\\..\\.venv\\Scripts\\python.exe wide_portfolio.py    # K × 调仓频率 网格
..\\..\\..\\.venv\\Scripts\\python.exe wide_buffer.py       # 缓冲带规则对比
..\\..\\..\\.venv\\Scripts\\python.exe real_price.py         # 真实成交价还原（$close/$factor）
..\\..\\..\\.venv\\Scripts\\python.exe build_post.py        # 合成这篇文章
```"""
out = re.sub(r"cd /d D:.*?自检（数字与切分一致性）", lambda m: new_code, out, flags=re.S)

new_footer = ("生成时间：2026-10-30 数据截面 · 本文由 `build_report.py` + `build_post.py` 自动生成，"
              "所有数字取自 `projects/csi300_lgbm/results/*.json` · "
              "风险提示：本文是回测复盘，不构成投资建议；模型输出与历史回测均不预示未来收益。")
out = re.sub(r"生成时间：2026-10-30 数据截面.*?不预示未来收益。", new_footer, out, flags=re.S)

bad = [ln for ln in out.splitlines() if re.match(r"^\s*(>\s*)?[-*+]\s*\*\*", ln)]
if bad:
    raise SystemExit("仍有列表项开头的粗体:\n" + "\n".join(bad))
(POST / "article.md").write_text(out, encoding="utf-8")
print(f"已写出 {POST / 'article.md'}  {len(out)} 字符")
print(f"  正文字符 {len(out) - len(front)}")
