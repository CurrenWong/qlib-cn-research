import json
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 260)
pd.set_option("display.unicode.east_asian_width", True)

rows = []
for d in ["results_A", "results_B", "results_C"]:
    m = pd.read_csv(f"{d}/metrics.csv")
    t = m[m["区间"] == "测试集"].set_index("标的")
    for lbl in ["策略（择时）", "策略（零成本对照）", "沪深300", "买入持有江淮汽车"]:
        r = t.loc[lbl]
        rows.append({"方案": d[-1], "标的": lbl, "区间收益": r["区间收益"], "年化": r["年化收益"],
                     "夏普": r["夏普"], "IR": r["信息比率"], "MDD": r["最大回撤"],
                     "日胜率": r["日胜率"], "成本": r["总成本"]})
df = pd.DataFrame(rows)
for c in ["区间收益", "年化", "MDD", "日胜率"]:
    df[c] = df[c].map(lambda v: f"{v:.2%}" if pd.notna(v) else "-")
for c in ["夏普", "IR"]:
    df[c] = df[c].map(lambda v: f"{v:.3f}" if pd.notna(v) else "-")
print(df.to_string(index=False))

# 成本拖累 = 零成本年化 - 含成本年化
print()
for d in ["results_A", "results_B", "results_C"]:
    m = pd.read_csv(f"{d}/metrics.csv")
    t = m[m["区间"] == "测试集"].set_index("标的")
    drag = t.loc["策略（零成本对照）", "年化收益"] - t.loc["策略（择时）", "年化收益"]
    ex = t.loc["策略（择时）", "年化收益"] - t.loc["沪深300", "年化收益"]
    ex0 = t.loc["策略（零成本对照）", "年化收益"] - t.loc["沪深300", "年化收益"]
    print(f"{d}: 成本拖累 {drag:.2%}/年 | 对指数超额(含成本) {ex:+.2%}/年 | 超额(零成本) {ex0:+.2%}/年")
