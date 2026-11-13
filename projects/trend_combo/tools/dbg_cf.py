"""调试：打印 counterfactual 的各变体选股与取价失败情况。"""

import json
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parent.parent
RESULTS = PROJ / "results"

sc = pd.read_parquet(PROJ / "data" / "scores.parquet",
                     columns=["datetime", "symbol", "price_score", "fund_score",
                              "event_score", "board_name"])
sc["datetime"] = pd.to_datetime(sc["datetime"])
day = sc[sc["datetime"] == pd.Timestamp("2026-10-30")].copy()
day["symbol"] = day["symbol"].astype(str)

w = json.loads((RESULTS / "backtest.json").read_text(encoding="utf-8"))["weights"]
wp, wf, we = w["recommended"]["price"], w["recommended"]["fund"], w["recommended"]["event"]
day["mix_rec"] = wp * day["price_score"] + wf * day["fund_score"] + we * day["event_score"]

for col, K in [("mix_rec", 20), ("price_score", 20), ("fund_score", 20)]:
    d = day[day[col].notna()].sort_values(col, ascending=False).head(K)
    print(f"\n== {col} top{K} ==")
    for _, r in d.iterrows():
        print(f"  {r['symbol']:<11} {col}={r[col]:+.4f} price={r['price_score']:+.4f} "
              f"fund={r['fund_score']:+.4f} event={r['event_score']:+.4f} "
              f"board={r['board_name']}")

print("\nprice_score NaN 数:", int(day["price_score"].isna().sum()),
      "| fund_score NaN:", int(day["fund_score"].isna().sum()),
      "| event_score NaN:", int(day["event_score"].isna().sum()))
