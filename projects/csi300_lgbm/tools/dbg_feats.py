import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

p = pd.read_parquet(_ROOT + r"/projects/csi300_lgbm/data/panel.parquet")
close = p["$close"].unstack(level=1).sort_index().astype(float)
volume = p["$volume"].unstack(level=1).sort_index().astype(float)
idx = pd.read_parquet(_ROOT + r"/projects/csi300_lgbm/data/index_close.parquet")["close"]
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
