"""看 walk-forward 各变体的底仓版本表现（判断是否值得用更高参与度换相近 IR）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

import config as cfg

res = pd.read_csv(cfg.RESULTS / "walkforward_folds.csv", encoding="utf-8-sig")
agg = res.groupby(["model", "rule", "q"]).agg(
    IR_mean=("IR", "mean"), IR_std=("IR", "std"), IR_min=("IR", "min"),
    ann_mean=("ann", "mean"), expo_mean=("expo", "mean"),
    folds_pos=("IR", lambda x: int((x > 0).sum())),
).reset_index()

print("=== 含底仓变体的 Top12 ===")
print(agg.sort_values("IR_mean", ascending=False).head(12).to_string(index=False))

print("\n=== Ridge_a10 + ML&MA20 全部 q ===")
sub = agg[(agg["model"] == "Ridge_a10") & (agg["rule"].isin(["ML&MA20", "ML&MA20底仓"]))]
print(sub.to_string(index=False))

print("\n=== 选定组合在各折的仓位与 IR ===")
det = res[(res["model"] == "Ridge_a10") & (res["rule"] == "ML&MA20") & (res["q"] == 0.3)]
print(det.to_string(index=False))
