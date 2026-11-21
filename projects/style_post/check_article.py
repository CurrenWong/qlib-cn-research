"""数字自检：把 article.md 里出现的每个关键数字，重新从源数据算一遍核对。

用法：
    ..\\..\\.venv\\Scripts\\python.exe check_article.py [文章路径]

原则（AGENTS.md §9）：**数字必须来自实际输出**。正文写死的数字必须能在源文件里复算出来，
否则就是"凭印象写"。退出码非 0 = 有数字对不上。

数据源：
  projects\\csi300_lgbm\\results\\track_pnl.csv          组合净值
  projects\\csi300_lgbm\\results\\track_positions_latest.csv  持仓明细
  data\\sw_industry\\bias\\bias_snapshot.csv              乖离率截面
  data\\sw_industry\\index_daily\\*.parquet               行业日线（复算分位与历史值）
  data\\sw_industry\\map.parquet                          股票 → 申万一级
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import industry_bias_heatmap as ibh  # noqa: E402

ARTICLE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "article.md"
TEXT = ARTICLE.read_text(encoding="utf-8")

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(f"{name}  {detail}")


def has(s: str) -> bool:
    """文章里是否出现这个字符串（数字按正文里的写法核对）。"""
    return s in TEXT


def num(x: float, fmt: str = "+.2f") -> str:
    return format(x, fmt)


# ---------------------------------------------------------------- 源数据
trk = pd.read_csv(REPO / "projects" / "csi300_lgbm" / "results" / "track_pnl.csv")
trk["date"] = pd.to_datetime(trk["date"])
pos = pd.read_csv(REPO / "projects" / "csi300_lgbm" / "results" / "track_positions_latest.csv")
amap = pd.read_parquet(REPO / "data" / "sw_industry" / "map.parquet")
pos = pos.merge(amap[["qlib_symbol", "l1_name"]], left_on="symbol", right_on="qlib_symbol",
                how="left")
pos["l1_name"] = pos["l1_name"].fillna("未分类")
snap = pd.read_csv(REPO / "data" / "sw_industry" / "bias" / "bias_snapshot.csv", index_col=0,
                    encoding="utf-8-sig")

last = trk.iloc[-1]

# ---------------------------------------------------------------- 组合净值
check("组合累计收益 -8.18%", has(num(float(last["ret_pct"]))), num(float(last["ret_pct"])))
check("沪深300 开盘基 -1.28%", has(num(float(last["bench_ret_from_open_pct"]))),
      num(float(last["bench_ret_from_open_pct"])))
check("超额 -6.89pct", has(num(float(last["excess_pct"]))), num(float(last["excess_pct"])))
check("总资产 235,555", has(f"{float(last['total']):,.0f}"), f"{float(last['total']):,.0f}")
check("成本 256,525", has(f"{float(last['cost']):,.0f}"), f"{float(last['cost']):,.0f}")
check("交易日 15 个", len(trk) == 15 and has("15 个交易日"), str(len(trk)))
check("8 盈 12 亏", int((pos["ret_pct"] > 0).sum()) == 8 and int((pos["ret_pct"] <= 0).sum()) == 12
      and has("8 盈 12 亏"), f"{int((pos['ret_pct'] > 0).sum())} 盈 "
                           f"{int((pos['ret_pct'] <= 0).sum())} 亏")

for d, val, key in [("11-03", -4.43, "ret_pct"), ("11-11", 4.19, "ret_pct"),
                    ("11-16", -3.45, "ret_pct"), ("11-18", -3.68, "ret_pct")]:
    row = trk[trk["date"] == pd.Timestamp("2026-" + d)]
    v = float(row[key].iloc[0]) if len(row) else float("nan")
    check(f"{d} 收益 {val:+.2f}%", abs(v - val) < 0.005 and has(f"{val:+.2f}%"), f"{v:+.2f}%")
check("11-11 超额 +2.45pct",
      abs(float(trk[trk["date"] == pd.Timestamp("2026-11-11")]["excess_pct"].iloc[0]) - 2.45) < 0.005
      and has("+2.45pct"))

# ---------------------------------------------------------------- 持仓
worst5 = pos.nsmallest(5, "ret_pct")
best5 = pos.nlargest(5, "ret_pct")
listed = pd.concat([worst5, best5])
for _, r in listed.iterrows():
    check(f"持仓 {r['name']} {r['ret_pct']:+.2f}%", has(f"{r['ret_pct']:+.2f}%"),
          f"{r['ret_pct']:+.2f}%")
check("最大权重 7.13%", abs(pos["weight_pct"].max() - 7.13) < 0.005 and has("7.13%"),
      f"{pos['weight_pct'].max():.2f}%")
check("持仓 20 只", len(pos) == 20 and has("20 只"), str(len(pos)))
for _, r in worst5.iterrows():
    check(f"最差 {r['name']} 在跌前五", r["ret_pct"] < 0)
for _, r in best5.iterrows():
    check(f"最好 {r['name']} 在赚前五", r["ret_pct"] > 0)

# ---------------------------------------------------------------- 行业归因
grp = pos.groupby("l1_name").agg(weight=("weight_pct", "sum"), pnl=("pnl", "sum"),
                                  ret=("ret_pct", "mean"), n=("symbol", "count")).reset_index()
for _, r in grp.iterrows():
    check(f"行业 {r['l1_name']} 权重 {r['weight']:.1f}%", has(f"{r['weight']:.1f}%"),
          f"{r['weight']:.1f}%")
    check(f"行业 {r['l1_name']} 盈亏 {r['pnl']:,.0f}", has(f"{r['pnl']:,.0f}"), f"{r['pnl']:,.0f}")
    check(f"行业 {r['l1_name']} 均收益 {r['ret']:+.2f}%", has(f"{r['ret']:+.2f}%"),
          f"{r['ret']:+.2f}%")

tech = grp[grp["l1_name"].isin(["电子", "通信"])]
check("电子+通信 58.6%", abs(tech["weight"].sum() - 58.6) < 0.05 and has("58.6%"),
      f"{tech['weight'].sum():.1f}%")
check("电子+通信 亏 21,916", abs(tech["pnl"].sum() + 21916) < 1 and has("21,916"),
      f"{tech['pnl'].sum():,.0f}")
win = grp[grp["l1_name"].isin(["银行", "公用事业"])]
check("银行+公用 32.3%", abs(win["weight"].sum() - 32.3) < 0.05 and has("32.3%"),
      f"{win['weight'].sum():.1f}%")
check("银行+公用 赚 3,339", abs(win["pnl"].sum() - 3339) < 1 and has("3,339"),
      f"{win['pnl'].sum():,.0f}")
check("行业 5 个", grp.shape[0] == 5 and has("5 个行业"), str(grp.shape[0]))

# ---------------------------------------------------------------- 乖离率
for ind in ["银行", "家用电器", "食品饮料", "公用事业", "非银金融", "交通运输",
            "国防军工", "传媒", "综合", "有色金属", "机械设备", "通信", "电子"]:
    for col, fmt in [("20", "+.2f"), ("120", "+.2f")]:
        v = float(snap.loc[ind, col])
        check(f"{ind} BIAS{col} {v:+.2f}%", has(f"{v:+.2f}%"), f"{v:+.2f}%")

# 分位（近 750 个交易日）
panel = ibh.build_panel(ibh.load_industries(), refresh=False)
bm = ibh.bias_matrix(panel, [6, 20, 60, 120])
pct = pd.Series({n: ibh.percentile_rank(bm[20][n], 750) for n in panel.columns})
for ind, want in [("银行", 95), ("通信", 3), ("传媒", 1), ("家用电器", 81), ("食品饮料", 80)]:
    v = int(round(float(pct[ind])))
    hit = False
    for ln in TEXT.splitlines():
        cells = [c.strip() for c in ln.split("|")]
        if ind not in cells:
            continue
        i = cells.index(ind)
        tail = cells[i + 1: i + 4]          # BIAS20 / BIAS120 / 分位
        if len(tail) == 3 and tail[2].strip("*") == str(want):
            hit = True
    check(f"{ind} 分位 {want}", v == want and hit, f"{v} | 命中 {hit}")

# 传媒 11-11 的状态
i1111 = panel.index[panel.index <= pd.Timestamp("2026-11-11")][-1]
ii = panel.index.get_loc(i1111)
b1111 = {n: bm[n].iloc[ii] for n in [6, 20, 60, 120]}
mc_then = float(b1111[20]["传媒"])
allpos = [n for n in panel.columns if all(b1111[p][n] > 0 for p in [6, 20, 60, 120])]
check("传媒 11-11 BIAS20 +7.66%", abs(mc_then - 7.66) < 0.005 and has("+7.66%"),
      f"{mc_then:+.2f}%")
check("传媒 11-11 四周期全正（传媒/农林牧渔/银行）",
      allpos == ["传媒", "农林牧渔", "银行"], str(allpos))
pct_then = ibh.percentile_rank(bm[20]["传媒"].iloc[: ii + 1], 750)
check("传媒 11-11 分位 93", int(round(pct_then)) == 93 and has("分位 **93**"),
      f"{pct_then:.0f}")
check("传媒 11-20 四周期全负",
      all(bm[n].iloc[-1]["传媒"] < 0 for n in [6, 20, 60, 120]))
check("行业日线 6504 个交易日", len(panel) == 6504 and has("6504 个交易日"), str(len(panel)))
check("行业指数起点 1999-12-30", str(panel.index.min().date()) == "1999-12-30"
      and has("1999-12-30"))

# 11-13 → 11-20 的 BIAS20 变动榜
i1113 = panel.index[panel.index <= pd.Timestamp("2026-11-13")][-1]
i13 = panel.index.get_loc(i1113)
diff = (bm[20].iloc[-1] - bm[20].iloc[i13]).sort_values()
for ind, want in [("传媒", -14.81), ("机械设备", -9.15), ("商贸零售", -8.69),
                  ("国防军工", -8.52), ("纺织服饰", -8.29), ("银行", 1.78)]:
    v = float(diff[ind])
    check(f"{ind} BIAS20 变动 {want:+.2f}pct", abs(v - want) < 0.005 and has(f"{want:+.2f}pct"),
          f"{v:+.2f}pct")

# ---------------------------------------------------------------- 分红
check("累计现金分红 275 元", abs(float(trk["cash_div"].iloc[-1]) - 275) < 1 and has("275 元"),
      f"{float(trk['cash_div'].iloc[-1]):.0f}")
check("中信银行每股 0.203 元", has("0.203 元"))
check("税后分红 178.64 元", has("178.64 元"))

# ---------------------------------------------------------------- 成分与图片
mem = pd.read_parquet(REPO / "data" / "sw_industry" / "members.parquet")
check("申万成分 5222 只", len(mem) == 5222 and has("5222 只"), str(len(mem)))

imgs = re.findall(r"【插图\s*\d+：([^｜]+)｜图注：([^】]+)】", TEXT)
check("插图 7 张", len(imgs) == 7, str(len(imgs)))
for rel, cap in imgs:
    check(f"图文件存在 {rel}", (HERE / rel.strip()).exists())
    check(f"图注非空 {rel}", len(cap.strip()) > 8)
n_h2 = len(re.findall(r"^## ", TEXT, flags=re.M))
check("H2 章节 9 节", n_h2 == 9, str(n_h2))

# ---------------------------------------------------------------- 输出
print(f"== 数字自检 {ARTICLE.name} ==")
print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
if FAIL:
    print("\n失败项：")
    for f in FAIL:
        print("  ✗", f)
    sys.exit(1)
print("全部通过 ✅")
