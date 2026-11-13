import numpy as np
import pandas as pd

import model_core as mc

ctx = mc.load_all()
dates = ctx["dates"]
close = ctx["close"]
syms = ctx["symbols"]
last = len(dates) - 1
print("最后日期:", dates[last].date(), "close 形状", close.shape)

for s in ["SH600000", "SZ002241", "SH601857", "SH600938"]:
    j = syms.index(s)
    print(f"{s}: close[last]={close[last, j]}  close[last-1]={close[last-1, j]}  "
          f"close[last-20]={close[last-20, j]}")

mask = ctx["mask"]
pool = np.where(mask[last])[0]
print("池子", len(pool), "最后一日 close 为 NaN 的只数:", int(np.isnan(close[last, pool]).sum()))

# 逐日看 NaN 比例
for i in range(last - 8, last + 1):
    print(f"  {dates[i].date()}: NaN {int(np.isnan(close[i, pool]).sum()):3d}/{len(pool)}")

# 原始 parquet 检查
p = pd.read_parquet(r"D:\Project\qlib\projects\csi300_lgbm\data\features.parquet",
                    columns=["datetime", "symbol", "close"])
p["datetime"] = pd.to_datetime(p["datetime"])
sub = p[(p["symbol"].isin(["SZ002241", "SH601857"])) & (p["datetime"] >= "2026-10-20")]
print(sub.to_string(index=False))
