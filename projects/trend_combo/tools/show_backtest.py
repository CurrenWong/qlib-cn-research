import json

import pandas as pd

P = r"D:\Project\qlib\projects\trend_combo\results"
b = json.load(open(P + r"\backtest.json", encoding="utf-8"))

print("=== 测试期 2023-01-01 ~ 2026-10-30 ===")
hdr = f"{'策略':<26}{'年化':>9}{'总收益':>9}{'波动':>8}{'Sharpe':>8}{'MDD':>8}{'IR':>7}{'超额年化':>9}{'换手/年':>9}{'成本/年':>9}"
print(hdr)
for k, v in b["runs"].items():
    print(f"{k:<26}{v.get('ann_return',0)*100:>8.2f}%{v.get('total_return',0)*100:>8.2f}%"
          f"{v.get('ann_vol',0)*100:>7.2f}%{v.get('sharpe',0):>8.2f}"
          f"{v.get('max_drawdown',0)*100:>7.2f}%{v.get('ir',0):>7.2f}"
          f"{v.get('excess_ann',0)*100:>8.2f}%{v.get('ann_turnover',0):>9.2f}"
          f"{v.get('cost_per_year_pct',0):>8.2f}pct")

print("\n=== 分年收益 ===")
y = pd.read_csv(P + r"\backtest_yearly.csv")
piv = y.pivot_table(index="run", columns="year", values="ret")
print((piv * 100).round(2).to_string())

print("\n=== 全区间 2016-2026 ===")
f = b["full_period"]
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in f.items()
       if k in ("ann_return", "total_return", "max_drawdown", "ir", "excess_ann",
                "ann_turnover", "total_cost", "cost_per_year_pct")})
