"""核对对照实验的前提是否成立（宇宙一致 / 僵尸股影响 / 分数头尾收益差）。"""

import json
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parent.parent
RESULTS = PROJ / "results"
LGBM = Path(r"D:\Project\qlib\projects\csi300_lgbm")

COLS = ["datetime", "symbol", "close", "price_score", "fund_score", "event_score", "board_name"]
sc = pd.read_parquet(PROJ / "data" / "scores.parquet", columns=COLS)
sc["datetime"] = pd.to_datetime(sc["datetime"])
day = sc[sc["datetime"] == pd.Timestamp("2026-10-30")].copy()
live299 = set(day.loc[day["close"].notna(), "symbol"])
print("10-30 有有效收盘价的只数:", len(live299))

w = json.loads((RESULTS / "backtest.json").read_text(encoding="utf-8"))["weights"]
wp, wf, we = (w["recommended"]["price"], w["recommended"]["fund"], w["recommended"]["event"])
day["mix_rec"] = wp * day["price_score"] + wf * day["fund_score"] + we * day["event_score"]

book = json.loads((LGBM / "results" / "positions_A.json").read_text(encoding="utf-8"))
live20 = [p["symbol"] for p in book["positions"]]
print("实盘 20 只里在 299 有效池内的:", sum(1 for s in live20 if s in live299), "/ 20")
print("不在池内的:", [s for s in live20 if s not in live299])

# 混合分 top20：全池 vs 剔僵尸池，是否一样
def top(df, col, K):
    d = df[df[col].notna()].sort_values(col, ascending=False)
    return list(d["symbol"].head(K))


t_all = top(day, "mix_rec", 20)
t_pool = top(day[day["close"].notna()], "mix_rec", 20)
print("\n混合分 top20（全池637）== 剔僵尸池（299）:", t_all == t_pool)
t_all_p = top(day, "price_score", 20)
t_pool_p = top(day[day["close"].notna()], "price_score", 20)
print("纯价量 top20（全池）前 5:", t_all_p[:5])
print("纯价量 top20（剔僵尸）前 5:", t_pool_p[:5])
zomb = set(day["symbol"]) - live299
print("  → 全池版本里有僵尸股的只数:", len(set(t_all_p) & zomb))

print("\n混合分 top20 全池 vs 有效池 的差异：")
print("  仅在全池里:", [s for s in t_all if s not in t_pool])
print("  仅在有效池里:", [s for s in t_pool if s not in t_all])
sub = day.set_index("symbol")
for s in [s for s in t_all if s not in t_pool]:
    r = sub.loc[s]
    print(f"    {s} close={r['close']} price={r['price_score']:+.4f} "
          f"fund={r['fund_score']:+.4f} event={r['event_score']} mix={r['mix_rec']:+.4f}")

# 分数头尾在 11-02~11-05 的实际收益差（用 counterfactual 的行情缓存不方便，这里只报排名分布）
rank = day.set_index("symbol")["mix_rec"].rank(ascending=False)
live_ranks = [int(rank[s]) for s in live20 if s in rank.index]
live_ranks.sort()
print("\n实盘 20 只在混合分里的排名（中位数 / 最好 / 最差）:",
      live_ranks[len(live_ranks) // 2], "/", live_ranks[0], "/", live_ranks[-1])
print("  进入全池前 20 的:", [s for s in live20 if rank.get(s, 999) <= 20])

# 行业分布对比
print("\n混合分 top20 行业:", day.set_index("symbol").loc[t_pool, "board_name"].tolist())
