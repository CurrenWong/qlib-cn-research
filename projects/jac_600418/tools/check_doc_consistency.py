"""最终一致性检查：README 里引用的关键数字，必须与 results/ 的实际产物对得上。

防止改了代码/参数后忘记同步文档。
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

import config as cfg

ROOT = Path(__file__).resolve().parents[1]
doc = (ROOT / "README.md").read_text(encoding="utf-8")
metrics = pd.read_csv(cfg.RESULTS / "metrics.csv", encoding="utf-8-sig")
choice = json.loads((cfg.RESULTS / "strategy_choice.json").read_text(encoding="utf-8"))
fails = []


def get(period, name, col):
    row = metrics[(metrics["区间"] == period) & (metrics["标的"] == name)]
    return float(row.iloc[0][col])


# 1) 文档必须声明的关键结论数字
checks = [
    ("验证集", "策略（择时）", "区间收益", 13.76),
    ("验证集", "策略（择时）", "信息比率", 0.571),
    ("验证集", "沪深300", "区间收益", -9.92),
    ("验证集", "买入持有江淮汽车", "区间收益", -57.75),
    ("测试集", "策略（择时）", "区间收益", -18.96),
    ("测试集", "策略（择时）", "信息比率", -0.898),
    ("测试集", "沪深300", "区间收益", 53.66),
    ("测试集", "买入持有江淮汽车", "区间收益", 53.00),
]
for period, name, col, expect in checks:
    actual = get(period, name, col)
    if col == "区间收益":          # metrics.csv 里是小数，文档里是百分数
        actual *= 100
    if abs(actual - expect) > 0.005:
        fails.append(f"metrics.csv {period}/{name}/{col} = {actual:.4f}，文档写 {expect}")

# 2) 文档里必须出现的字符串（关键结论与选型结果）
must_have = [
    choice["rule"], f"q={choice['q']}", f"平滑{choice['smooth']}",
    "Ridge", "α=100", "MA20", "沪深300", "验证集", "测试集", "walk-forward",
    "98.97%", "98.58%", "+0.237", "-0.197",
]
for s in must_have:
    if s not in doc:
        fails.append(f"README 缺少关键字：{s}")

# 3) 关键产物必须存在
for f in ["README.md", "config.py", "data_model.py", "strategy.py", "run_backtest.py",
          "tools/walkforward.py", "tools/verify_backtest.py", "tools/attribution.py",
          "results/metrics.csv", "results/strategy_choice.json", "results/walkforward_folds.csv",
          "results/nav_valid.png", "results/nav_test.png", "results/predictions.csv",
          "results/feature_weights.csv", "results/summary.json"]:
    if not (ROOT / f).exists():
        fails.append(f"缺少文件：{f}")

# 4) 文档引用的图片路径要真实存在
for m in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", doc):
    if not (ROOT / m).exists():
        fails.append(f"README 引用的图片不存在：{m}")

print("=" * 70)
if fails:
    print("❌ 一致性检查未通过：")
    for f in fails:
        print("   -", f)
    sys.exit(1)
print("✅ 一致性检查通过：文档数字 / 选型结果 / 产物文件 / 图片路径 全部对得上")
print(f"   策略: {choice['model']} | {choice['rule']} | q={choice['q']} | smooth={choice['smooth']}")
print(f"   walk-forward IR均值 {choice['IR_mean_walkforward']:.3f}，{choice['folds_positive']}/{choice['folds']} 折为正")
