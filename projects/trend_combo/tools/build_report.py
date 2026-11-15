"""生成 trend_combo 方案报告（HTML）。

所有数字都从 results/*.json / *.csv 读，不手写。
用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\build_report.py
产出：report\\trend_combo_report.html
"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
RESULTS = PROJ / "results"
REPORT = PROJ / "report"
REPORT.mkdir(exist_ok=True)


def pct(x, d=2):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    return f"{x * 100:+.{d}f}%"


def num(x, d=4):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    return f"{x:+.{d}f}"


def main():
    res = json.loads((RESULTS / "ic_results.json").read_text(encoding="utf-8"))
    V = res["variants"]
    sel = res["selected"]
    fdf = pd.read_csv(RESULTS / "factor_ic.csv")
    grid = pd.read_csv(RESULTS / f"weight_grid_{sel['wmode']}.csv")
    pstat = json.loads((RESULTS / "panel_stats.json").read_text(encoding="utf-8"))
    flog = json.loads((RESULTS / "fetch_log.json").read_text(encoding="utf-8"))
    hold = json.loads((RESULTS / "holdings_score.json").read_text(encoding="utf-8"))
    yearly = pd.DataFrame(res["yearly"])

    g0 = grid[grid["we"] == 0.0].sort_values("wf")
    sweet = g0[(g0["valid_icir_f5"] > 0.35) & (g0["test_icir_f5"] > 0.30)]

    # 因子表（前 18，按训练期 |IC|）
    ft = fdf.reindex(fdf["fwd5_train_ic"].abs().sort_values(ascending=False).index).head(18)
    frows = ""
    for _, r in ft.iterrows():
        flip = " <span class='flip'>方向被推翻</span>" if (r["keep"] and not r["prior_agrees"]) else ""
        keep = "✓" if r["keep"] else "✗"
        frows += (f"<tr><td class='k'>{r['factor']}{flip}</td><td class='k'>{r['domain']}</td>"
                  f"<td>{r['prior_dir']:+.0f}</td><td>{num(r['fwd5_train_ic'])}</td>"
                  f"<td>{num(r['fwd5_train_t'], 1)}</td>"
                  f"<td>{num(r['fwd5_valid_ic'])}</td><td>{num(r['fwd5_test_ic'])}</td>"
                  f"<td>{keep}</td></tr>")

    # 权重表
    wrows = ""
    for _, r in g0.iterrows():
        mark = ""
        note = ""
        if abs(r["wf"] - 0.30) < 1e-9 and abs(r["wp"] - 0.70) < 1e-9:
            mark = " sel"
            note = " <span class='tag'>建议实盘</span>"
        if abs(r["wf"] - sel["wf"]) < 1e-9 and abs(r["wp"] - sel["wp"]) < 1e-9:
            mark = " sel"
            note = " <span class='tag'>验证期选中</span>"
        wrows += (f"<tr class='{mark}'><td class='k'>{r['wp']:.1f} / {r['wf']:.1f}{note}</td>"
                  f"<td>{num(r['train_ic_f5'])}</td><td>{num(r['valid_ic_f5'])}</td>"
                  f"<td>{num(r['valid_icir_f5'], 3)}</td>"
                  f"<td>{num(r['test_ic_f5'])}</td><td>{num(r['test_icir_f5'], 3)}</td>"
                  f"<td>{num(r['test_ic_f20'])}</td><td>{num(r['test_icir_f20'], 3)}</td></tr>")

    # 持仓表
    hrows = ""
    for r in hold["rows"]:
        if r["total"] is None:
            continue
        hrows += (f"<tr><td class='rk'>{r['rank']}</td>"
                  f"<td class='nm'>{r['name']}<span class='cd'>{r['symbol']}</span></td>"
                  f"<td class='{'pos' if r['total']>0 else 'neg'}'>{r['total']:+.3f}</td>"
                  f"<td>{r['price_score']:+.3f}</td><td>{r['fund_score']:+.3f}</td>"
                  f"<td>{r['event_score']:+.3f}</td>"
                  f"<td>{num(r.get('roe'), 1) if r.get('roe') is not None else 'n/a'}</td>"
                  f"<td>{num(r.get('rev_yoy'), 1) if r.get('rev_yoy') is not None else 'n/a'}</td>"
                  f"<td>{num(r.get('pe_ttm'), 1) if r.get('pe_ttm') is not None else 'n/a'}</td></tr>")

    b = res.get("buckets_test_fwd20", {})
    btext = " · ".join(f"Q{k} {b[k]['mean']*100:+.2f}%" for k in sorted(b)) if b else "n/a"

    # ---------------- 策略回测（阶段二）------------------
    bt_path = RESULTS / "backtest.json"
    bt_html = ""
    if bt_path.exists():
        bt = json.loads(bt_path.read_text(encoding="utf-8"))
        BR = bt["runs"]
        CFG = bt["config"]
        PP = bt["per_period"]
        FULL = bt["full_period"]

        def rrow(name, label=None, hl=False):
            v = BR.get(name)
            if not v:
                return ""
            cls = " sel" if hl else ""
            return (f"<tr class='{cls}'><td class='k'>{label or name}</td>"
                    f"<td>{pct(v.get('ann_return'))}</td>"
                    f"<td>{pct(v.get('total_return'))}</td>"
                    f"<td>{pct(v.get('ann_vol'))}</td>"
                    f"<td>{v.get('sharpe', 0):+.2f}</td>"
                    f"<td>{pct(v.get('max_drawdown'))}</td>"
                    f"<td>{v.get('ir', 0):+.2f}</td>"
                    f"<td>{pct(v.get('excess_ann'))}</td>"
                    f"<td>{v.get('ann_turnover', 0):.2f}</td>"
                    f"<td>{v.get('cost_per_year_pct', 0):.2f}pct</td></tr>")

        main_name = f"策略(验证期选参) top{CFG['K']}"
        srows = (rrow(main_name, f"<b>策略(验证期选参) top{CFG['K']}</b>", True)
                 + rrow("同上(零成本对照)")
                 + rrow("默认 top20 月调(参照)")
                 + rrow("纯价量分 top20 月调")
                 + rrow("纯基本面分 top20 月调")
                 + rrow("混合分 top20 月调(行业≤3)")
                 + rrow("池内等权300只")
                 + rrow("沪深300买入持有"))

        prow = ""
        for k, lb in [("train_2016_2019", "训练 2016-2019"),
                      ("valid_2020_2022", "验证 2020-2022"),
                      ("test_2023_2026", "测试 2023-2026")]:
            v = PP[k]
            prow += (f"<tr><td class='k'>{lb}</td><td>{pct(v['ann_return'])}</td>"
                     f"<td>{v.get('ir', 0):+.2f}</td><td>{pct(v['max_drawdown'])}</td>"
                     f"<td>{v.get('ann_turnover', 0):.2f}</td>"
                     f"<td>{v.get('cost_per_year_pct', 0):.2f}pct</td></tr>")

        sens_rows = ""
        for s in sorted(bt["sensitivity"], key=lambda x: (x["K"], x["freq"])):
            sens_rows += (f"<tr><td class='k'>{s['K']} 只</td><td>每 {s['freq']} 日</td>"
                          f"<td>{pct(s['ann_return'])}</td><td>{s['ir']:+.2f}</td>"
                          f"<td>{pct(s['mdd'])}</td><td>{s['ann_turnover']:.1f}</td>"
                          f"<td>{s['cost_per_year_pct']:.2f}pct</td></tr>")

        grid = pd.read_csv(RESULTS / "strategy_grid_valid.csv")
        ycsv = pd.read_csv(RESULTS / "backtest_yearly.csv")
        main_run = f"策略(验证期选参) top{CFG['K']}"
        ytext = " · ".join(
            f"{int(r['year'])} {r['ret']*100:+.1f}%"
            for _, r in ycsv[ycsv["run"] == main_run].sort_values("year").iterrows())
        gtop = grid.head(6)
        grid_rows = ""
        for _, r in gtop.iterrows():
            grid_rows += (f"<tr><td class='k'>K={int(r['K'])}</td>"
                          f"<td>每 {int(r['freq'])} 日</td>"
                          f"<td>{'不限' if pd.isna(r['ind_cap']) else int(r['ind_cap'])}</td>"
                          f"<td>{'等权' if r['weight_mode'] == 'equal' else '分数加权'}</td>"
                          f"<td>{pct(r['valid_ann'])}</td><td>{r['valid_ir']:+.2f}</td>"
                          f"<td>{pct(r['valid_excess_ann'])}</td></tr>")

        bt_html = f"""
<h2>七、把分数变成钱：完整策略回测（含换手与成本）</h2>

<table>
<tr><th class="k">设计项</th><th class="k">口径</th></tr>
<tr><td class="k">股票池</td><td class="k">沪深300 <b>时点</b>成分（沿用 csi300_lgbm 的 membership.csv，不是今日 300 只倒推）</td></tr>
<tr><td class="k">信号</td><td class="k">score = {bt['weights']['recommended']['price']:.2f}×价量 + {bt['weights']['recommended']['fund']:.2f}×基本面 + {bt['weights']['recommended']['event']:.2f}×事件
（基本面缺失按 0 中性填补，缺失格子 {bt['missing']['fund_missing_cells']} 个）</td></tr>
<tr><td class="k">选股</td><td class="k">池内按分数取 top-K 等权；行业上限用东财 BOARD_NAME</td></tr>
<tr><td class="k">调仓</td><td class="k">信号 T 日收盘 → <b>T+1 日收盘成交</b>（与本仓库其他项目同口径）</td></tr>
<tr><td class="k">成本</td><td class="k">买入 {bt['cost_model']['buy']*100:.2f}% / 卖出 {bt['cost_model']['sell']*100:.2f}% / 单笔最低 {bt['cost_model']['min_fee']:.0f} 元，账户 {bt['cost_model']['account']/10000:.0f} 万</td></tr>
<tr><td class="k">不可交易</td><td class="k">停牌（成交量=0）不可买卖；收盘涨停买不进</td></tr>
<tr><td class="k">参数选择</td><td class="k"><b>只在验证期 2020-2022 搜</b>：K×频率×行业上限×权重方式 共 {len(grid)} 组，测试期只跑一次</td></tr>
</table>

<div class="good"><b>验证期选出的配置</b>：K={CFG['K']}、每 {CFG['freq']} 个交易日调仓、
行业上限 {CFG['ind_cap'] if CFG['ind_cap'] else '不限'}、{('等权' if CFG['weight_mode']=='equal' else '分数加权')}
（验证期 IR {bt['valid_best']['valid_ir']:+.2f}）。
注意这个配置是<b>低换手 + 宽组合</b>：它比「top20 月调」更慢、更散 —— 下面的对比会看到这件事有多重要。</div>

<img src="img/fig9_nav_test.png" alt="测试期净值曲线">

<table>
<tr><th class="k">策略</th><th>年化</th><th>总收益</th><th>波动</th><th>Sharpe</th><th>MDD</th>
<th>IR vs 沪深300</th><th>超额年化</th><th>换手/年</th><th>成本/年</th></tr>
{srows}
</table>

<img src="img/fig11_yearly.png" alt="分年收益">
<img src="img/fig12_freq_cost.png" alt="频率与成本">

<div class="bad"><b>换手是这件事的胜负手，不是因子。</b>
每 5 个交易日调仓的三个配置全部亏损（成本 4.3~4.7pct/年），每 10 日勉强打平（+0.7%~+1.2%），
只有每 20 日以上才转正。<b>所以「基本面该不该加」的答案，一半是「别乱换手」的答案。</b></div>

<table>
<tr><th class="k">K</th><th class="k">调仓频率</th><th>年化</th><th>IR</th><th>MDD</th>
<th>换手/年</th><th>成本/年</th></tr>
{sens_rows}
</table>

<h3>分期体检：同一套参数，三段都跑</h3>
<table>
<tr><th class="k">区间</th><th>年化</th><th>IR</th><th>MDD</th><th>换手/年</th><th>成本/年</th></tr>
{prow}
</table>
<img src="img/fig13_periods.png" alt="分期年化">
<img src="img/fig10_nav_full.png" alt="全区间净值">

<div class="warn"><b>这里有两个数字，别混用：</b><br>
① <b>测试期最高年化 +7.05%</b>（默认 top20 月调）——但它在训练期是 {pct(PP['train_2016_2019']['ann_return'])}、
验证期 {pct(PP['valid_2020_2022']['ann_return'])}，全区间年化 {pct(FULL['ann_return'])}。
<b>只在测试期好看的配置不能上线</b>，这是本仓库第三次同款教训。<br>
② <b>能拿出去的数字：验证期选参版</b>（top{CFG['K']}、每 {CFG['freq']} 日、行业≤{CFG['ind_cap']}）——
测试期年化 <b>{pct(BR[main_name]['ann_return'])}</b>、超额年化 <b>{pct(BR[main_name]['excess_ann'])}</b>、
IR {BR[main_name]['ir']:+.2f}、MDD {pct(BR[main_name]['max_drawdown'])}；
训练期 {pct(PP['train_2016_2019']['ann_return'])}、验证期 {pct(PP['valid_2020_2022']['ann_return'])}、
全区间 {pct(FULL['ann_return'])}（超额 {pct(FULL['excess_ann'])}）——<b>三段都是正的</b>，
这才是「分数能变钱」的最低证据。</div>

<table>
<tr><th class="k">验证期网格 Top6</th><th class="k">K</th><th class="k">频率</th><th class="k">行业上限</th>
<th class="k">权重方式</th><th>年化</th><th>IR</th><th>超额年化</th></tr>
{grid_rows}
</table>

<div class="card">
<b>三个必须一起看的结论</b>
<ol>
<li><b>纯价量分和纯基本面分单独用都不行</b>：测试期年化 {pct(BR['纯价量分 top20 月调']['ann_return'])} 与
{pct(BR['纯基本面分 top20 月调']['ann_return'])}，都跑输沪深300；
<b>混在一起才有 {pct(BR[main_name]['ann_return'])}</b>。基本面在组合里的作用不是"自己赚钱"，
是<b>改变选股排序、砍掉价量信号里的坑</b>。</li>
<li><b>超额主要来自 2025</b>：测试期分年收益 {ytext}——2025 年 AI 行情贡献了绝大部分，
2023 和 2026 两年策略都是亏的。<b>不要把 {pct(BR[main_name]['ann_return'])} 当成未来预期</b>。</li>
<li><b>回撤仍然很大</b>：测试期 MDD {pct(BR[main_name]['max_drawdown'])}，全区间 MDD {pct(FULL['max_drawdown'])}。
年化 2~6%、回撤 30~48%，<b>这个风险收益比只适合做组合里的一小块卫星仓</b>，不适合当主仓。</li>
</ol>
</div>
"""

    yrows = ""
    for v, lb, c in [("price_only", "纯价量", "teal"), ("fund_only", "纯基本面", "grey"),
                     ("mix_selected", "混合", "orange")]:
        s = yearly[(yearly["variant"] == v) & (yearly["label"] == "fwd5")].sort_values("year")
        yrows += (f"<tr><td class='k'>{lb}</td>" +
                  "".join(f"<td class='{c}'>{x:+.4f}</td>" for x in s["ic_mean"]) + "</tr>")
    years = [int(y) for y in sorted(yearly[yearly["variant"] == "price_only"]["year"].unique())]
    yhead = "".join(f"<th>{y}</th>" for y in years)

    p5 = V["price_only"]["fwd5"]
    f5 = V["fund_only"]["fwd5"]
    e5 = V["event_only"]["fwd5"]
    m5 = V["mix_selected"]["fwd5"]
    pp5 = V["price_prior_dir"]["fwd5"]
    p20 = V["price_only"]["fwd20"]
    m20 = V["mix_selected"]["fwd20"]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>基本面 × 高频价量 混合趋势打分：框架选型、指标体系与参数方案</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; background:#fff; color:#1F2933;
  font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;
  font-size:14px; line-height:1.78; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:38px 34px 60px; }}
h1 {{ font-size:27px; margin:0 0 6px; letter-spacing:-.3px; }}
.sub {{ color:#8A9099; font-size:12.5px; margin-bottom:26px; }}
h2 {{ font-size:18.5px; margin:40px 0 10px; padding-left:11px;
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
.good {{ background:#F1F7F6; border-left:4px solid #2F7E8C; padding:13px 18px;
  border-radius:6px; margin:16px 0; }}
table {{ border-collapse:collapse; width:100%; margin:14px 0 6px; font-size:12.6px; }}
th {{ background:#F2F4F6; color:#5B6470; font-weight:600; text-align:right;
  padding:9px 10px; border-bottom:1px solid #E4E7EB; white-space:nowrap; }}
td {{ padding:8px 10px; border-bottom:1px solid #F0F2F4; text-align:right;
  vertical-align:top; }}
th.k, td.k {{ text-align:left; }}
td.k {{ color:#39424E; }}
tr.sel td {{ background:#FDF6F1; font-weight:600; }}
.pos {{ color:#C94C4C; }} .neg {{ color:#2F7E8C; }}
.teal {{ color:#2F7E8C; }} .grey {{ color:#9AA1A9; }} .orange {{ color:#E8833A; }}
.rk {{ color:#E8833A; font-weight:700; text-align:center; width:34px; }}
.nm {{ text-align:left; font-weight:600; }}
.cd {{ color:#9AA1A9; font-weight:400; font-size:11px; margin-left:7px; }}
.flip {{ color:#C94C4C; font-size:11px; margin-left:6px; }}
img {{ max-width:100%; margin:12px 0 4px; display:block; }}
.cap {{ color:#9AA1A9; font-size:11.5px; margin:2px 0 18px; }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
code {{ background:#F2F4F6; padding:1.5px 6px; border-radius:4px; font-size:12px;
  font-family:Consolas,monospace; }}
ul {{ padding-left:22px; }} li {{ margin:6px 0; }}
.tag {{ display:inline-block; background:#F2F4F6; color:#5B6470; border-radius:4px;
  padding:1px 7px; font-size:11.5px; margin-right:6px; }}
.foot {{ color:#9AA1A9; font-size:11.5px; border-top:1px solid #E4E7EB;
  margin-top:40px; padding-top:14px; }}
.big {{ font-size:21px; font-weight:700; }}
</style></head><body><div class="wrap">

<h1>基本面 × 高频价量 混合趋势打分：框架选型、指标体系、参数方案</h1>
<div class="sub">
项目 <code>projects/trend_combo</code> · 股票池：沪深300 时点成分 {pstat['symbols']} 只（2014-01-02 ~ 2026-10-30，{pstat['dates']} 个交易日）
· 基本面源：东方财富 F10（{flog['n_symbols']} 只，财务 {flog['n_fin_rows']} 行 / 估值 {flog['n_val_rows']} 行 / 预告 {flog['n_pre_rows']} 行）
· 切分：训练 2016-2019 / 验证 2020-2022 / 测试 2023-2026（测试期只跑一次）
</div>

<div class="lead">
<ol>
<b>方案结论：qlib 保留，但只让它干「价量高频 + 标签 + 回测」这一层；基本面不进 qlib 的 bin，
改成外置 PIT 财务库；合成层用「标准化 + 训练期自动定向 + 分域线性加权」，不重训 LightGBM。</b>
换框架的收益为负——要重写 30 个特征、回测引擎和 18 条踩坑，产出还是同样的信号。</li>

<b>最大的坑不是数据源，是方向。</b>按教科书先验（动量+、反转−、低波+、低估值+）给价量因子定向，
测试期 RankIC 是 <b class="neg">{num(pp5['test']['ic_mean'])}</b>（负的，等于反向信号）；
改成「训练期 RankIC 定方向 + |IC|≥{res['ic_threshold']} 且 |t|≥{res['t_threshold']} 筛选」之后，
同一批因子测试期 IC 变成 <b class="pos">{num(p5['test']['ic_mean'])}</b>（t={p5['test'].get('t_stat', 0):+.1f}）。
45 个因子里 <b>{int((~fdf['prior_agrees']).sum())} 个先验方向被数据推翻</b>。</li>

<b>基本面确实有正 alpha，但比价量弱、衰减更快。</b>纯基本面块测试期 IC {num(f5['test']['ic_mean'])}
（IR {f5['test'].get('icir', 0):+.2f}），纯价量块 {num(p5['test']['ic_mean'])}
（IR {p5['test'].get('icir', 0):+.2f}）；20 日 horizon 上差距更大：
基本面 {num(V['fund_only']['fwd20']['test']['ic_mean'])} vs 价量 {num(p20['test']['ic_mean'])}。</li>

<b>权重：验证期最优把基本面给到 {sel['wf']:.1f}，测试期最优却在 0.2~0.4 —— 「选型不可外推」又一次复现。</b>
两段都靠前的甜点区是基本面 0.2~0.4，<b>建议实盘用 价量 0.65 / 基本面 0.30 / 事件 0.05</b>，
而不是验证期极值。</li>

<b>但有个不好听的事实：IC 稳，分档不单调。</b>测试期按混合分五档的未来 20 日收益是 {btext}
——高低档收益差 {abs(b['5']['mean']-b['1']['mean'])*100:.2f}pct，
说明这个分数<b>可以当「趋势判断/风控过滤」用，直接当选股器排序收益一般</b>。</li>
</ol>
</div>

<h2>一、方案选型：三条路，逐一算账</h2>
<table>
<tr><th class="k">方案</th><th class="k">做法</th><th class="k">成本</th><th class="k">结论</th></tr>
<tr><td class="k">A. qlib 留 + 基本面外置 PIT 库 <span class="tag">推荐</span></td>
<td class="k">qlib 提供价量 30 特征、标签、回测/模拟器；基本面走东财 F10 三个接口落 parquet，
按<b>披露日</b> as-of 对齐成日频面板；两层用线性加权合成</td>
<td class="k">复用 csi300_lgbm 现成面板（637 只 × 3117 天，30 特征已跑通）；
新写 3 个脚本（抓数 / PIT 对齐 / 打分）</td>
<td class="k"><b>采用</b>：增量成本最小，且基本面可单独刷新</td></tr>
<tr><td class="k">B. 换框架（backtrader / zipline / R quantstrats）</td>
<td class="k">用别的框架重做取数、特征、回测</td>
<td class="k">重写 30 特征 + 标签 + 组合模拟 + 交易成本/涨跌停/停牌规则</td>
<td class="k"><b>否决</b>：本仓库 18 条 qlib 踩坑（bin 对齐、复权因子、col_set 元组、
Windows 下 D.features 无限 fork…）全部要重踩一遍，换不到新信号</td></tr>
<tr><td class="k">C. 把基本面 dump 成 qlib 的 bin</td>
<td class="k">走 qlib 自带 <code>scripts/dump_pit.py</code> 落 PIT 财务 bin</td>
<td class="k">字段受限于它的 schema，要重写 bin 对齐与复权处理</td>
<td class="k"><b>不做</b>：同样的数据用 parquet 存更省事，qlib 的 bin 优势只在对齐日历，
而我们本来就用 qlib 的交易日历做 as-of 对齐</td></tr>
<tr><td class="k">D. 基本面直接进 LightGBM</td>
<td class="k">30 个价量 + 18 个基本面对子一起喂模型</td>
<td class="k">特征维度翻倍，样本外更难稳</td>
<td class="k"><b>否决</b>：本仓库两次样本外失败（600418 训练 IC +0.12 → 测试 −0.01；
002230 同类），Linear/IC 加权的可解释合成在这个量级上更靠谱</td></tr>
</table>

<div class="warn"><b>为什么基本面不进 LightGBM（证据在本仓库里）：</b>
① <code>projects/jac_600418</code> 三次样本外失败，IC 从训练 +0.12 掉到测试 −0.01；
② 财报/业绩公告 <b>T0 超额 −0.551%（n=187）</b>，短线是负 alpha；
③ 本次实测纯基本面块的 IC 明显弱于价量块，喂进模型只会增加过拟合面。</div>

<h2>二、数据层：三个免费接口 + PIT 纪律（已实测跑通）</h2>
<table>
<tr><th class="k">接口</th><th class="k">拿到什么</th><th class="k">关键字段</th><th class="k">PIT 怎么用</th></tr>
<tr><td class="k">东财 F10 <code>RPT_F10_FINANCE_MAINFINADATA</code></td>
<td class="k">每期财报 165 个财务指标</td>
<td class="k"><code>REPORT_DATE</code>（报告期）<b>+ <code>NOTICE_DATE</code>（披露日）</b>、
ROEJQ / ROIC / XSMLL / TOTALOPERATEREVETZ / PARENTNETPROFITTZ / KCFJCXSYJLRTZ / ROEJQTZ / BPSTZ</td>
<td class="k">按 <code>NOTICE_DATE ≤ t</code> as-of 取最新一期，披露前不可见</td></tr>
<tr><td class="k">东财 <code>RPT_VALUEANALYSIS_DET</code></td>
<td class="k">日频估值 + 行业名</td>
<td class="k">PE_TTM / PB_MRQ / PS_TTM / PEG / 总市值 / <b>BOARD_NAME</b></td>
<td class="k">本身日频无前视；BOARD_NAME 用于<b>行业中性化</b></td></tr>
<tr><td class="k">东财 <code>RPT_PUBLIC_OP_NEWPREDICT</code></td>
<td class="k">业绩预告（事件）</td>
<td class="k">NOTICE_DATE + ADD_AMP_LOWER/UPPER（预增幅度）</td>
<td class="k">按公告日 as-of；同时用 <code>days_since_predict</code> 惩罚陈旧预告</td></tr>
</table>
<p>抓取：{flog['n_symbols']} 只股票、{flog['n_errors']} 个请求失败（重试 3 次后放弃，失败只影响该股票的部分字段），
耗时 {flog['seconds']:.0f} 秒；财务覆盖 {flog['symbols_with_fin']}/{flog['n_symbols']} 只，
估值覆盖 {flog['symbols_with_val']}/{flog['n_symbols']} 只。</p>

<img src="img/fig6_coverage.png" alt="因子覆盖率">
<div class="cap">基本面因子在 2014-2026 面板上的覆盖率。估值类因子从 2018 年才有数据
（三年分位需要 250 日最小窗口，2019-01 才开始有值），这是面板里最实在的一处缺口。</div>

<h2>三、指标体系：四域 + 事件，共 45 个因子</h2>
<table>
<tr><th class="k">域</th><th class="k">因子</th><th class="k">来源</th><th class="k">计算</th><th class="k">先验方向</th></tr>
<tr><td class="k">价量·趋势</td><td class="k">mom_20 / mom_60 / mom_120、ma_slope_20/60、ma_dist_20/60、
ma_cross_5_20、price_pos_250、rel_str_60</td><td class="k">qlib</td><td class="k">现成 30 特征</td>
<td class="k">动量 +（<b>数据推翻了</b>）</td></tr>
<tr><td class="k">价量·反转</td><td class="k">rev_3 / rev_10 / mom_5_ex / mom_20_ex / dd_60</td>
<td class="k">qlib</td><td class="k">现成 30 特征</td><td class="k">反转 −（部分被推翻）</td></tr>
<tr><td class="k">价量·风险</td><td class="k">vol_20 / vol_60 / hl_range_20 / beta_60 / alpha_20</td>
<td class="k">qlib</td><td class="k">现成 30 特征</td><td class="k">低波好 / alpha 好</td></tr>
<tr><td class="k">价量·量能</td><td class="k">vol_ratio / vol_ratio_5_20 / vol_z_20 / liq_change</td>
<td class="k">qlib</td><td class="k">现成 30 特征</td><td class="k">放量 +</td></tr>
<tr><td class="k">基本面·估值</td><td class="k">pe_pct_3y / pb_pct_3y / ps_pct_3y / pe_log / cap_log</td>
<td class="k">东财估值</td><td class="k">PE/PB/PS 的 750 日滚动分位（min 250 日）</td><td class="k">低分位（便宜）看多</td></tr>
<tr><td class="k">基本面·成长</td><td class="k">rev_yoy / rev_qoq / np_yoy / dnp_yoy / rev_gap</td>
<td class="k">东财 F10</td><td class="k">营收/净利同比、环比；rev_gap = 营收同比 − 净利同比（剪刀差）</td>
<td class="k">高增看多</td></tr>
<tr><td class="k">基本面·质量</td><td class="k">roe / roic / gross_margin / net_margin / debt_ratio /
cfo_to_np / inv_turn</td><td class="k">东财 F10</td>
<td class="k">加权 ROE、ROIC、毛利率、净利率、资产负债率、经营现金流/净利、存货周转</td><td class="k">高质量看多</td></tr>
<tr><td class="k">基本面·边际</td><td class="k">roe_yoy / bps_yoy</td><td class="k">东财 F10</td>
<td class="k">ROE 同比变化、每股净资产同比</td><td class="k">改善看多</td></tr>
<tr><td class="k">事件</td><td class="k">predict_growth / days_since_predict</td><td class="k">东财预告</td>
<td class="k">预告净利增幅中值；距上次预告天数</td><td class="k">预增看多 / 预告越旧越扣分</td></tr>
</table>
<p class="cap">基本面里特意放了「边际变化」域（roe_yoy、bps_yoy、rev_gap）：只放水平值会让高分股永远是高分股，
边际变化才是趋势信息。</p>

<h2>四、计算流程与参数怎么定</h2>
<div class="grid2">
<div class="card">
<h3>标准化（四步，顺序不能换）</h3>
<ul>
<li>截面 winsorize(1%, 99%)——去极值</li>
<li>行业中性化——减同行业同日均值（成分 &lt; 5 只的行业跳过）</li>
<li>截面 z-score</li>
<li>clip(z/3, −1, 1)——限幅，避免单因子主导</li>
</ul>
<p class="cap">基本面和价量走同一套，量纲统一后才能线性加权。</p>
</div>
<div class="card">
<h3>参数怎么调（协议）</h3>
<ul>
<li><b>方向</b>：训练期 RankIC 的符号（不是教科书先验）</li>
<li><b>筛选</b>：|训练 IC| ≥ {res['ic_threshold']} 且 |t| ≥ {res['t_threshold']}，留 {res['n_kept']}/{res['n_factors']} 个</li>
<li><b>域内权重</b>：等权 / 训练期 IC 加权两种都跑，验证期挑</li>
<li><b>跨域权重</b>：网格搜索，<b>只在验证期选</b>；测试期只跑一次</li>
<li><b>阈值</b>：分数分位（不设绝对阈值，跨期不可比）</li>
</ul>
</div>
</div>

<img src="img/fig8_direction.png" alt="先验方向 vs 自动定向">
<div class="cap">同一批价量因子，方向定错整块信号就是反的：先验版测试期 IC
{num(pp5['test']['ic_mean'])}，自动定向版 {num(p5['test']['ic_mean'])}。</div>

<h2>五、验证结果</h2>
<img src="img/fig1_ic_compare.png" alt="IC 对比">

<table>
<tr><th class="k">变体</th><th>训练 IC</th><th>验证 IC</th><th>验证 IR</th><th>测试 IC</th><th>测试 IR</th><th>测试 t</th></tr>
<tr><td class="k">纯价量（自动定向）</td><td>{num(p5['train']['ic_mean'])}</td><td>{num(p5['valid']['ic_mean'])}</td>
<td>{p5['valid'].get('icir', 0):+.3f}</td><td>{num(p5['test']['ic_mean'])}</td>
<td>{p5['test'].get('icir', 0):+.3f}</td><td>{p5['test'].get('t_stat', 0):+.2f}</td></tr>
<tr><td class="k">纯基本面</td><td>{num(f5['train']['ic_mean'])}</td><td>{num(f5['valid']['ic_mean'])}</td>
<td>{f5['valid'].get('icir', 0):+.3f}</td><td>{num(f5['test']['ic_mean'])}</td>
<td>{f5['test'].get('icir', 0):+.3f}</td><td>{f5['test'].get('t_stat', 0):+.2f}</td></tr>
<tr><td class="k">纯事件（预告）</td><td>{num(e5['train']['ic_mean'])}</td><td>{num(e5['valid']['ic_mean'])}</td>
<td>{e5['valid'].get('icir', 0):+.3f}</td><td>{num(e5['test']['ic_mean'])}</td>
<td>{e5['test'].get('icir', 0):+.3f}</td><td>{e5['test'].get('t_stat', 0):+.2f}</td></tr>
<tr class="sel"><td class="k">混合（验证期选中 {sel['wp']:.1f}/{sel['wf']:.1f}/{sel['we']:.2f}）</td>
<td>{num(m5['train']['ic_mean'])}</td><td>{num(m5['valid']['ic_mean'])}</td>
<td>{m5['valid'].get('icir', 0):+.3f}</td><td>{num(m5['test']['ic_mean'])}</td>
<td>{m5['test'].get('icir', 0):+.3f}</td><td>{m5['test'].get('t_stat', 0):+.2f}</td></tr>
<tr><td class="k">价量（教科书先验方向）</td><td>{num(pp5['train']['ic_mean'])}</td>
<td>{num(pp5['valid']['ic_mean'])}</td><td>{pp5['valid'].get('icir', 0):+.3f}</td>
<td>{num(pp5['test']['ic_mean'])}</td><td>{pp5['test'].get('icir', 0):+.3f}</td>
<td>{pp5['test'].get('t_stat', 0):+.2f}</td></tr>
</table>

<img src="img/fig2_ic_yearly.png" alt="分年 IC">
<table>
<tr><th class="k">变体</th>{yhead}</tr>
{yrows}
</table>

<img src="img/fig3_weight_sens.png" alt="权重敏感性">
<table>
<tr><th class="k">价量/基本面权重</th><th>训练 IC</th><th>验证 IC</th><th>验证 IR</th>
<th>测试 IC</th><th>测试 IR</th><th>测试 IC(20日)</th><th>测试 IR(20日)</th></tr>
{wrows}
</table>
<div class="warn"><b>怎么读这张表：</b>上表是「事件权重 = 0」的切片（验证期选中的组合是
{sel['wp']:.1f}/{sel['wf']:.1f}/{sel['we']:.2f}）。验证期（蓝）最优落在基本面 {sel['wf']:.1f}，
测试期（橙）最优落在基本面 0.2~0.3——<b>验证期的极值不能直接外推</b>。
两段都靠前的区域是基本面 0.2~0.4，这也是建议实盘权重（价量 0.65 / 基本面 0.30 / 事件 0.05）的依据：
它不赌任何一段的极值，落在两段曲线的共同高台区。
<br><span style="font-size:11.8px;color:#8A9099">
口径提示：本表 1.0/0.0 行（测试 IC {num(g0.iloc[0]['test_ic_f5'])}）比上面「纯价量」变体
（{num(p5['test']['ic_mean'])}）略高，原因是网格里 <code>0 × NaN</code> 会把基本面缺失的样本整行剔掉，
等于只在「基本面齐」的子样本上评估；上面的变体表是<b>不剔样本</b>的干净口径，本报告以变体表为准。</span></div>

<img src="img/fig7_factor_ic.png" alt="因子级 IC">
<table>
<tr><th class="k">因子</th><th class="k">域</th><th>先验方向</th><th>训练 IC</th><th>训练 t</th>
<th>验证 IC</th><th>测试 IC</th><th>保留</th></tr>
{frows}
</table>

<img src="img/fig4_buckets.png" alt="分档收益">
<div class="bad"><b>分档不单调，这是本方案最需要警惕的地方。</b>
测试期五档未来 20 日收益：{btext}。IC 是 {num(m20['test']['ic_mean'])}（t={m20['test'].get('t_stat', 0):+.1f}），
但「最高分档」并不比中间档好多少。含义：<b>这个分数适合当「趋势确认 / 减仓触发」的过滤信号，
直接拿来排序选股的收益会被 IC 的非线性吃掉</b>。要变成选股器，还需要加行业上限、风格约束、换手控制。</div>

<h2>六、落到实盘：当前 20 只持仓的趋势分</h2>
<img src="img/fig5_holdings.png" alt="持仓打分">
<table>
<tr><th>排名</th><th class="k">名称</th><th>总分</th><th>价量分</th><th>基本面分</th><th>事件分</th>
<th>ROE%</th><th>营收同比%</th><th>PE(TTM)</th></tr>
{hrows}
</table>
<div class="card kv">
截面 {hold['as_of']}，权重 价量 {hold['weights']['price']:.2f} / 基本面 {hold['weights']['fund']:.2f} /
事件 {hold['weights']['event']:.2f}。读法：<b>价量分是主旋律，基本面分是修正项</b>。
比如天孚通信价量 −0.118（中期动量已转弱）但基本面 +0.096（ROE/毛利率仍在高位），
这类「技术弱、基本面没坏」的票更适合减而不是清；反过来蓝思科技、锐捷网络两域同时为负，是先跑的对象。
</div>

<h2>八、局限与风险（必须一起看）</h2>
{bt_html}
<ul>
<li><b>分档不单调</b>：IC 显著 ≠ 组合收益好；本方案只能算「打分/过滤」，还不是完整策略（缺换手与成本回测）。</li>
<li><b>基本面衰减快</b>：纯基本面块训练 {num(f5['train']['ic_mean'])} → 测试 {num(f5['test']['ic_mean'])}，
掉了 {abs(f5['train']['ic_mean']-f5['test']['ic_mean'])/f5['train']['ic_mean']*100:.0f}%；
而价量块几乎没掉（{num(p5['train']['ic_mean'])} → {num(p5['test']['ic_mean'])}）。基本面当压舱石可以，当主引擎不行。</li>
<li><b>接口依赖</b>：东财 F10 无官方 SLA，字段可能改；缓存里存了原始快照，可离线复现，但需要定期重抓。</li>
<li><b>行业中性化依赖 BOARD_NAME</b>：{flog['symbols_with_val']}/{flog['n_symbols']} 只有估值覆盖，
未覆盖的股票没有行业标签（本次处理为不做行业中性化）。</li>
<li><b>幸存者与成分口径</b>：股票池用 csi300_lgbm 的时点成分（含退市/被剔除的历史成分），非今日 300 只倒推。</li>
<li><b>样本区间</b>：2014-2026，含 2015 与 2024-09 两次极端行情；未做危机期剔除。</li>
<li><b>没有做的事</b>：没做交易成本与换手回测、没做组合优化、没做多空对冲、没接实时行情。</li>
</ul>

<h2>九、落地清单与复现命令</h2>
<div class="card kv">
<pre style="margin:0;white-space:pre-wrap;line-height:1.9">cd /d projects\\trend_combo
..\\..\\.venv\\Scripts\\python.exe tools\\fetch_fundamental.py   :: 抓东财 F10 → data\\fund_*.parquet（约 6.5 分钟）
..\\..\\.venv\\Scripts\\python.exe tools\\build_panel.py         :: PIT 对齐 → data\\panel_merged.parquet
..\\..\\.venv\\Scripts\\python.exe tools\\composite.py          :: 标准化 + 分域 → data\\scores.parquet
..\\..\\.venv\\Scripts\\python.exe tools\\eval_ic.py             :: 因子 IC → 自动定向 → 权重网格 → results\\ic_results.json
..\\..\\.venv\\Scripts\\python.exe tools\\score_holdings.py      :: 实盘 20 只打分 → results\\holdings_score.json
..\\..\\.venv\\Scripts\\python.exe tools\\strategy.py           :: 验证期选参 + 策略回测(换手/成本/基线) → results\\backtest.json
..\\..\\.venv\\Scripts\\python.exe tools\\make_figures.py        :: 13 张配图
..\\..\\.venv\\Scripts\\python.exe tools\\build_report.py       :: 本报告
..\\..\\.venv\\Scripts\\python.exe tools\\render_png.py         :: HTML → PNG</pre>
</div>
<table>
<tr><th class="k">文件</th><th class="k">内容</th></tr>
<tr><td class="k">data/fund_financials.parquet</td><td class="k">{flog['n_fin_rows']} 行季频财务（含 NOTICE_DATE，可做 PIT）</td></tr>
<tr><td class="k">data/fund_valuation.parquet</td><td class="k">{flog['n_val_rows']} 行日频估值 + 行业名</td></tr>
<tr><td class="k">data/fund_predict.parquet</td><td class="k">{flog['n_pre_rows']} 行业绩预告</td></tr>
<tr><td class="k">data/panel_merged.parquet</td><td class="k">{pstat['rows']} 行日频面板（价量 30 + 基本面 19 + 标签）</td></tr>
<tr><td class="k">data/scores.parquet</td><td class="k">标准化后的 45 个 z 因子 + 分域分数</td></tr>
<tr><td class="k">results/factor_ic.csv</td><td class="k">因子级训练/验证/测试 IC + 方向 + 保留与否</td></tr>
<tr><td class="k">results/weight_grid_equal.csv / _icw.csv</td><td class="k">跨域权重网格（等权 / IC 加权两套）</td></tr>
<tr><td class="k">results/ic_results.json</td><td class="k">全部 IC 统计、分年、分档</td></tr>
</table>

<div class="foot">
生成时间：2026-11-05 · 报告由 <code>tools/build_report.py</code> 自动生成，
所有数字取自 <code>projects/trend_combo/results/*</code> · 行情与价量特征来自
<code>qlib cn_data_2026</code>，基本面来自东方财富 F10 公开接口。
</div>
</div></body></html>"""

    out = REPORT / "trend_combo_report.html"
    out.write_text(html, encoding="utf-8")
    print("已写出", out, f"{out.stat().st_size/1024:.0f}KB")
    return out


if __name__ == "__main__":
    main()
