"""调试：price_score 限幅分布 + counterfactual 日志里的取价失败。"""

from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parent.parent
RESULTS = PROJ / "results"

print("==== 日志中的取价失败行 ====")
log = (RESULTS / "counterfactual_oct.log").read_text(encoding="utf-8", errors="replace")
for ln in log.splitlines():
    if "失败" in ln or "空返回" in ln or "无行情" in ln or "停牌" in ln:
        print(ln)

print("\n==== price_score 分布 ====")
sc = pd.read_parquet(PROJ / "data" / "scores.parquet",
                     columns=["datetime", "symbol", "price_score", "fund_score", "event_score"])
sc["datetime"] = pd.to_datetime(sc["datetime"])
day = sc[sc["datetime"] == pd.Timestamp("2026-10-30")].copy()
p = day["price_score"]
print("max", p.max(), "min", p.min())
print("等于 max 的只数:", int((p == p.max()).sum()))
top = day.sort_values("price_score", ascending=False).head(30)
print("前 30 只里等于 max 的:", int((top["price_score"] == p.max()).sum()))
print("前 30 的 price_score:", [round(float(x), 4) for x in top["price_score"].head(30)])
q = p.quantile([0.9, 0.95, 0.99, 1.0])
print("分位:", {str(k): round(float(v), 4) for k, v in q.items()})
