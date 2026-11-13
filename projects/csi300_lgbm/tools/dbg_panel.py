import pandas as pd
from pathlib import Path

p = pd.read_parquet(r"D:\Project\qlib\projects\csi300_lgbm\data\panel.parquet")
print("panel shape", p.shape)
idx = p.index
dup = idx.duplicated(keep=False)
print("重复 (date,symbol) 行数:", int(dup.sum()))
if dup.any():
    d = idx[dup]
    print(d.value_counts().head(10))
    print(d.sort_values()[:12].tolist())
