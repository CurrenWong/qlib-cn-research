"""验证补数效果：新 features/panel 里 10-30 有收盘价的只数（补之前是 299）。"""

from pathlib import Path

import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

PROJ = Path(_ROOT + r"/projects/csi300_lgbm")
d = pd.read_parquet(PROJ / "data" / "panel.parquet")
if "datetime" in d.columns:
    d["datetime"] = pd.to_datetime(d["datetime"])
else:
    d = d.reset_index().rename(columns={d.index.name or "index": "datetime"})
    d["datetime"] = pd.to_datetime(d["datetime"])
last = d["datetime"].max()
sub = d[d["datetime"] == last]
have = sub["$close"].notna()
print("面板末日期", last.date())
print("宇宙", sub["symbol"].nunique(), "| 当天有收盘价", int(have.sum()))
miss = sub.loc[~have, "symbol"].tolist()
print("仍缺价的只数:", len(miss))
if miss:
    hist = (d[d["symbol"].isin(miss) & d["$close"].notna()]
            .groupby("symbol")["datetime"].max().sort_values())
    print(hist.head(30).to_string())
