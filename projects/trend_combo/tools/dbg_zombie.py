"""检查 trend_combo 面板里的「僵尸股」：价格长期冻结（停牌/退市）却仍在 637 只宇宙里。

判定：最近 60 天内收盘价完全不变 → 视为停牌/退市。
这类票会污染因子（动量 z 值爆表 → winsorize 限幅），也会污染选股。
"""

from pathlib import Path

import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

PROJ = Path(__file__).resolve().parent.parent
LGBM = Path(_ROOT + r"/projects/csi300_lgbm")

COLS = ["datetime", "symbol", "close", "volume", "price_score",
        "fund_score", "event_score", "board_name"]

sc = pd.read_parquet(PROJ / "data" / "scores.parquet", columns=COLS)
sc["datetime"] = pd.to_datetime(sc["datetime"])
last = sc["datetime"].max()
day = sc[sc["datetime"] == last].copy()
print("截面", last.date(), len(day), "只")

cutoff = last - pd.Timedelta(days=60)
recent = sc[sc["datetime"] > cutoff]
g = recent.groupby("symbol")["close"].agg(["nunique", "count", "std"])
stale = g[(g["nunique"] <= 1) | (g["std"].fillna(0) == 0)]
print("最近 60 天内价格完全冻结的：", len(stale), "只")

z = day[day["symbol"].isin(stale.index)]
cols = ["symbol", "close", "price_score", "fund_score", "event_score", "board_name"]
print("\n落在 10-30 截面上的僵尸股：", len(z))
print(z[cols].sort_values("price_score", ascending=False).to_string(index=False))

pmax = day["price_score"].max()
print("\nprice_score 最大值:", round(float(pmax), 4),
      "并列只数:", int((day["price_score"] == pmax).sum()))
if len(stale):
    hit = day.set_index("symbol").loc[stale.index, "price_score"]
    print("僵尸股里打到上限的只数:", int((hit == pmax).sum()), "/", len(hit))

print("\n=== 与 csi300_lgbm 的宇宙对比 ===")
uni = LGBM / "universe_latest.txt"
if uni.exists():
    lines = [l.strip() for l in uni.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("universe_latest.txt:", len(lines), "行, 前 3 行", lines[:3])
    inter = set(lines) & set(day["symbol"])
    print("与 637 只面板交集:", len(inter))
    print("僵尸股里也在 csi300 宇宙的:", sorted(set(stale.index) & inter))
else:
    print("universe_latest.txt 不存在")
