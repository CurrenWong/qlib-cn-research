"""A 组（全池 637）与 B 组（干净池 299）的差异拆解。"""

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"
j = json.loads((RESULTS / "counterfactual_oct30.json").read_text(encoding="utf-8"))
A = next(v for v in j["variants"] if v["label"].startswith("A "))
B = next(v for v in j["variants"] if v["label"].startswith("B "))


def rows(v):
    return {r["symbol"]: r for r in v["rows"]}


ra, rb = rows(A), rows(B)
only_a = [s for s in A["picks"] if s not in rb]
only_b = [s for s in B["picks"] if s not in ra]
common = [s for s in A["picks"] if s in rb]

print(f"A 组 {len(A['picks'])} 只 / B 组 {len(B['picks'])} 只；"
      f"共同 {len(common)} 只，A 独有 {len(only_a)} 只，B 独有 {len(only_b)} 只\n")

print("A 独有（分数带缺口：面板价只到 10-27，用旧价算的分）：")
tot = 0.0
for s in only_a:
    r = ra[s]
    tot += r["pnl"]
    print(f"  {r['name']:<8}{s:<11} 买 {r['buy_open']:>8} 卖 {r['sell_close']:>8} "
          f"{r['ret_pct']:>7.2f}%  盈亏 {r['pnl']:+,.0f}")
print(f"  → 6 只合计盈亏 {tot:+,.0f} 元")

print("\nB 独有（10-30 当天有收盘价，纳入干净池后顶上来的）：")
tot2 = 0.0
for s in only_b:
    r = rb[s]
    tot2 += r["pnl"]
    print(f"  {r['name']:<8}{s:<11} 买 {r['buy_open']:>8} 卖 {r['sell_close']:>8} "
          f"{r['ret_pct']:>7.2f}%  盈亏 {r['pnl']:+,.0f}")
print(f"  → 6 只合计盈亏 {tot2:+,.0f} 元")

print("\n共同 14 只的合计：")
c = sum(ra[s]["pnl"] for s in common)
print(f"  合计盈亏 {c:+,.0f} 元")

print(f"\nA 组总盈亏 {A['pnl_gross']:+,.0f} 元（毛）/ 投入 {A['total_cost']:,.0f} → {A['ret_gross_pct']:+.2f}%")
print(f"B 组总盈亏 {B['pnl_gross']:+,.0f} 元（毛）/ 投入 {B['total_cost']:,.0f} → {B['ret_gross_pct']:+.2f}%")
print(f"\n差额（毛收益率）{A['ret_gross_pct'] - B['ret_gross_pct']:+.2f} pct；"
      f"净差额 {A['ret_net_pct'] - B['ret_net_pct']:+.2f} pct")
print(f"投入也不同：A {A['total_cost']:,.0f} vs B {B['total_cost']:,.0f}"
      f"（A 组里 2 只高价股各占 2 手，B 组单价分布更散）")
