"""看一下 csi300_lgbm 已有的数据面板结构，决定 trend_combo 能复用多少。"""

import pandas as pd

P = r"D:\Project\qlib\projects\csi300_lgbm\data"

for name in ["panel.parquet", "features.parquet"]:
    d = pd.read_parquet(f"{P}\\{name}")
    print("=" * 90)
    print(name, d.shape)
    print("  cols:", list(d.columns))
    print(d.head(3).to_string()[:1500])
    for c in ("date", "symbol", "datetime", "instrument"):
        if c in d.columns:
            print(f"  {c}: {d[c].min()} ~ {d[c].max()}, nunique={d[c].nunique()}")

idx = pd.read_parquet(f"{P}\\index_close.parquet")
print("=" * 90)
print("index_close", idx.shape, list(idx.columns)[:10])
print(idx.head(3).to_string()[:600])
