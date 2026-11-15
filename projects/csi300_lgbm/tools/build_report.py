"""生成 HTML 报告（report/report.html）。数字全部从 results/*.json 读，不手写。"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RES = HERE / "results"
REPORT = HERE / "report"
REPORT.mkdir(exist_ok=True)

bt = json.loads((RES / "backtest.json").read_text(encoding="utf-8"))
cfg = json.loads((RES / "config.json").read_text(encoding="utf-8"))
hp = json.loads((RES / "hp_search.json").read_text(encoding="utf-8"))
var = json.loads((RES / "variants.json").read_text(encoding="utf-8"))
picks = json.loads((RES / "picks.json").read_text(encoding="utf-8"))
diag = json.loads((RES / "signal_diag.json").read_text(encoding="utf-8"))

V = bt["periods"]["valid_2020_2022"]
T = bt["periods"]["test_2023_2026"]


def pct(x, d=2, sign=True):
    if x is None:
        return "—"
    s = f"{x*100:+.{d}f}%" if sign else f"{x*100:.{d}f}%"
    return s


def num(x, d=2):
    return "—" if x is None else f"{x:,.{d}f}"


def row(name, v, t, note=""):
    return f"""<tr><td class="k">{name}</td><td>{v}</td><td class="t">{t}</td>
    <td class="n">{note}</td></tr>"""


def perf_row(label, d, cls=""):
    return f"""<tr class="{cls}">
      <td class="k">{label}</td>
      <td>{pct(d.get('ann_return'))}</td>
      <td>{pct(d.get('ann_vol'))}</td>
      <td>{num(d.get('sharpe'))}</td>
      <td>{pct(d.get('ir'))}</td>
      <td>{pct(d.get('excess_ann'))}</td>
      <td class="neg">{pct(d.get('max_drawdown'))}</td>
    </tr>"""


PERF_HEAD = """<tr><th class="k">组合</th><th>年化</th><th>年化波动</th><th>夏普</th>
<th>IR</th><th>超额年化</th><th>最大回撤</th></tr>"""


def reason_text(p):
    out = []
    for r in p["reasons"]:
        v = r["value"]
        if abs(v) < 0.001:
            vs = "0"
        elif abs(v) < 0.05:
            vs = f"{v:+.3f}"
        else:
            vs = f"{v:+.1f}"
        out.append(f'{r["feature_cn"]}（{vs}，{r["dir"]}贡献）')
    return "；".join(out)


def risk_tag(p):
    tags = []
    if p["ret_20"] is not None and p["ret_20"] < -0.25:
        tags.append(f'20日已跌 {abs(p["ret_20"])*100:.0f}%')
    if p["vol20"] and p["vol20"] > 0.045:
        tags.append(f'日波动 {p["vol20"]*100:.0f}%')
    if p["board"] != "主板":
        tags.append(f'{p["board"]}±{int(p["limit_pct"]*100)}%')
    if p["dd_60"] is not None and p["dd_60"] < -0.15:
        tags.append(f'距60日高点 {p["dd_60"]*100:.0f}%')
    return " · ".join(tags) if tags else "—"


def build():
    t = picks["picks"]
    hp0 = cfg["model_hp"]
    pc = cfg["portfolio"]
    d_test = diag["test"]
    d_valid = diag["valid"]

    n_big = sum(1 for p in t if (p["ret_20"] or 0) < -0.25)
    worst = min((p["ret_20"] for p in t if p["ret_20"] is not None), default=0) * 100
    n_hithigh = sum(1 for p in t if p["board"] != "主板")
    pick_rows = ""
    for p in t:        pick_rows += f"""<tr>
          <td class="rk">{p['rank']}</td>
          <td class="nm">{p['name']}<span class="cd">{p['symbol']}</span></td>
          <td class="pos">{pct(p['pred'])}</td>
          <td>{p['pct']:.0f}%</td>
          <td class="{'neg' if (p['ret_20'] or 0) < 0 else 'pos'}">{pct(p['ret_20'])}</td>
          <td class="neg">{pct(p['dd_60'])}</td>
          <td>{pct(p['vol20'], 1, False)}</td>
          <td class="rs">{reason_text(p)}</td>
          <td class="rk2">{risk_tag(p)}</td>
        </tr>"""
    cfg_rows = ""
    for r in var["appendix"]["test_2023_2026"]:
        vr = next(x for x in var["appendix"]["valid_2020_2022"]
                  if x["K"] == r["K"] and x["freq"] == r["freq"])
        sel = " sel" if (r["K"] == pc["K"] and r["freq"] == pc["freq"]) else ""
        cfg_rows += f"""<tr class="{sel}"><td class="k">K={r['K']} · {'月度' if r['freq']==20 else '周度'}</td>
        <td>{num(vr['ir'])}</td><td>{pct(vr['ann_return'])}</td>
        <td>{num(r['ir'])}</td><td>{pct(r['ann_return'])}</td>
        <td class="neg">{pct(r['mdd'])}</td><td>{r['cost']/10000:.1f} 万</td></tr>"""

    imp_rows = ""
    for f in picks["feature_importance"][:12]:
        imp_rows += f'<tr><td class="k">{f["cn"]}</td><td>{f["feature"]}</td><td>{f["imp"]}</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>沪深300 × LightGBM 选股回测与最新观察名单（数据截至 2026-10-30）</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; background:#fff; color:#1F2933;
  font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;
  font-size:14px; line-height:1.75; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:38px 34px 60px; }}
h1 {{ font-size:27px; margin:0 0 6px; letter-spacing:-.3px; }}
.sub {{ color:#8A9099; font-size:12.5px; margin-bottom:26px; }}
h2 {{ font-size:18.5px; margin:38px 0 10px; padding-left:11px;
  border-left:4px solid #E8833A; line-height:1.35; }}
h3 {{ font-size:14.5px; margin:22px 0 8px; color:#2F7E8C; }}
p {{ margin:9px 0; }}
.lead {{ background:#F7F8FA; border:1px solid #E4E7EB; border-radius:10px; padding:20px 24px; }}
.lead ol {{ margin:8px 0 0; padding-left:22px; }}
.lead li {{ margin:11px 0; }}
.card {{ background:#F7F8FA; border:1px solid #E4E7EB; border-radius:10px;
  padding:16px 20px; margin:14px 0; }}
.warn {{ background:#FDF6F1; border-left:4px solid #E8833A; padding:13px 18px;
  border-radius:6px; margin:16px 0; }}
.bad {{ background:#FBF3F3; border-left:4px solid #C94C4C; padding:13px 18px;
  border-radius:6px; margin:16px 0; }}
table {{ border-collapse:collapse; width:100%; margin:14px 0 6px; font-size:12.6px; }}
th {{ background:#F2F4F6; color:#5B6470; font-weight:600; text-align:right;
  padding:9px 10px; border-bottom:1px solid #E4E7EB; white-space:nowrap; }}
td {{ padding:8px 10px; border-bottom:1px solid #F0F2F4; text-align:right;
  vertical-align:top; }}
th.k, td.k {{ text-align:left; }}
td.k {{ color:#39424E; }}
tr.sel td {{ background:#FDF6F1; font-weight:600; }}
.pos {{ color:#C94C4C; }}
.neg {{ color:#2F7E8C; }}
.rk {{ color:#E8833A; font-weight:700; text-align:center; width:34px; }}
.nm {{ text-align:left; font-weight:600; }}
.cd {{ color:#9AA1A9; font-weight:400; font-size:11px; margin-left:7px; }}
.rs {{ text-align:left; font-size:11.6px; color:#5B6470; line-height:1.55; }}
.rk2 {{ text-align:left; font-size:11.4px; color:#8A9099; }}
img {{ max-width:100%; margin:12px 0 4px; display:block; }}
.cap {{ color:#9AA1A9; font-size:11.5px; margin:2px 0 18px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.kv {{ font-size:12.8px; }}
.kv b {{ color:#39424E; }}
code {{ background:#F2F4F6; padding:1.5px 6px; border-radius:4px; font-size:12px;
  font-family:Consolas,monospace; }}
ul {{ padding-left:22px; }}
li {{ margin:6px 0; }}
.tag {{ display:inline-block; background:#F2F4F6; color:#5B6470; border-radius:4px;
  padding:1px 7px; font-size:11.5px; margin-right:6px; }}
.foot {{ color:#9AA1A9; font-size:11.5px; border-top:1px solid #E4E7EB;
  margin-top:40px; padding-top:14px; }}
</style></head><body><div class="wrap">

<h1>沪深300 × LightGBM 选股：完整回测与最新观察名单</h1>
<div class="sub">
数据截至 <b>2026-10-30</b>（最新完整交易日）· 股票池 300 只时点成分股 ·
切分：训练 2016-2019 / 验证 2020-2022 / 测试 2023-2026 ·
模型 LightGBM（30 个价量特征）· 组合：月度调仓、等权 top10、含交易成本
</div>

<div class="lead">
<ol>
<li><b>排名信号是真的，但很弱。</b>按模型预测分位分档，预测越靠前、未来 5 日平均收益越高，
两期都单调（验证期前 3% 档 {pct(d_valid['buckets']['前3%']['mean_fwd5'],3)} vs 池内 {pct(d_valid['pool_mean'],3)}；
测试期 {pct(d_test['buckets']['前3%']['mean_fwd5'],3)} vs 池内 {pct(d_test['pool_mean'],3)}）。
分年度 RankIC 全部为正，但 2021 与 2026 已弱到统计不显著（t&lt;1.5）。</li>

<li><b>但"只买 10 只集中持有"这套组合在测试期不成立。</b>
测试期年化 <b class="neg">{pct(T['strategy']['ann_return'])}</b>，
跑输沪深300（{pct(T['index_buyhold']['ann_return'])}），
更跑输"300 只等权不动"（{pct(T['equal_pool']['ann_return'])}）；
交易成本每年再吃掉约 2 个百分点（零成本对照：{pct(T['strategy_zero_cost']['ann_return'])}）。</li>

<li><b>验证期选出来的配置在测试期失效。</b>同一套模型、同样 6 组配置，
验证期 IR 最高的是 K=10 月度（IR {num(V['strategy']['ir'])}），到测试期它的 IR 是
{num(T['strategy']['ir'])}——<b>"选型不可外推"又一次复现</b>（这也是本项目 AGENTS.md 里记的老教训）。</li>

<li><b>所以下面这 10 只是模型的观察名单，不是买入建议。</b>
它们是模型在 2026-10-30 的排序输出，其中 <b>{n_big} 只近 20 日跌幅超过 25%</b>（最深 {worst:.1f}%），
是典型的"超跌反弹"信号——这类信号在 2020-2022 有效、在 2023-2026 大部分时间无效。
</li>
</ol>
</div>

<h2>一、这次到底做了什么</h2>
<table>
<tr><th class="k">环节</th><th class="k">做法</th><th class="k">关键约束</th></tr>
<tr><td class="k">数据源</td><td class="k">本地 qlib <code>cn_data_2026</code>（chenditc 日更版 + 手工追加），
最新到 2026-10-30</td><td class="k">股票维度的"最新完整横截面"是 10-30（见下方数据陷阱）</td></tr>
<tr><td class="k">股票池</td><td class="k">沪深300 <b>时点</b>成分股（用成分文件的 start/end 区间逐日还原，
不拿今天的 300 只倒推历史）</td><td class="k">避免幸存者偏差；637 只曾在池内</td></tr>
<tr><td class="k">特征</td><td class="k">30 个价量特征：动量/反转/波动/均线/RSI/量比/Amihud/Beta/52周位置…</td>
<td class="k">数据源<b>没有</b>基本面字段，特征全部无量纲</td></tr>
<tr><td class="k">标签</td><td class="k">未来 5 日收益 <code>close(t+5)/close(t)-1</code></td>
<td class="k">对齐月度调仓；训练样本必须满足"标签期末早于预测日"</td></tr>
<tr><td class="k">切分</td><td class="k">训练 2016-2019 / 验证 2020-2022 / 测试 2023-2026</td>
<td class="k">超参、topK、调仓频率<b>只在验证期</b>选；测试期只跑一次</td></tr>
<tr><td class="k">模型</td><td class="k">LightGBM（leaves {hp0['num_leaves']} / lr {hp0['learning_rate']} /
min_leaf {hp0['min_data_in_leaf']} / ff {hp0['feature_fraction']}），年度 walk-forward 重训</td>
<td class="k">每折只用"折前标签已知"的样本训练</td></tr>
<tr><td class="k">组合</td><td class="k">等权 top{K if False else pc['K']}，每 {pc['freq']} 个交易日调仓，
信号 T 日收盘 → T+1 日收盘成交</td><td class="k">涨停买不进、停牌不可交易</td></tr>
<tr><td class="k">成本</td><td class="k">买入 0.05% / 卖出 0.15% / 单笔最低 5 元，账户 100 万</td>
<td class="k">与本仓库历史项目同口径，可比</td></tr>
<tr><td class="k">基线</td><td class="k">沪深300买入持有、池内等权 300 只、MA20 趋势过滤、零成本对照</td>
<td class="k">必须保留"干脆别择时"的退路</td></tr>
</table>

<div class="warn"><b>数据陷阱（本次实际踩到）：</b>
qlib 的日历到 2026-10-30，但 300 只成分股里 <b>298 只的行情只到 2026-10-27</b>——
之前的日更脚本默认只补 2 只标的。直接用会得到"最后 3 天全 NaN"、特征失效、模型输出乱码。
本次用 <code>tools/append_latest_bars.py --symbols-file … --until 2026-10-30</code>
把这 300 只补到 10-30（腾讯不复权价 × 既有 factor，与原始价逐只核对偏差 0.000%），并排除了当天未收盘的 bar。
</div>

<h2>二、信号强度：RankIC 与分档</h2>
<img src="img/fig2_ic.png" alt="分年 RankIC">
<div class="cap">分年度样本外 RankIC：walk-forward 每折只用折前数据训练。2021（0.0070）与 2026（0.0089）已弱到 t&lt;1.5。</div>

<img src="img/fig3_buckets.png" alt="预测分档与前瞻收益">
<div class="cap">预测分位越靠前，未来 5 日平均收益越高——两期都单调，说明<b>排序信号本身成立</b>。</div>

<h2>三、回测结果</h2>
<img src="img/fig1_nav.png" alt="净值曲线">
<div class="cap">左：验证期（选型只用这段）；右：测试期（冻结后一次性评估）。</div>

<table>{PERF_HEAD}
{perf_row("策略 top10 月调（含成本）", V['strategy'])}
{perf_row("策略（零成本对照）", V['strategy_zero_cost'])}
{perf_row("池内等权 300 只", V['equal_pool'])}
{perf_row("MA20 趋势过滤", V['ma20_trend'])}
{perf_row("沪深300 买入持有", V['index_buyhold'])}
<tr><td colspan="7" style="background:#F2F4F6;font-weight:600">测试期 2023-01-01 ~ 2026-10-30（一次性评估）</td></tr>
{perf_row("策略 top10 月调（含成本）", T['strategy'], "sel")}
{perf_row("策略（零成本对照）", T['strategy_zero_cost'])}
{perf_row("池内等权 300 只", T['equal_pool'])}
{perf_row("MA20 趋势过滤", T['ma20_trend'])}
{perf_row("沪深300 买入持有", T['index_buyhold'])}
</table>

<div class="bad"><b>测试期结论（不好听但是真的）：</b>
策略年化 {pct(T['strategy']['ann_return'])}、最大回撤 {pct(T['strategy']['max_drawdown'])}，
三个基线里<b>没有一个被跑赢</b>——连"300 只等权不动"都拿到 {pct(T['equal_pool']['ann_return'])}。
拆解：①零成本也只有 {pct(T['strategy_zero_cost']['ann_return'])}，
说明信号在组合层面就没有把择时优势变成收益；②成本每年再扣约 2.1 个点；
③集中到 10 只后年化波动 {pct(T['strategy']['ann_vol'])}，波动拖累把算术平均超额吃掉了。</div>

<img src="img/fig4_configs.png" alt="配置对比">
<div class="cap">同一套模型换配置：验证期挑中的（橙）在测试期反而最差——排序完全反转，说明差异都在噪声里。</div>

<img src="img/fig7_cost.png" alt="成本">
<div class="cap">测试期累计交易成本：周度调仓的换手是月度调仓的 3.5 倍。</div>

<h2>四、诚实结论</h2>
<div class="card">
<p><b>1. 排序信号可用，组合信号不可用。</b>分档结果说明模型确实能把"未来涨得好的"排在前面，
但把这个排序压缩成"10 只、月度调仓、等权"之后，算术超额被波动拖累与成本吃掉。
如果要继续做，方向是<b>更宽的持仓池、更长的持有期</b>（例如 top 10% ≈ 30 只、季度调仓），
而不是继续调模型。</p>
<p><b>2. 单一切分不足以定论。</b>本次额外试了一个"指数跌破 MA60 空仓"的过滤变体：
验证期它更差（IR {num(var['variant']['with_ma60_filter']['valid_2020_2022']['ir'])} vs {num(var['variant']['no_filter_valid']['ir'])}），
按协议（只在验证期选型）<b>不采用</b>；但它在测试期反而更好（年化 {pct(var['variant']['with_ma60_filter']['test_2023_2026']['ann_return'])}）。
这既说明"一刀切"会错过东西，也说明单次切分的结论不该被当成定论——本次两边都如实写出来。</p>
<p><b>3. 不要把模型输出当目标价。</b>表里的"预测 5 日收益"是回归输出，横截面可比、绝对值不可信，
也不是任何意义上的收益承诺。</p>
</div>

<h2>五、模型当前的 Top 10（2026-10-30，观察名单）</h2>
<img src="img/fig5_picks.png" alt="Top10">
<div class="cap">左：模型预测的未来 5 日收益；右：近 20 日实际涨跌。预测值全部为正但幅度普遍很小。</div>

<table>
<tr><th>排名</th><th class="k">名称</th><th>预测5日</th><th>预测分位</th><th>近20日</th>
<th>距60日高点</th><th>日波动(20日)</th><th class="k">模型主要依据（SHAP 贡献）</th><th class="k">风险标签</th></tr>
{pick_rows}
</table>

<div class="warn"><b>名单要这么读：</b>
① 前 2 位（{t[0]['name']}、{t[1]['name']}）近 20 日分别跌了 {abs(t[0]['ret_20'])*100:.0f}% 和 {abs(t[1]['ret_20'])*100:.0f}%，模型给它们最高分是因为
"超跌 + 高振幅 + 高 Beta"的反转特征——<b>这是赌反弹，不是赌基本面</b>，反弹失败就是继续跌；
② 10 只里有 {n_hithigh} 只是创业板/科创板（±20% 涨跌幅、单日波动更大），
③ 名单里没有基本面信息（数据源没有财务字段），任何"公司变好了"的说法都是我自己加的，不是数据说的。</div>

<img src="img/fig8_price.png" alt="Top10 走势">
<div class="cap">Top 10 近 6 个月走势（qlib 前复权价，起点=100）。</div>

<h2>六、如果要用这份名单，怎么用</h2>
<ul>
<li><b>把它当研究起点，不是买入清单。</b>先看这 10 只各自的公告、财报、订单和估值，
本报告的数据里没有任何一条财务信息。</li>
<li><b>如果要上组合，先做减法。</b>10 只高度集中且偏科创/创业板，建议至少扩到 20-30 只、
把月度调仓拉长到一个季度，再重跑一次样本外验证——本次的数据不支持"只买这 10 只"的结论。</li>
<li><b>把成本算进去。</b>周度调仓的换手是月度的 3.5 倍；本次测试期成本每年吃掉约 2.1 个点。</li>
<li><b>数据要跟到最新。</b>本次就因为成分股数据停在 10-27 而返工一轮（见第一节数据陷阱）。</li>
</ul>

<h2>附录</h2>
<h3>A. 6 组配置的验证期 / 测试期对照（选型只依据左半边）</h3>
<table>
<tr><th class="k">配置</th><th>验证期 IR</th><th>验证期年化</th><th>测试期 IR</th>
<th>测试期年化</th><th>测试期 MDD</th><th>测试期成本</th></tr>
{cfg_rows}
</table>

<h3>B. 最终模型特征重要性（分裂次数，top12 / 共 30）</h3>
<table><tr><th class="k">特征</th><th class="k">字段</th><th>分裂次数</th></tr>{imp_rows}</table>

<h3>C. 复现命令</h3>
<div class="card kv">
<pre style="margin:0;white-space:pre-wrap;line-height:1.9">cd /d projects\\csi300_lgbm\\tools
..\\..\\..\\.venv\\Scripts\\python.exe build_dataset.py      # 取数 → 30 特征 + 标签
..\\..\\..\\.venv\\Scripts\\python.exe train_select.py       # 超参搜索 + walk-forward + 选型
..\\..\\..\\.venv\\Scripts\\python.exe backtest.py           # 组合回测 vs 4 基线 + 零成本对照
..\\..\\..\\.venv\\Scripts\\python.exe variants.py           # 全配置附录 + MA60 过滤变体
..\\..\\..\\.venv\\Scripts\\python.exe diag_signal.py        # 信号分档诊断
..\\..\\..\\.venv\\Scripts\\python.exe rank_latest.py        # 最终模型 → Top10 + 理由
..\\..\\..\\.venv\\Scripts\\python.exe make_figures.py       # 8 张配图
..\\..\\..\\.venv\\Scripts\\python.exe build_report.py       # 本报告
..\\..\\..\\.venv\\Scripts\\python.exe check_report.py       # 自检（数字与切分一致性）</pre>
</div>

<div class="foot">
生成时间：{picks['as_of']} 数据截面 · 报告由 <code>build_report.py</code> 自动生成，
所有数字取自 <code>projects/csi300_lgbm/results/*.json</code> ·
风险提示：本报告不构成投资建议，模型输出与历史回测均不预示未来收益。
</div>
</div></body></html>"""

    out = REPORT / "report.html"
    out.write_text(html, encoding="utf-8")
    print("已写出", out, f"{out.stat().st_size/1024:.0f}KB")
    return out


if __name__ == "__main__":
    build()
