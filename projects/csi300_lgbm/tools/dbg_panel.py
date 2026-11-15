import pandas as pd
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

p = pd.read_parquet(_ROOT + r"/projects/csi300_lgbm/data/panel.parquet")
print("panel shape", p.shape)
idx = p.index
dup = idx.duplicated(keep=False)
print("重复 (date,symbol) 行数:", int(dup.sum()))
if dup.any():
    d = idx[dup]
    print(d.value_counts().head(10))
    print(d.sort_values()[:12].tolist())
