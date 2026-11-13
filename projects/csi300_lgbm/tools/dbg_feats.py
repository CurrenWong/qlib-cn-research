import numpy as np
import pandas as pd

p = pd.read_parquet(r"D:\Project\qlib\projects\csi300_lgbm\data\panel.parquet")
close = p["$close"].unstack(level=1).sort_index().astype(float)
volume = p["$volume"].unstack(level=1).sort_index().astype(float)
idx = pd.read_parquet(r"D:\Project\qlib\projects\csi300_lgbm\data\index_close.parquet")["close"]
idx.index = pd.to_datetime(idx.index)
ret = close.pct_change()
idx_ret = idx.pct_change().reindex(close.index).fillna(0.0)

cov60 = ret.rolling(60).cov(idx_ret)
print("cov60", cov60.shape, type(cov60.columns))
var60 = idx_ret.rolling(60).var()
beta = cov60.div(var60, axis=0)
print("beta", beta.shape)
a = (close / close.shift(20) - 1)
print("a", a.shape)
b = beta * (idx_close := (idx / idx.shift(20) - 1))
print("b", b.shape)
amihud = (ret.abs() / volume.replace(0, np.nan))
print("amihud", amihud.shape)
