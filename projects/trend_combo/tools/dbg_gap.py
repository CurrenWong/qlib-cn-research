"""查清：10-30 面板里 close 为 NaN 的那些票，到底是「真退市/停牌」还是「数据缺口」。

做法：对每个 10-30 有分数但无收盘价的票，找它面板里最后一个有收盘价的日期，
      再去腾讯拉最新行情看最后交易日。
"""

import time
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parent.parent
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counterfactual_oct import fetch_raw, tx_symbol  # noqa: E402

COLS = ["datetime", "symbol", "close", "price_score", "fund_score", "event_score"]
sc = pd.read_parquet(PROJ / "data" / "scores.parquet", columns=COLS)
sc["datetime"] = pd.to_datetime(sc["datetime"])
day = sc[sc["datetime"] == pd.Timestamp("2026-10-30")].copy()

has_score = day[day["price_score"].notna() | day["fund_score"].notna()]
no_px = has_score[has_score["close"].isna()]
print("10-30 有分数但无收盘价:", len(no_px), "只（下列抽查 12 只）")

for sym in list(no_px["symbol"])[:12]:
    hist = sc[(sc["symbol"] == sym) & sc["close"].notna()].sort_values("datetime")
    last_panel = hist["datetime"].max() if len(hist) else None
    df = fetch_raw(tx_symbol(sym), count=8)
    last_live = df.index.max() if len(df) else None
    print(f"  {sym}  面板最后有价 {last_panel}  腾讯最后交易日 {last_live}  "
          f"price_score={day.set_index('symbol').loc[sym, 'price_score']}")
    time.sleep(0.2)

print("\n=== 抽查 6 只进入混合分 top20 但面板无价的票 ====")
for sym in ["SH600648", "SH600079", "SH600848", "SH603195", "SH600867", "SH600763"]:
    hist = sc[(sc["symbol"] == sym) & sc["close"].notna()].sort_values("datetime")
    last_panel = hist["datetime"].max() if len(hist) else None
    df = fetch_raw(tx_symbol(sym), count=8)
    last_live = df.index.max() if len(df) else None
    live = df.loc[pd.Timestamp("2026-11-02"):pd.Timestamp("2026-11-05")] if len(df) else df
    print(f"  {sym}  面板最后有价 {last_panel}  腾讯最后交易日 {last_live}")
    if len(live):
        print("      11-02~11-05:", live[["open", "close"]].round(2).to_dict("index"))
    time.sleep(0.2)
