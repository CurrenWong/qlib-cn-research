"""江淮汽车（SH600418）择时策略 —— 全局配置。

所有路径、样本切分、因子、模型超参、交易成本都集中在这里，方便复现与调参。
"""

from pathlib import Path

import os

ROOT = Path(__file__).resolve().parent
# 结果目录可用环境变量切换，避免新旧数据的结果混在一起
RESULTS = Path(os.environ.get("JAC_RESULTS", str(ROOT / "results")))
RESULTS.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 数据
# 数据源可用环境变量切换：
#   旧数据（2020-09 快照）  : 不设 JAC_PROVIDER，用默认值
#   新数据（2026-10 日更版）: JAC_PROVIDER=D:\Project\qlib\qlib_data\cn_data_2026
PROVIDER_URI = os.environ.get("JAC_PROVIDER", r"D:\Project\qlib\qlib_data\cn_data")
REGION = "cn"

INSTRUMENT = "SH600418"   # 江淮汽车
BENCHMARK = "SH000300"    # 沪深300

# 数据总区间
DATA_START = "2007-01-01"
DATA_END = os.environ.get("JAC_DATA_END", "2020-12-31")

# ---------------------------------------------------------------- 样本切分
# 训练集：训练模型（walk-forward 的起点也由它决定）
# 三种切分方案见 README「样本切分」一节，可用环境变量覆盖：
#   A（主方案）: TRAIN 2007~2018 / VALID 2019 / TEST 2020-01-01~2026-10-26
#   B（长训练）: TRAIN 2007~2021 / VALID 2022 / TEST 2023-01-01~2026-10-26
#   C（中训练）: TRAIN 2007~2019 / VALID 2020 / TEST 2021-01-01~2026-10-26
TRAIN_START = os.environ.get("JAC_TRAIN_START", "2008-01-01")
TRAIN_END = os.environ.get("JAC_TRAIN_END", "2016-12-31")
# 验证集：模型选型 + 早停 + 选阈值（选完冻结，不再改）
VALID_START = os.environ.get("JAC_VALID_START", "2017-01-01")
VALID_END = os.environ.get("JAC_VALID_END", "2018-12-31")
# 测试集：完全样本外，只跑一次
# 注：回测结束日不能取日历最后一天（qlib get_step_time 会越界）
#   旧数据日历末日 2020-09-25 → 测试集结束 2020-09-24
#   新数据日历末日 2026-10-27 → 可用 JAC_TEST_END=2026-10-26
TEST_START = os.environ.get("JAC_TEST_START", "2019-01-01")
TEST_END = os.environ.get("JAC_TEST_END", "2020-09-24")

# 标签用 Ref($close,-2)/Ref($close,-1)，会吃掉边界后 2 个交易日的数据，
# 所以训练集末尾砍掉 2 行，避免标签把验证期价格泄漏进训练。
LABEL_PURGE_BARS = 2

# ---------------------------------------------------------------- 因子
# 全部用 qlib 表达式引擎计算（只用历史数据，无未来函数）
FACTORS = {
    # 动量 / 短期反转
    "mom_5": "$close/Ref($close,5)-1",
    "mom_10": "$close/Ref($close,10)-1",
    "mom_20": "$close/Ref($close,20)-1",
    "mom_60": "$close/Ref($close,60)-1",
    "rev_1": "Ref($close,1)/$close-1",
    # 均线偏离
    "ma_dev_5": "$close/Mean($close,5)-1",
    "ma_dev_10": "$close/Mean($close,10)-1",
    "ma_dev_20": "$close/Mean($close,20)-1",
    "ma_dev_60": "$close/Mean($close,60)-1",
    "ma_spread": "Mean($close,5)/Mean($close,20)-1",
    # 波动 / 振幅
    "vol_20": "Std($close,20)/Mean($close,20)",
    "vol_60": "Std($close,60)/Mean($close,60)",
    "atr_14": "Mean(($high-$low)/$close,14)",
    # 量价
    "vol_z_5": "$volume/Mean($volume,5)-1",
    "vol_z_20": "$volume/Mean($volume,20)-1",
    "vol_trend": "Mean($volume,5)/Mean($volume,20)-1",
    "px_vol_corr": "Corr($close,$volume,20)",
    # 日内形态 / 价格位置
    "price_pos_20": "($close-Min($low,20))/(Max($high,20)-Min($low,20))",
    "intraday": "($close-$open)/$open",
    "gap": "$open/Ref($close,1)-1",
    "dist_high_250": "$close/Max($high,250)-1",
}

FEATURE_NAMES = list(FACTORS.keys())

# 标签：t 日信号 → t+1 日收盘买入 → 持有到 t+2 日收盘的收益
LABEL = "Ref($close,-2)/Ref($close,-1)-1"

# ---------------------------------------------------------------- 模型
LGB_PARAMS = {
    "objective": "regression",
    "metric": "l2",
    "learning_rate": 0.02,
    "num_leaves": 7,
    "max_depth": 3,
    "min_child_samples": 60,
    "feature_fraction": 0.6,
    "bagging_fraction": 0.7,
    "bagging_freq": 1,
    "lambda_l1": 0.5,
    "lambda_l2": 20.0,
    "verbosity": -1,
    "seed": 42,
    "num_threads": 8,
}
NUM_BOOST_ROUND = 1000
EARLY_STOPPING_ROUNDS = 50

# 候选模型（最终用验证集 IC 显著性挑一个，测试集不参与选型）
RIDGE_ALPHAS = [1.0, 10.0, 100.0]

# 阈值候选：训练集分数的分位点（+ 永远满仓）
THRESHOLD_QUANTILES = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

# 阈值选择标准：相对沪深300 的信息比率（只在验证集内计算）
THRESHOLD_SELECT_BY = "IR_vs_CSI300"

# 规则规格：规则名 -> (是否用模型分数, 趋势过滤窗口(None=关闭), 底仓权重)
RULE_SPEC = {
    "ML": (True, None, 0.0),
    "ML&MA20": (True, 20, 0.0),
    "ML&MA60": (True, 60, 0.0),
    "MA60": (False, 60, 0.0),
    "ML底仓": (True, None, 0.5),
    "ML&MA20底仓": (True, 20, 0.5),
    "MA20底仓": (False, 20, 0.5),
    # 基线：不择时，只买持有
    "全仓持有": (False, None, 1.0),
    "MA20趋势": (False, 20, 0.0),
    "MA60趋势": (False, 60, 0.0),
}

# ---------------------------------------------------------------- 交易成本
ACCOUNT = 1_000_000.0
OPEN_COST = 0.0005     # 买入佣金
CLOSE_COST = 0.0015    # 卖出佣金 + 印花税
MIN_COST = 5.0
LIMIT_THRESHOLD = 0.095  # 主板 ±10%
DEAL_PRICE = "close"   # 以收盘价撮合（信号在 T 日生成，T+1 日收盘成交）
RISK_FREE = 0.02       # 年化无风险利率，用于 Sharpe
TRADING_DAYS = 252
