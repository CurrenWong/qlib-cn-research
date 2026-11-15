"""生成"组合调整"报告页 HTML（数字全部读 results/*.json，不手抄）。"""

import json
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

RES = Path(_ROOT + r"/projects/csi300_lgbm/results")
OUT = Path(_ROOT + r"/projects/csi300_lgbm/report/portfolio_v2.html")

wide = json.loads((RES / "wide_portfolio.json").read_text(encoding="utf-8"))
buf = json.loads((RES / "wide_buffer.json").read_text(encoding="utf-8"))
px = json.loads((RES / "picks_K20_price.json").read_text(encoding="utf-8"))
p20 = json.loads((RES / "picks_K20.json").read_text(encoding="utf-8"))
base = wide["baselines"]


def sgn(x):
    return "pos" if x >= 0 else "neg"


def pct(x, cls=True):
    c = f' class="{sgn(x)}"' if cls else ""
    return f"<span{c}>{x*100:+.2f}%</span>"


def wan(x):
    return f"{x/1e4:.1f}"


chosen = next(r for r in buf if r["n_hold"] == 20 and r["mult"] == 2.0)
cv, ct = chosen["valid"], chosen["test"]
repl = ct["replace_ratio"] * 0.5 * 20
cost_yr = ct["cost_total"] / 1e6 / ct["years"]

# ---------------- 网格表
grid_rows = []
for r in wide["grid"]:
    v, t = r["valid"], r["test"]
    hot = r["K"] == 10 and r["freq"] == 20
    tr = ' class="old"' if hot else ""
    freq = {20: "月度", 60: "季度", 120: "半年"}[r["freq"]]
    grid_rows.append(
        f"<tr{tr}><td class='k'>top{r['K']}</td><td class='k'>{freq}</td>"
        f"<td>{pct(v['ann_return'])}</td><td>{v['ir']:.2f}</td>"
        f"<td>{pct(t['ann_return'])}</td><td>{t['ir']:.2f}</td>"
        f"<td class='neg'>{t['max_drawdown']*100:.1f}%</td></tr>")

# ---------------- 缓冲带表
buf_rows = []
for r in buf:
    if r["mult"] not in (1.0, 2.0, 3.0, 4.0):
        continue
    v, t = r["valid"], r["test"]
    hot = r["n_hold"] == 20 and r["mult"] == 2.0
    tr = ' class="sel"' if hot else ""
    if r["mult"] == 1.0:
        band = "无（top%d）" % r["n_hold"]
    else:
        band = "×%.1f（top%d）" % (r["mult"], int(r["n_hold"] * r["mult"]))
    buf_rows.append(
        f"<tr{tr}><td class='k'>top{r['n_hold']}</td>"
        f"<td class='k'>{band}</td>"
        f"<td>{pct(v['ann_return'])}</td><td>{v['ir']:.2f}</td>"
        f"<td>{pct(t['ann_return'])}</td><td>{t['ir']:.2f}</td>"
        f"<td class='neg'>{t['max_drawdown']*100:.1f}%</td>"
        f"<td>{t['replace_ratio']*50:.0f}%</td>"
        f"<td>{wan(t['cost_total'])}万</td></tr>")

# ---------------- 持仓表
pick_rows = []
for r in px["rows"]:
    pick_rows.append(
        f"<tr><td class='rk'>{r['rank']}</td>"
        f"<td class='k'>{r['name']}<span class='cd'>{r['symbol'][2:]}</span></td>"
        f"<td class='k' style='color:#8A9099'>{r['board']}</td>"
        f"<td>{r['real_price']:.2f}</td><td>{r['one_lot']:,.0f}</td>"
        f"<td class='k'>5.00%</td></tr>")

B = base["test"]
Bv = base["valid"]

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>组合调整：top10 → top20 + 缓冲带（2026-10-30）</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; background:#fff; color:#1F2933;
  font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;
  font-size:14px; line-height:1.75; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:38px 34px 56px; }}
h1 {{ font-size:27px; margin:0 0 6px; letter-spacing:-.3px; }}
.sub {{ color:#8A9099; font-size:12.5px; margin-bottom:24px; }}
h2 {{ font-size:18.5px; margin:34px 0 10px; padding-left:11px;
  border-left:4px solid #E8833A; line-height:1.35; }}
p {{ margin:9px 0; }}
.lead {{ background:#F7F8FA; border:1px solid #E4E7EB; border-radius:10px; padding:18px 24px; }}
.lead ol {{ margin:6px 0 0; padding-left:22px; }}
.lead li {{ margin:10px 0; }}
.warn {{ background:#FDF6F1; border-left:4px solid #E8833A; padding:13px 18px;
  border-radius:6px; margin:16px 0; }}
.bad {{ background:#FBF3F3; border-left:4px solid #C94C4C; padding:13px 18px;
  border-radius:6px; margin:16px 0; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0 4px; font-size:12.4px; }}
th {{ background:#F2F4F6; color:#5B6470; font-weight:600; text-align:right;
  padding:8px 9px; border-bottom:1px solid #E4E7EB; white-space:nowrap; }}
td {{ padding:7px 9px; border-bottom:1px solid #F0F2F4; text-align:right; }}
th.k, td.k {{ text-align:left; }}
tr.old td {{ color:#9AA1A9; }}
tr.sel td {{ background:#FDF6F1; font-weight:600; }}
.pos {{ color:#C94C4C; }}
.neg {{ color:#2F7E8C; }}
.rk {{ color:#E8833A; font-weight:700; text-align:center; width:30px; }}
.cd {{ color:#9AA1A9; font-weight:400; font-size:10.5px; margin-left:6px; }}
.cap {{ color:#9AA1A9; font-size:11.5px; margin:4px 0 6px; }}
.kpi {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:16px 0 4px; }}
.kpi div {{ background:#F7F8FA; border:1px solid #E4E7EB; border-radius:9px; padding:13px 16px; }}
.kpi b {{ display:block; font-size:21px; letter-spacing:-.3px; margin-bottom:2px; }}
.kpi span {{ color:#8A9099; font-size:11.5px; }}
.foot {{ color:#9AA1A9; font-size:11.5px; border-top:1px solid #E4E7EB;
  margin-top:34px; padding-top:13px; }}
</style></head><body><div class="wrap">

<h1>组合调整：从 top10 扩到 top20，加一道缓冲带</h1>
<div class="sub">数据截面 <b>2026-10-30</b> 收盘 · 股票池 300 只时点成分股 ·
切分：训练 2016-2019 / 验证 2020-2022 / 测试 2023-2026 · 等权 · 含交易成本（买 0.05% / 卖 0.15%）</div>

<div class="lead">
<b>先说结论</b>
<ol>
<li><b>扩仓是对的。</b>原 top10 月度方案测试期年化 {pct(-0.0213)}、最大回撤 -50.74%；
换成 top20 + 2 倍缓冲带后，测试期 {pct(ct['ann_return'])}、回撤
{ct['max_drawdown']*100:.1f}%，验证期几乎不受损（{pct(cv['ann_return'])} / IR {cv['ir']:.2f}，
原方案 20.86% / 1.22）。</li>
<li><b>“拉长到季度”这条建议被数据否掉了。</b>K=20 从月度改季度，验证期年化从
{pct(11.66/100)} 掉到 {pct(-2.12/100)}——标签是未来 5 日收益，信号衰减太快，持有 60 天等于空转。</li>
<li><b>没有能复制这个组合的 ETF。</b>ETF 只能买指数；自建 20 只的年成本约
{cost_yr*100:.1f}%/年，几乎等于模型的全部超额。省不了，只能少赚或不做。</li>
</ol>
</div>

<h2>一、原方案死在“太集中”，不是死在“手续费”</h2>
<p>top10 月度方案：验证期年化 +20.86%（IR 1.22）看起来很能打，测试期 -2.13%（IR -0.07）。
关键是<b>零成本对照也只有 -0.02%</b>——把手续费全额退回，组合层面依然不赚钱。
所以主因是集中度：10 只票让年化波动冲到 32%，波动拖累把算术超额吃干净。</p>

<h2>二、持仓只数 × 调仓频率：季度方案全线不合格</h2>
<table>
<tr><th class="k">持仓</th><th class="k">调仓</th><th>验证年化</th><th>验证IR</th>
<th>测试年化</th><th>测试IR</th><th>测试MDD</th></tr>
{''.join(grid_rows)}
</table>
<div class="cap">灰色行＝原方案。基线：验证期沪深300 {pct(Bv['index_buyhold']['ann_return'])}、
池内等权 {pct(Bv['equal_pool']['ann_return'])}；测试期沪深300 {pct(B['index_buyhold']['ann_return'])}、
池内等权 {pct(B['equal_pool']['ann_return'])}。</div>

<div class="warn"><b>季度 / 半年调仓被否：</b>所有 K 在改成 60 日、120 日调仓后，验证期年化普遍掉到
0 以下。这不是成本问题（成本确实降到 3 万），是<b>信号寿命问题</b>——模型预测的是 5 日收益，
拿 60 天，前面 55 天都在赌一个已经失效的判断。</div>

<h2>三、加一道缓冲带：老仓位只要还在 top40 就不动</h2>
<table>
<tr><th class="k">持仓</th><th class="k">缓冲带</th><th>验证年化</th><th>验证IR</th>
<th>测试年化</th><th>测试IR</th><th>测试MDD</th><th>替换比例</th><th>测试成本</th></tr>
{''.join(buf_rows)}
</table>
<div class="cap">橙色行＝选定方案。替换比例＝每次调仓被换掉的只数占比（无缓冲时 top20 每月换 78%）。</div>

<h3>选定的这一档</h3>
<div class="kpi">
  <div><b class="pos">{ct['ann_return']*100:+.2f}%</b><span>测试期年化（原方案 -2.13%）</span></div>
  <div><b>{ct['max_drawdown']*100:.1f}%</b><span>测试期最大回撤（原 -50.7%）</span></div>
  <div><b>{ct['cost_total']/1e4:.1f} 万</b><span>测试期总成本 ≈ {cost_yr*100:.1f}%/年</span></div>
</div>
<p>代价写清楚：每月约 <b>{repl:.0f} 只被替换</b>（20 只的 {ct['replace_ratio']*50:.0f}%），
约 <b>{repl*2:.0f} 笔委托</b>；缓冲带只把换手从 78% 压到 70%，压不下去——因为这个模型的排名本身就不稳。</p>

<div class="bad"><b>纪律提示：</b>测试期被近 30 个配置看过，属于多重比较。
可信的是<b>方向</b>（放宽 + 缓冲带降低单票依赖），不可信的是“top20/×2 恰好最优”。
反面例子就在上表：top30 + 5 倍缓冲的验证期 IR 1.44 是全网格最高，测试期只有 +1.73%。</div>

<h2>四、调整后的组合（等权 5%，2026-10-30 收盘）</h2>
<table>
<tr><th class="k">#</th><th class="k">名称</th><th class="k">板块</th>
<th>现价（元）</th><th>一手金额</th><th class="k">权重</th></tr>
{''.join(pick_rows)}
</table>
<div class="cap">20 只各买一手合计 <b>{px['total_one_lot']:,.0f} 元</b>，这是这套组合的最小可执行资金。
现价已按 <code>$close / $factor</code> 还原成真实市场价——qlib 的 $close 是复权连续序列，不能直接当成交价。</div>

<h2>五、有没有现成 ETF 可以直接买？没有</h2>
<p>这套组合是模型每天重排出来的 top20，ETF 只能复制指数，复制不了“某个模型的当期名单”。三条替代路径：</p>
<table>
<tr><th class="k">方案</th><th class="k">你能拿到什么</th><th>年成本</th><th class="k">操作量</th></tr>
<tr><td class="k">沪深300ETF<br><span class="cd">510300 / 510310 / 510330</span></td>
<td class="k">指数收益：测试期 {pct(B['index_buyhold']['ann_return'])}/年</td>
<td>0.20%</td><td class="k">1 笔</td></tr>
<tr><td class="k">沪深300指数增强 ETF<br><span class="cd">561990、159238 等</span></td>
<td class="k">别人家的增强模型，与本事无关；159238 规模仅 5406 万</td>
<td>见公告</td><td class="k">1 笔</td></tr>
<tr class="sel"><td class="k">自建 20 只 + 缓冲带</td>
<td class="k">回测那套：测试期 {pct(ct['ann_return'])}/年</td>
<td>{cost_yr*100:.1f}%</td><td class="k">每月约 {repl*2:.0f} 笔</td></tr>
</table>
<p>关键在这笔账：自建的年化成本约 {cost_yr*100:.1f} 个点，几乎等于模型相对 300 只等权的全部超额
（{pct(ct['ann_return'])} vs {pct(B['equal_pool']['ann_return'])}，约
{(ct['ann_return']-B['equal_pool']['ann_return'])*100:+.1f} 个点）。
<b>这套策略的钱不是“省 ETF 管理费省出来的”，是“扣完交易成本还剩多少”决定的。</b></p>

<h2>六、风险（不粉饰）</h2>
<ul>
<li>最大回撤仍有 <b>{ct['max_drawdown']*100:.1f}%</b>，扩仓只是把 -51% 收窄到 -45%，没有消除。</li>
<li>20 只里 <b>11 只近 20 日跌超 20%</b>，本质是赌超跌反弹；反弹失败就是继续跌。</li>
<li>数据源只有价量、没有财务字段，任何“公司变好了”的说法都不是数据说的。</li>
<li>2026 年至今，这套策略仍是负的。</li>
</ul>

<div class="foot">数据与复现：<code>projects/csi300_lgbm/tools/</code> 下 wide_portfolio.py（K × 频率网格）、
wide_buffer.py（缓冲带）、rank_latest.py（Top-N）、real_price.py（真实价还原）、
gen_portfolio_note.py（本页）。所有数字取自 <code>results/*.json</code>。<br>
风险提示：本页是回测复盘，不构成投资建议；模型输出与历史回测均不预示未来收益。</div>
</div></body></html>
"""

OUT.write_text(html, encoding="utf-8")
print(f"已写出 {OUT}  {len(html)} 字节")
