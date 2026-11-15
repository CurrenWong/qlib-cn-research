"""把 picks_K20.json 变成可执行清单：等权权重、一手金额、最小资金、板块分布。"""

import json
from collections import Counter
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

RES = Path(_ROOT + r"/projects/csi300_lgbm/results")
d = json.loads((RES / "picks_K20.json").read_text(encoding="utf-8"))
picks = d["picks"]
n = len(picks)
w = 1.0 / n

lot_cost = [(p["name"], p["symbol"], p["close_adj"], p["close_adj"] * 100) for p in picks]
total_lot = sum(c for *_, c in lot_cost)

print(f"as_of {d['as_of']}  pool {d['pool_size']}  持仓 {n} 只  等权 {w*100:.2f}%")
print(f"一手(100股)合计 {total_lot:,.0f} 元；按等权最小可执行资金约 {total_lot:,.0f} 元")
for target in (100_000, 300_000, 1_000_000):
    per = target / n
    print(f"  资金 {target/1e4:6.0f} 万 → 每只 {per:8,.0f} 元 ≈ "
          f"{sum(max(1, int(per // (c*100))) for _, _, _, c in lot_cost)} 手总额")

print("\n明细:")
for i, (name, sym, px, lot) in enumerate(lot_cost, 1):
    print(f"  {i:2d}. {sym} {name:6s} 收盘 {px:8.2f}  一手 {lot:9,.0f} 元  权重 {w*100:4.2f}%")

print("\n板块:", dict(Counter(p["board"] for p in picks)))
print("近20日跌幅>20%:", sum(1 for p in picks if (p["ret_20"] or 0) < -0.20), "只")
print("近20日为正:", sum(1 for p in picks if (p["ret_20"] or 0) > 0), "只")
amt = sorted(p["amount_yuan"] for p in picks)
print(f"日成交额 中位数 {amt[len(amt)//2]/1e8:.2f} 亿，最小 {amt[0]/1e8:.2f} 亿")
