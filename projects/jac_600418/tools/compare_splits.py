"""汇总三种样本切分方案的回测结果（读 results_X/metrics.csv + summary.json）。"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
pd.set_option("display.width", 320)
pd.set_option("display.unicode.east_asian_width", True)

rows = []
for d in ["results_A", "results_B", "results_C"]:
    p = ROOT / d
    if not (p / "metrics.csv").exists():
        continue
    m = pd.read_csv(p / "metrics.csv")
    c = json.loads((p / "strategy_choice.json").read_text(encoding="utf-8"))
    s = json.loads((p / "summary.json").read_text(encoding="utf-8"))
    t = m[m["区间"] == "测试集"].set_index("标的")
    st, zz, bh, bn = (t.loc["策略（择时）"], t.loc["策略（零成本对照）"],
                      t.loc["买入持有江淮汽车"], t.loc["沪深300"])
    rows.append({
        "方案": d[-1],
        "测试区间": f"{s['split']['test'][0]}~{s['split']['test'][1]}",
        "年数": round(s["split"]["test"][2] / 252, 2),
        "参数": f"{c['model']}/{c['rule']}/q{c['q']}/sm{c['smooth']}",
        "WF_IR均值": round(c["IR_mean_walkforward"], 3),
        "正折": f"{c['folds_positive']}/{c['folds']}",
        "测试IC": round(s["ic"]["test"]["IC"], 4),
        "策略年化": st["年化收益"],
        "零成本年化": zz["年化收益"],
        "HS300年化": bn["年化收益"],
        "买持年化": bh["年化收益"],
        "策略MDD": st["最大回撤"],
        "仓位": st["平均仓位"],
        "年化换手": st["年化换手"],
        "成本/本金": st["总成本"] / 1e6,
    })

df = pd.DataFrame(rows)
pct = ["策略年化", "零成本年化", "HS300年化", "买持年化", "策略MDD", "仓位", "成本/本金"]
show = df.copy()
for c in pct:
    show[c] = show[c].map(lambda v: f"{v:.2%}")
show["年化换手"] = show["年化换手"].map(lambda v: f"{v:.1f}x")
print(show.to_string(index=False))

print("\n【方案 A 分段（普通回测区间外，仅看测试期年度表现）】")
p = ROOT / "results_A" / "nav_test.csv"
nav = pd.read_csv(p, index_col=0, parse_dates=True)
print(nav.resample("YE").last().pct_change().round(4).to_string())
