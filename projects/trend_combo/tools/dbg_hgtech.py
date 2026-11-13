import pandas as pd

p = r"D:\Project\qlib\projects\trend_combo\data\scores.parquet"
d = pd.read_parquet(p, columns=["datetime", "symbol", "close", "mom_20", "ma_dist_20",
                                 "vol_20", "rsi_14", "price_score", "fund_score"])
s = d[d["symbol"] == "SZ000988"]
print("rows", len(s))
print(s.tail(4).to_string(index=False))
print("non-nan close:", s["close"].notna().sum(), "mom_20:", s["mom_20"].notna().sum(),
      "price_score:", s["price_score"].notna().sum())
print("date range:", s["datetime"].min(), "->", s["datetime"].max())
print("z_mom_20 non-nan:", d[d["symbol"] == "SZ000988"]["z_mom_20"].notna().sum())
