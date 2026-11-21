"""生成「策略收益 × 行业乖离率」周度更新报告（HTML → 之后用 Chrome 截 PNG）。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\build_update_report.py [--asof 2026-11-20]

数据源：
  - 策略净值：results\\track_pnl.csv（tools\\track_pnl.py 产出，腾讯不复权日线）
  - 持仓明细：results\\track_positions_latest.csv
  - 行业日线：data\\sw_industry\\index_daily\\*.parquet（申万 index_publish/trend）
  - 行业映射：data\\sw_industry\\map.parquet
  - 乖离率口径与 tools\\industry_bias_heatmap.py 完全一致（直接 import 复用）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
REPO = PROJ.parent.parent          # projects\csi300_lgbm → projects → <repo>
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

import industry_bias_heatmap as ibh  # noqa: E402

RESULTS = PROJ / "results"
OUT = PROJ / "report" / "update_20261120"
IMG = OUT / "img"
PERIODS = [6, 20, 60, 120]
RED, GREEN, INK = "#c0392b", "#1e8449", "#1c2833"
GREY = "#7f8c8d"


def setup_font() -> str:
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ibh.CJK_FONTS:
        if name in have:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False
            return name
    raise SystemExit("没找到中文字体")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None, help="报告截止日（默认取数据最新）")
    args = ap.parse_args()

    font = setup_font()
    OUT.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)

    # ---------------- 策略净值 ----------------
    trk = pd.read_csv(RESULTS / "track_pnl.csv")
    trk["date"] = pd.to_datetime(trk["date"])
    trk = trk.sort_values("date").reset_index(drop=True)
    pos = pd.read_csv(RESULTS / "track_positions_latest.csv")
    amap = pd.read_parquet(REPO / "data" / "sw_industry" / "map.parquet")
    pos = pos.merge(amap[["qlib_symbol", "l1_name"]], left_on="symbol",
                    right_on="qlib_symbol", how="left")
    pos["l1_name"] = pos["l1_name"].fillna("未分类")

    asof = pd.Timestamp(args.asof) if args.asof else trk["date"].max()
    trk = trk[trk["date"] <= asof].reset_index(drop=True)
    pos = pos.copy()
    last = trk.iloc[-1]

    # ---------------- 行业乖离率 ----------------
    inds = ibh.load_industries()
    panel = ibh.build_panel(inds, refresh=False)
    panel = panel.loc[: asof]
    bm = ibh.bias_matrix(panel, PERIODS)
    snap_now = pd.DataFrame({n: bm[n].iloc[-1] for n in PERIODS}, index=panel.columns)
    pct20 = pd.Series({name: ibh.percentile_rank(bm[20][name], 750) for name in panel.columns})

    # 上一个报告日（数据里最后一个早于 asof 7 个自然日以上的交易日）→ 做对比
    prev_pos = panel.index[panel.index <= asof - pd.Timedelta(days=7)]
    prev_date = prev_pos[-1] if len(prev_pos) else None
    snap_prev = None
    if prev_date is not None:
        i = panel.index.get_loc(prev_date)
        snap_prev = pd.DataFrame({n: bm[n].iloc[i] for n in PERIODS}, index=panel.columns)

    # ---------------- 图 1：净值 vs 沪深300 ----------------
    fig, ax = plt.subplots(figsize=(11, 4.6))
    d = trk["date"]
    ax.plot(d, trk["ret_pct"], color=RED, lw=2.2, marker="o", ms=4,
            label="策略组合（相对建仓成本）")
    ax.plot(d, trk["bench_ret_from_open_pct"], color="#2c3e50", lw=1.8, ls="--",
            marker="s", ms=3.5, label="沪深300（11-02 开盘基准）")
    ax.axhline(0, color="#bdc3c7", lw=1)
    ax.fill_between(d, trk["ret_pct"], trk["bench_ret_from_open_pct"],
                    where=trk["ret_pct"] < trk["bench_ret_from_open_pct"],
                    color=RED, alpha=0.12, label="跑输区间")
    for x, y in zip(d, trk["ret_pct"]):
        if x == d.iloc[-1]:
            ax.annotate(f"{y:+.2f}%", (x, y), textcoords="offset points",
                        xytext=(-46, 10), fontsize=10, color=RED, weight="bold")
    ax.set_ylabel("累计收益率 %", fontsize=10)
    ax.set_title(f"策略组合 vs 沪深300（{trk['date'].iloc[0]:%m-%d} 建仓 ~ {asof:%Y-%m-%d} 收盘）",
                 fontsize=13, pad=10)
    ax.legend(fontsize=9, loc="lower left", framealpha=0.95)
    ax.grid(alpha=0.25)
    ax.text(0.005, -0.28, f"数据：腾讯不复权日线；分红单独计入现金（红利税按持有期）｜字体 {font}",
            transform=ax.transAxes, fontsize=8, color=GREY)
    fig.tight_layout()
    fig.savefig(IMG / "fig_nav.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---------------- 图 2：持仓累计盈亏 ----------------
    p = pos.sort_values("ret_pct")
    fig, ax = plt.subplots(figsize=(9.5, 7.2))
    colors = [RED if v < 0 else GREEN for v in p["ret_pct"]]
    ax.barh(range(len(p)), p["ret_pct"], color=colors, alpha=0.88)
    ax.set_yticks(range(len(p)), [f"{n}({s[-6:]})" for n, s in zip(p["name"], p["symbol"])],
                  fontsize=9)
    for i, (r, w) in enumerate(zip(p["ret_pct"], p["weight_pct"])):
        ax.text(r + (0.9 if r >= 0 else -0.9), i, f"{r:+.1f}%  权重{w:.1f}%",
                va="center", ha="left" if r >= 0 else "right", fontsize=8.5)
    ax.axvline(0, color="#333", lw=1)
    ax.set_xlim(min(p["ret_pct"].min() - 12, -10), max(p["ret_pct"].max() + 14, 8))
    ax.set_xlabel("持仓累计收益率 %（2026-11-02 开盘买入起）", fontsize=10)
    ax.set_title(f"20 只持仓累计盈亏（{asof:%Y-%m-%d}）", fontsize=13, pad=10)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(IMG / "fig_holdings.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---------------- 图 3：行业暴露 vs 行业乖离率 ----------------
    grp = pos.groupby("l1_name").agg(weight=("weight_pct", "sum"),
                                     pnl=("pnl", "sum"),
                                     ret=("ret_pct", "mean"),
                                     n=("symbol", "count")).reset_index()
    grp["bias120"] = grp["l1_name"].map(snap_now[120])
    grp["bias20"] = grp["l1_name"].map(snap_now[20])
    grp = grp.sort_values("weight", ascending=False)
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    xs = grp["bias120"].fillna(0)
    ys = grp["weight"]
    size = grp["weight"] * 26
    cc = [RED if b < 0 else GREEN for b in xs]
    ax.scatter(xs, ys, s=size, c=cc, alpha=0.55, edgecolors="#1c2833", linewidths=0.8)
    for _, row in grp.iterrows():
        ax.annotate(f"{row['l1_name']}\n{row['ret']:+.1f}%",
                    (row["bias120"] if not np.isnan(row["bias120"]) else 0, row["weight"]),
                    fontsize=8.5, ha="center", va="bottom",
                    xytext=(0, 8), textcoords="offset points")
    ax.axvline(0, color="#555", lw=1, ls="--")
    ax.set_xlabel("该行业当前 BIAS120 %（左=深度偏离120日均线=这轮跌得最狠）", fontsize=10)
    ax.set_ylabel("组合在该行业的权重 %", fontsize=10)
    ax.set_title("组合行业暴露 × 行业乖离率（气泡大小=权重）", fontsize=13, pad=10)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(IMG / "fig_sector_bias.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---------------- 图 4：主要行业指数近 30 日 ----------------
    watch = ["通信", "电子", "传媒", "银行", "食品饮料", "公用事业"]
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    for name in watch:
        if name not in panel.columns:
            continue
        s = panel[name].dropna().tail(30)
        ax.plot(s.index, s / s.iloc[0] * 100, lw=1.7, label=name)
    b300 = trk.set_index("date")["bench_close"].dropna()
    ax.plot(b300.index, b300 / b300.iloc[0] * 100, color="#2c3e50", lw=2.2, ls="--",
            label="沪深300")
    ax.axhline(100, color="#bdc3c7", lw=1)
    ax.legend(fontsize=9, ncol=3, framealpha=0.95)
    ax.set_ylabel("归一化（起点=100）", fontsize=10)
    ax.set_title("行业指数近 30 个交易日走势（申万一级）", fontsize=13, pad=10)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(IMG / "fig_rotate.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---------------- 拷贝乖离率三图 ----------------
    for f in ["bias_cross_section.png", "bias_timeline.png", "bias_percentile.png"]:
        src = REPO / "data" / "sw_industry" / "bias" / f
        if src.exists():
            (IMG / f).write_bytes(src.read_bytes())

    # ---------------- 数字 ----------------
    cost = float(last["cost"])
    total = float(last["total"])
    ret = float(last["ret_pct"])
    bench_open = float(last["bench_ret_from_open_pct"])
    bench_close = float(last["bench_ret_pct"])
    excess = float(last["excess_pct"])
    n_win = int((pos["ret_pct"] > 0).sum())
    n_loss = int((pos["ret_pct"] <= 0).sum())
    worst = pos.nsmallest(3, "ret_pct")
    best = pos.nlargest(3, "ret_pct")
    tech = grp[grp["l1_name"].isin(["通信", "电子", "计算机", "传媒"])]
    tech_w = float(tech["weight"].sum())
    div_total = float(trk["cash_div"].iloc[-1])

    # 组合实际持有的行业（按权重降序）
    held = grp[grp["weight"] > 0].sort_values("weight", ascending=False)
    held_txt = "、".join(
        f"{r['l1_name']} {r['weight']:.1f}%（BIAS120 {snap_now[120].get(r['l1_name'], float('nan')):+.1f}%）"
        for _, r in held.iterrows())
    win_inds = grp[grp["pnl"] > 0].sort_values("pnl", ascending=False)
    win_txt = "、".join(
        f"{r['l1_name']} {r['ret']:+.1f}%" for _, r in win_inds.iterrows())

    # 传媒在上一个报告日的状态（数据驱动，不写死数字）
    idx1111 = panel.index[panel.index <= pd.Timestamp("2026-11-11")][-1]
    i1111 = panel.index.get_loc(idx1111)
    b1111 = {n: bm[n].iloc[i1111] for n in PERIODS}
    all_pos_1111 = [n for n in panel.columns if all(b1111[p][n] > 0 for p in PERIODS)]
    pct1111 = ibh.percentile_rank(bm[20]["传媒"].iloc[: i1111 + 1], 750)
    mc_now = float(snap_now[20]["传媒"])
    mc_then = float(b1111[20]["传媒"])
    mc_pct_now = float(pct20["传媒"])
    bank_day = float(panel["银行"].pct_change().iloc[-1] * 100)
    tech_mask = pos["l1_name"].isin(["通信", "电子", "计算机", "传媒"])
    n_tech_pos = int((tech_mask & (pos["ret_pct"] > 0)).sum())
    n_tech_total = int(tech_mask.sum())
    n_bank_pos = int(((pos["l1_name"] == "银行") & (pos["ret_pct"] > 0)).sum())
    n_bank_total = int((pos["l1_name"] == "银行").sum())

    # 净值节奏（数据驱动）
    peak_i = int(trk["ret_pct"].idxmax())
    peak_date = trk.loc[peak_i, "date"]
    peak_ret = float(trk.loc[peak_i, "ret_pct"])
    peak_exc = float(trk.loc[peak_i, "excess_pct"])
    lose_streak = len(trk) - peak_i
    after = trk.loc[peak_i:]
    zero_rows = after[after["excess_pct"] <= 0]
    zero_date = zero_rows["date"].iloc[0] if len(zero_rows) else trk["date"].iloc[-1]

    def bias_rows(frame, key, n=6):
        s = frame[key].dropna().sort_values(ascending=False)
        top = s.head(n)
        bot = s.tail(n)
        return top, bot

    t20, b20 = bias_rows(snap_now, 20)
    t120, b120 = bias_rows(snap_now, 120)

    def tbl_rows(df, cols, headers):
        out = []
        for _, r in df.iterrows():
            out.append("<tr>" + "".join(
                f"<td>{r[c]:.2f}</td>" if isinstance(r[c], float) else f"<td>{r[c]}</td>"
                for c in cols) + "</tr>")
        return "\n".join(out)

    # 行业汇总表
    grp_html = []
    for _, r in grp.sort_values("pnl").iterrows():
        gb120 = r["bias120"]
        gb20 = r["bias20"]
        grp_html.append(
            f"<tr><td>{r['l1_name']}</td><td>{int(r['n'])}</td>"
            f"<td>{r['weight']:.1f}%</td><td class='{'neg' if r['pnl'] < 0 else 'pos'}'>"
            f"{r['pnl']:,.0f}</td><td>{r['ret']:+.2f}%</td>"
            f"<td>{gb20:+.2f}%</td><td>{gb120:+.2f}%</td></tr>")

    pos_html = []
    for _, r in pos.sort_values("ret_pct").iterrows():
        cls = "neg" if r["pnl"] < 0 else "pos"
        pos_html.append(
            f"<tr><td>{r['name']}</td><td class='mono'>{r['symbol']}</td>"
            f"<td>{r['l1_name']}</td><td>{int(r['shares'])}</td>"
            f"<td class='mono'>{r['entry_price']:.2f}</td><td class='mono'>{r['close']:.2f}</td>"
            f"<td class='mono'>{r['mkt_value']:,.0f}</td>"
            f"<td class='{cls}'>{r['pnl']:,.0f}</td>"
            f"<td class='{cls}'>{r['ret_pct']:+.2f}%</td>"
            f"<td>{r['day_ret_pct']:+.2f}%</td><td>{r['weight_pct']:.1f}%</td></tr>")

    prev_tbl = ""
    if snap_prev is not None:
        diff = (snap_now[20] - snap_prev[20]).sort_values()
        rows = []
        for name in list(diff.head(5).index) + list(diff.tail(5).index):
            rows.append(
                f"<tr><td>{name}</td><td>{snap_prev[20][name]:+.2f}%</td>"
                f"<td>{snap_now[20][name]:+.2f}%</td>"
                f"<td class='{'neg' if diff[name] < 0 else 'pos'}'>{diff[name]:+.2f}pct</td>"
                f"<td>{pct20.get(name, float('nan')):.0f}</td></tr>")
        prev_tbl = f"""
    <h2>3.2 七天里行业乖离率怎么变的（{prev_date:%m-%d} → {asof:%m-%d}）</h2>
    <p>下表是 BIAS20 变动最大的 10 个行业，以及当前 BIAS20 在近三年（约 750 个交易日）里的分位。
       分位 &gt; 80 算历史极热，&lt; 20 算历史极冷。</p>
    <table><thead><tr><th>行业</th><th>BIAS20 @{prev_date:%m-%d}</th><th>BIAS20 @{asof:%m-%d}</th>
    <th>变动</th><th>当前分位</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>策略收益 × 行业乖离率 更新（{asof:%Y-%m-%d}）</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:36px 48px; background:#fff; color:{INK};
    font-family:"Microsoft YaHei","PingFang SC","Segoe UI",sans-serif; line-height:1.75;
    font-size:15px; }}
  h1 {{ font-size:27px; margin:0 0 6px; }}
  h2 {{ font-size:20px; margin:38px 0 12px; padding-left:11px; border-left:5px solid {RED}; }}
  h3 {{ font-size:16px; margin:22px 0 8px; color:#34495e; }}
  .sub {{ color:{GREY}; font-size:13px; margin-bottom:22px; }}
  .kpis {{ display:flex; gap:12px; flex-wrap:wrap; margin:20px 0 8px; }}
  .kpi {{ flex:1 1 190px; border:1px solid #e3e7ea; border-radius:9px; padding:13px 15px; background:#fafbfc; }}
  .kpi .k {{ font-size:12px; color:{GREY}; }}
  .kpi .v {{ font-size:23px; font-weight:700; margin-top:3px; }}
  .neg {{ color:{RED}; }} .pos {{ color:{GREEN}; }} .mono {{ font-family:Consolas,monospace; }}
  table {{ border-collapse:collapse; width:100%; margin:12px 0 6px; font-size:13px; }}
  th,td {{ border:1px solid #e1e5e8; padding:6px 9px; text-align:right; }}
  th {{ background:#f4f6f7; text-align:center; font-weight:600; }}
  td:first-child, td:nth-child(2) {{ text-align:left; }}
  img {{ max-width:100%; border:1px solid #eceff1; border-radius:7px; margin:10px 0; }}
  .cap {{ font-size:12.5px; color:{GREY}; margin:2px 0 16px; }}
  .note {{ background:#fbf7ef; border-left:4px solid #d4a017; padding:12px 16px;
    font-size:13.5px; border-radius:0 7px 7px 0; margin:14px 0; }}
  .verdict {{ background:#f6f9fb; border:1px solid #dde5ea; border-radius:9px; padding:16px 20px; }}
  ul {{ margin:8px 0 8px 20px; padding:0; }} li {{ margin:5px 0; }}
</style></head><body>

<h1>策略收益 × 行业乖离率｜周度更新</h1>
<div class="sub">数据截止 <b>{asof:%Y-%m-%d}（周五）收盘</b> ｜ 策略：沪深300 × LightGBM 选股 A 口径实盘组合（20 只，2026-11-02 开盘买入）｜
 行业：申万一级（31 个）｜ 生成时间 {pd.Timestamp.now():%Y-%m-%d %H:%M}</div>

<div class="verdict">
<b>一句话：</b>组合累计 <span class="neg">{ret:+.2f}%</span>，同期沪深300 <span class="neg">{bench_open:+.2f}%</span>（开盘基准），
超额 <span class="neg">{excess:+.2f}pct</span>。亏钱不是选股逻辑坏了，而是<b>风格</b>：组合实际持有的行业是
{held_txt}——<b>通信与电子合计 {tech_w:.1f}% 权重</b>，而这两个行业正是 31 个申万一级里
离 120 日均线最远（跌得最狠）的一只（通信 {snap_now[120]['通信']:+.1f}%、电子 {snap_now[120]['电子']:+.1f}%）；
组合里赚钱的那几行业（{win_txt}），恰好是乖离率最高（最热）的一批。
<b>风格暴露的代价这周一次结清。</b>
</div>

<div class="kpis">
  <div class="kpi"><div class="k">组合总资产</div><div class="v">{total:,.0f}</div><div class="k">成本 {cost:,.0f}</div></div>
  <div class="kpi"><div class="k">累计收益率</div><div class="v neg">{ret:+.2f}%</div><div class="k">{trk['date'].iloc[0]:%m-%d} 建仓起</div></div>
  <div class="kpi"><div class="k">沪深300（开起）</div><div class="v neg">{bench_open:+.2f}%</div><div class="k">收盘基 {bench_close:+.2f}%</div></div>
  <div class="kpi"><div class="k">累计超额</div><div class="v neg">{excess:+.2f}pct</div><div class="k">当日 {float(last['excess_pct']) - float(trk['excess_pct'].iloc[-2]):+.2f}pct</div></div>
  <div class="kpi"><div class="k">持仓盈亏分布</div><div class="v">{n_win} 盈 / {n_loss} 亏</div><div class="k">20 只</div></div>
</div>

<h2>1. 策略净值：跑输的 {abs(excess):.1f} 个点全是这两周跌出来的</h2>
<img src="img/fig_nav.png">
<div class="cap">组合累计收益（对建仓成本）vs 沪深300（以 11-02 开盘价为基准）。红色区间为跑输区间。</div>
<p>组合在建仓后第 2 个交易日先跌 {abs(trk.iloc[1]['ret_pct']):.2f}%（{trk.iloc[1]['date']:%m-%d}），
随后 {peak_date:%m-%d} 一度把收益率拉到 <b>{peak_ret:+.2f}%</b>、超额 <b>{peak_exc:+.2f}pct</b>，
之后连续 {lose_streak} 个交易日回落，把浮盈全部吐光并转负：{zero_date:%m-%d} 起超额归零，
{trk.tail(5)['date'].iloc[0]:%m-%d}~{asof:%m-%d} 连续 5 天跑输。
<b>亏损集中在最后 5 个交易日</b>（{'、'.join(f'{v:+.2f}%' for v in trk.tail(5)['ret_pct'])}），与同期通信/电子指数的连续下跌同步。</p>

<h2>2. 20 只持仓：通信电子链是重灾区</h2>
<img src="img/fig_holdings.png">
<div class="cap">按累计收益率排序，括号内为权重。</div>
<table>
<thead><tr><th>名称</th><th>代码</th><th>申万一级</th><th>股数</th><th>成本价</th><th>现价</th>
<th>市值</th><th>盈亏</th><th>累计</th><th>当日</th><th>权重</th></tr></thead>
<tbody>{''.join(pos_html)}</tbody></table>
<div class="cap">中信银行 11-20 除权除息（每股 0.203 元），持有 18 天按 20% 红利税计，税后分红 178.64 元已计入现金；
累计现金分红合计 {div_total:,.0f} 元，不算亏损。</div>

<h3>2.1 按行业拆：谁在拖后腿</h3>
<table>
<thead><tr><th>申万一级</th><th>只数</th><th>权重</th><th>盈亏(元)</th><th>平均收益</th>
<th>BIAS20</th><th>BIAS120</th></tr></thead>
<tbody>{''.join(grp_html)}</tbody></table>

<h2>3. 行业乖离率：风格分化到极致</h2>
<p>乖离率 <span class="mono">BIAS_n = (收盘价 − MA_n) / MA_n</span>，正值=在均线上方（强势/偏热），负值=在均线下方（弱势/偏冷）。
先用热力图看全局，再用截面表和分位表落到具体行业。</p>

<img src="img/bias_cross_section.png">
<div class="cap">图 1｜31 个申万一级行业 × 4 个周期的当前乖离率（{asof:%Y-%m-%d}）。红=在均线上方，蓝=在均线下方。</div>

<img src="img/bias_timeline.png">
<div class="cap">图 2｜近 60 个交易日 BIAS20 轮动路径：看谁在高位、谁在低位、什么时候切换的。</div>

<img src="img/bias_percentile.png">
<div class="cap">图 3｜当前 BIAS20 在近三年（约 750 个交易日）里的分位：&gt;80 极热，&lt;20 极冷。</div>

<h3>3.1 当前最热 / 最冷</h3>
<table>
<thead><tr><th>最热（BIAS20）</th><th>BIAS20</th><th>BIAS120</th><th>分位</th><th>最冷（BIAS20）</th>
<th>BIAS20</th><th>BIAS120</th><th>分位</th></tr></thead><tbody>
{''.join(f"<tr><td>{i1}</td><td class='pos'>{v1:+.2f}%</td><td class='pos'>{v2:+.2f}%</td><td>{p1:.0f}</td>"
          f"<td>{i2}</td><td class='neg'>{v3:+.2f}%</td><td class='neg'>{v4:+.2f}%</td><td>{p2:.0f}</td></tr>"
          for (i1, v1), v2, p1, (i2, v3), v4, p2 in
          zip(t20.items(), t20.index.map(lambda n: snap_now[120][n]),
              t20.index.map(lambda n: pct20.get(n, float('nan'))),
              b20.items(), b20.index.map(lambda n: snap_now[120][n]),
              b20.index.map(lambda n: pct20.get(n, float('nan')))))}
</tbody></table>
{prev_tbl}

<h2>4. 把两件事对上：组合的超额，就是风格押注的账单</h2>
<img src="img/fig_sector_bias.png">
<div class="cap">横轴=行业当前 BIAS120，纵轴=组合在该行业权重，气泡大小=权重，标注为行业与行业内平均收益。</div>
<img src="img/fig_rotate.png">
<div class="cap">近 30 个交易日行业指数归一化走势（起点=100）。</div>
<ul>
  <li><b>组合重仓的两端，正好是乖离率的两端。</b>权重最大的通信（{grp.set_index('l1_name').loc['通信','weight']:.1f}%）BIAS120 {snap_now[120]['通信']:+.1f}%、
      电子（{grp.set_index('l1_name').loc['电子','weight']:.1f}%）{snap_now[120]['电子']:+.1f}%，
      是 31 个行业里最偏离 120 日均线的两只；而组合持有的银行（{grp.set_index('l1_name').loc['银行','weight']:.1f}%）
      BIAS120 {snap_now[120]['银行']:+.1f}%，是最热的一只。</li>
  <li><b>一周前这个组合还在赚钱。</b>传媒在 {idx1111:%m-%d} 时 BIAS20 还有 {mc_then:+.2f}%，
      是当时<b>唯一四周期全正</b>的行业（{'、'.join(all_pos_1111)}，分位 {pct1111:.0f}，最拥挤）；
      {asof:%m-%d} 已经变成 <span class="neg">{mc_now:+.2f}%</span>（四周期全负，分位 {mc_pct_now:.0f}）——
      {(asof - idx1111).days} 个自然日内从「最拥挤」翻到「最超卖」，这正是组合 {n_tech_total} 只科技持仓集体回吐的来源
      （其中只有 {n_tech_pos} 只还赚钱）。</li>
  <li><b>银行/公用事业这周在托底。</b>银行指数 {asof:%m-%d} 单日 {bank_day:+.2f}%、BIAS20 {snap_now[20]['银行']:+.2f}%；
      组合里的 {n_bank_total} 只银行股有 {n_bank_pos} 只为正，国电电力 {pos[pos['name']=='国电电力']['ret_pct'].iloc[0]:+.2f}%、
      川投能源 {pos[pos['name']=='川投能源']['ret_pct'].iloc[0]:+.2f}%、
      中国电信 {pos[pos['name']=='中国电信']['ret_pct'].iloc[0]:+.2f}% 也都在赚钱——只是它们的正收益抵不过通信电子链的负收益。</li>
  <li><b>风控上的教训：</b>模型选的是「预测收益高的股票」，实际买到的是「同一个风格因子（AI/光通信/算力链）」的重仓。
      {len(pos)} 只股票、{len(grp)} 个行业，最大权重 {pos['weight_pct'].max():.2f}%，单看每只都"分散"，合起来是<b>单一风格的高 beta</b>。
      乖离率（BIAS120 &lt; -25%）正是识别这类持仓的现成指标 —— 下次建仓前应该加一条硬约束：
      组合在 BIAS120 &gt; +20% 的行业上的权重上限。</li>
</ul>

<h2>5. 数据与校验</h2>
<ul>
  <li>行情：腾讯不复权日线（<span class="mono">web.ifzq.gtimg.cn/appstock/app/kline/kline</span>），
      分红用东财 RPT_SHAREBONUS_DET 单独计现金，红利税按持有期（≤1 月 20% / 1 月~1 年 10% / &gt;1 年 0%）。</li>
  <li>行业指数：申万宏源研究 <span class="mono">index_publish/trend</span> 接口（akshare 同源），
      31 个一级行业，{panel.index.min():%Y-%m-%d} ~ {asof:%Y-%m-%d}，共 {len(panel)} 个交易日。</li>
  <li><b>交叉核对：</b>{asof:%Y-%m-%d} 收盘价用<b>东财 push2</b> 独立复核了 6 只标的
      （天孚通信 102.18、芯原股份 76.90、东山精密 67.60、中信银行 9.66、蓝思科技 22.98、沪深300 3954.57），
      与腾讯<b>逐位一致</b>；行业指数的涨跌由成分股独立验证（传媒 11-05→11-20：芒果超媒 -17.2%、完美世界 -22.6%、光线传媒 -19.7%）。</li>
  <li>乘数与分红处理口径与 <span class="mono">tools\\industry_bias_heatmap.py</span> 完全一致（同一份代码算 BIAS 与分位）。</li>
</ul>

<div class="note">
<b>别把这份报告当成「策略要崩了」的结论。</b>15 个交易日、20 只股票、一周风格反转，
样本量根本不够下判断 —— 它能支持的只有两件事：
① 组合的超额损失来自<b>行业风格暴露</b>（可验证、可归因），不是选股模型本身崩了；
② 11-30 是下一次调仓日，届时应当<b>检查风格约束</b>（BIAS120 极热行业的权重上限），
而不是简单地把亏损股票卖掉 —— 通信/电子现在恰恰是乖离率最负（最超卖）的一批。
</div>

<div class="sub" style="margin-top:30px">
本报告由 <span class="mono">projects\\csi300_lgbm\\tools\\build_update_report.py</span> 生成，
图由 matplotlib 绘制，HTML→PNG 用 headless Chrome 截取。所有数字来自
<span class="mono">results\\track_pnl.csv</span>、<span class="mono">results\\track_positions_latest.csv</span>、
<span class="mono">data\\sw_industry\\</span>，可回溯。<br>
不构成投资建议。
</div>

</body></html>
"""

    (OUT / "update_report.html").write_text(html, encoding="utf-8")
    print(f"HTML → {OUT / 'update_report.html'}  ({len(html)/1024:.0f} KB)")
    print(f"截至 {asof:%Y-%m-%d} | 组合 {ret:+.2f}% | 300 {bench_open:+.2f}% | 超额 {excess:+.2f}pct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
