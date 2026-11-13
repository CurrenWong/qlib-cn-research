"""片段 3：回测 —— 模型预测 → 信号 → qlib.backtest.backtest

⚠️ Windows 必读：任何调用 D.features / handler 的脚本都要有
   `if __name__ == "__main__":` 保护（qlib 会用 joblib 起子进程）。

运行：..\\.venv\\Scripts\\python.exe snippets\\snippet_03_backtest.py
"""

import qlib
from qlib.backtest import backtest
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset import DatasetH

PROVIDER_URI = r"D:\Project\qlib\qlib_data\cn_data"


def main():
    qlib.init(provider_uri=PROVIDER_URI, region=REG_CN)

    # ---- 1. 训练模型，拿到 test 段预测 ----
    handler = Alpha158(
        instruments="csi300",
        start_time="2018-01-01",
        end_time="2020-08-01",
        fit_start_time="2018-01-01",
        fit_end_time="2019-12-31",
        infer_processors=[],
        learn_processors=[],
    )
    dataset = DatasetH(
        handler=handler,
        segments={
            "train": ("2018-01-01", "2019-12-31"),
            "valid": ("2019-01-01", "2019-12-31"),
            "test": ("2020-01-01", "2020-08-01"),
        },
    )
    model = LGBModel(loss="mse", learning_rate=0.05, num_leaves=31, max_depth=6,
                     num_boost_round=100, early_stopping_rounds=20)
    model.fit(dataset)
    pred = model.predict(dataset, segment="test")   # MultiIndex(instrument, datetime)

    # ---- 2. 信号交给 qlib ----
    # signal 必须是 MultiIndex(instrument, datetime) 的 Series；
    # qlib 内部会自动 resample 到每个交易日。
    strategy = {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": pred,
            "topk": 50,
            "n_drop": 5,
        },
    }
    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "day", "generate_portfolio_metrics": True},
    }

    portfolio_dict, indicator_dict = backtest(
        start_time="2020-01-01",
        end_time="2020-08-01",
        strategy=strategy,
        executor=executor,
        benchmark="SH000300",
        account=1_000_000,
        exchange_kwargs={
            "open_cost": 0.0005,      # 买入佣金
            "close_cost": 0.0015,     # 卖出佣金 + 印花税
            "min_cost": 5.0,          # 单笔最低佣金
            "limit_threshold": 0.095, # 涨跌停 ±9.5%
            "deal_price": "close",    # 收盘价撮合
        },
    )

    # ---- 3. 取报告 ----
    # 注意：portfolio_dict 的 key 是 "1day"（由 Freq.parse 拼出），不是 "day"
    key = next(k for k in portfolio_dict if k.endswith("day"))
    report, positions = portfolio_dict[key]
    print(f"[回测] {len(report)} 个交易日，报告列：{list(report.columns)}")
    print(report[["account", "return", "turnover", "cost", "value", "cash", "bench"]].tail(5).to_string())

    nav = report["account"] / report["account"].iloc[0]
    ret = nav.pct_change().dropna()
    years = len(ret) / 252
    ann = nav.iloc[-1] ** (1 / years) - 1
    vol = ret.std() * 252 ** 0.5
    mdd = (nav / nav.cummax() - 1).min()
    print(f"\n[绩效] 区间收益 {nav.iloc[-1]-1:+.2%} | 年化 {ann:+.2%} | 波动 {vol:.2%} | 最大回撤 {mdd:.2%}")

    # bench 列是基准（沪深300）的日收益，可直接算超额
    excess = ret - report["bench"].reindex(ret.index).fillna(0.0)
    te = excess.std() * 252 ** 0.5
    print(f"[超额] 年化超额 {((1+excess.mean())**252-1):+.2%} | 跟踪误差 {te:.2%} | "
          f"信息比率 {((1+excess.mean())**252-1)/te:.3f}")


if __name__ == "__main__":
    main()
