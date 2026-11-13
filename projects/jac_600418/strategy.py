"""qlib 自定义策略：江淮汽车择时。

决策规则（在 qlib 交易时间轴上执行）：
    target_weight = target_weight  if  score > threshold  且  trend_ok
                  = floor_weight   otherwise

  - score     : 模型预测分数（T 日收盘算出，T+1 日收盘撮合）
  - threshold : 阈值（= 训练集分数分布的 q 分位点）
  - trend_ok  : 趋势过滤（收盘价 > MA(N)），None 表示不启用
  - floor_weight : 底仓权重（0 = 空仓；0.5 = 保留半仓底仓）

qlib 时间轴：T 日的信号 → T+1 日收盘成交 → 持有到 T+2 日收盘，
与标签 Ref($close,-2)/Ref($close,-1)-1 完全对齐。
"""

from typing import Dict, Optional

import pandas as pd

from qlib.contrib.strategy.signal_strategy import WeightStrategyBase


class JacScoreStrategy(WeightStrategyBase):
    """分数阈值 + 趋势过滤 + 底仓 的单标的择时策略。"""

    def __init__(
        self,
        *,
        signal: Optional[pd.Series] = None,
        signal_path: Optional[str] = None,
        threshold: float = 0.0,
        target_weight: float = 1.0,
        floor_weight: float = 0.0,
        trend_ok: Optional[pd.Series] = None,
        **kwargs,
    ):
        if signal is None:
            if signal_path is None:
                raise ValueError("signal 或 signal_path 必须给一个")
            df = pd.read_csv(signal_path, parse_dates=["datetime"])
            df = df.set_index(["instrument", "datetime"])["score"].sort_index()
            signal = df
        super().__init__(signal=signal, **kwargs)
        self.threshold = float(threshold)
        self.target_weight = float(target_weight)
        self.floor_weight = float(floor_weight)
        # trend_ok: datetime 索引的 bool 序列
        self.trend_ok = trend_ok

    def _trend_ok_at(self, when: pd.Timestamp) -> bool:
        if self.trend_ok is None:
            return True
        try:
            v = self.trend_ok.asof(when)
        except Exception:  # noqa: BLE001
            return True
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return True
        return bool(v)

    def generate_target_weight_position(
        self,
        score: pd.Series,
        current,
        trade_start_time: pd.Timestamp,
        trade_end_time: pd.Timestamp,
    ) -> Dict[str, float]:
        """把分数 + 趋势过滤翻译成目标权重。score 的 index 是 instrument。"""
        target: Dict[str, float] = {}
        ok = self._trend_ok_at(pd.Timestamp(trade_start_time))
        for stock_id, s in score.items():
            if s is None or pd.isna(s):
                continue
            hit = float(s) > self.threshold and ok
            w = self.target_weight if hit else self.floor_weight
            if w > 0:
                target[stock_id] = w
        return target
