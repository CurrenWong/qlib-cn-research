"""复核 counterfactual 总账（从 JSON 读，和报告对账）。"""

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"
j = json.loads((RESULTS / "counterfactual_oct30.json").read_text(encoding="utf-8"))

print("信号日", j["signal_date"], "| 建仓", j["entry"], "| 平仓", j["exit"])
print(f"{'组合':<50}{'只数':>4}{'投入(元)':>12}{'净收益率':>10}")
for v in j["variants"]:
    print(f"{v['label']:<50}{v['n']:>4}{v['total_cost']:>12,.0f}{v['ret_net_pct']:>9.2f}%")
L = j["live"]
print(f"{L['label']:<50}{L['n']:>4}{L['total_cost']:>12,.0f}{L['ret_net_pct']:>9.2f}%")
print(f"{'沪深300（同期）':<50}{'':>4}{'':>12}{j['benchmark']['ret_pct']:>9.2f}%")
print("\n重叠：", {k: v["n_overlap"] for k, v in j["overlap"].items()})
print("实盘 20 只在混合分的排名：",
      [r["rank"] for r in j["live_mix_rank"]])
