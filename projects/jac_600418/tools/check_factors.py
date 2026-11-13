"""快速验证：因子表达式是否被 qlib 解析器接受，数据是否干净。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import config as cfg
import data_model as dm

dm.init_qlib()
df = dm.fetch_data()
print("shape:", df.shape)
print("nan count per col:")
print(df.isna().sum().to_string())

clean = df.dropna()
print("\nclean rows:", len(clean), clean.index[0].date(), "->", clean.index[-1].date())
print("\nlabel describe:")
print(clean["label"].describe().to_string())
print("\nfeature corr with label (top 8):")
corr = clean[cfg.FEATURE_NAMES].corrwith(clean["label"]).abs().sort_values(ascending=False)
print(corr.head(8).to_string())

train, valid, test = dm.split_data(df)
print(f"\ntrain {train.index[0].date()}->{train.index[-1].date()} n={len(train)}")
print(f"valid {valid.index[0].date()}->{valid.index[-1].date()} n={len(valid)}")
print(f"test  {test.index[0].date()}->{test.index[-1].date()} n={len(test)}")
