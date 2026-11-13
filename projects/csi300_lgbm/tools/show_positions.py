"""打印 track_positions_latest.csv 的逐只明细（只读核验用）。"""

import csv
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "results"
rows = list(csv.DictReader(open(RES / "track_positions_latest.csv", encoding="utf-8-sig")))
print("行数", len(rows), "| 字段", list(rows[0].keys()))
print(f"{'名称':<8}{'代码':<11}{'股数':>6}{'成本价':>9}{'现价':>9}{'市值':>10}{'盈亏':>10}"
      f"{'累计%':>9}{'当日%':>8}{'权重%':>8}")
for r in rows:
    print(f"{r['name']:<8}{r['symbol']:<11}{r['shares']:>6}{r['entry_price']:>9}"
          f"{r['close']:>9}{r['mkt_value']:>10}{r['pnl']:>10}"
          f"{float(r['ret_pct']):>9.2f}{float(r['day_ret_pct']):>8.2f}"
          f"{float(r['weight_pct']):>8.2f}")
mv = sum(float(r["mkt_value"]) for r in rows)
pnl = sum(float(r["pnl"]) for r in rows)
print(f"市值合计 {mv:,.2f} | 盈亏合计 {pnl:,.2f}")
