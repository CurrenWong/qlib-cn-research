import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

p = _ROOT + r"/projects/csi300_lgbm/data/index_close.parquet"
idx = pd.read_parquet(p)
print(type(idx), idx.shape, idx.columns.tolist())
print(idx.head(3))
print(idx.tail(3))
print("NaN:", idx["close"].isna().sum(), "of", len(idx))
print("index dtype:", idx.index.dtype, idx.index[:2].tolist(), idx.index[-2:].tolist())

feat = pd.read_parquet(_ROOT + r"/projects/csi300_lgbm/data/features.parquet",
                       columns=["datetime"])
d = pd.to_datetime(feat["datetime"].unique())
print("features dates:", d.min(), d.max(), len(d))
s = idx["close"].copy()
s.index = pd.to_datetime(s.index)
r = s.reindex(pd.DatetimeIndex(d))
print("reindex 后 NaN:", int(r.isna().sum()), "of", len(r))
