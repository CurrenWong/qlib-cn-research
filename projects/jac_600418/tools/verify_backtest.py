"""执行正确性校验：qlib 回测里实际持有的仓位，是否等于我们期望的信号逻辑。

期望仓位（交易日 t）：
    pos(t) = (smooth_score[t-1] > threshold) AND (close[t-1] > MA20[t-1])

qlib 时间轴：T 日信号 → T+1 日收盘成交，所以交易日 t 用的是 t-1 的信息。
实际仓位取 report['value'] / report['account']（收盘计价的股票市值占比）。

差异来源（正常）：涨跌停无法成交、停牌、整手取整。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import config as cfg
import data_model as dm
from run_backtest import run_bt, CHOICE_PATH

dm.init_qlib()
choice = json.loads(CHOICE_PATH.read_text(encoding="utf-8"))
use_ml, trend_win, floor = cfg.RULE_SPEC[choice["rule"]]
smooth = int(choice.get("smooth", 1))
q = float(choice["q"])

df = dm.fetch_data()
train, valid, test = dm.split_data(df)
close = dm.stock_close()

sc = StandardScaler().fit(train[cfg.FEATURE_NAMES])
model = Ridge(alpha=float(choice["model"].split("_a")[1])).fit(
    sc.transform(train[cfg.FEATURE_NAMES]), train["label"])
clean = df.dropna(subset=cfg.FEATURE_NAMES)
raw = pd.Series(model.predict(sc.transform(clean[cfg.FEATURE_NAMES])), index=clean.index).sort_index()
score = raw.rolling(smooth).mean().dropna() if smooth > 1 else raw
thr = float(np.quantile(score.loc[train.index], q))

# 信号条件（用信号日的信息）
sig_pass = (score > thr).astype(int)
trend_ok = (close > close.rolling(trend_win).mean()).astype(int) if trend_win else pd.Series(1, index=close.index)
expect = (sig_pass & trend_ok).astype(float)

print(f"阈值={thr:+.6f}  平滑={smooth}日  趋势窗口={trend_win}")

for label, (s, e) in {"验证集": (cfg.VALID_START, cfg.VALID_END),
                      "测试集": (cfg.TEST_START, cfg.TEST_END)}.items():
    rep, _, _ = run_bt(dm.build_signal(score), s, e, thr,
                        (close > close.rolling(trend_win).mean()).shift(1).dropna() if trend_win else None,
                        floor)
    actual_w = (rep["value"] / rep["account"]).fillna(0.0)
    # 期望：交易日 t 用 t-1 的信号
    exp = expect.shift(1).reindex(rep.index)
    exp = exp.fillna(0.0)

    held = actual_w > 0.05
    want = exp > 0.5
    agree = (held == want)
    # 看错的日子
    wrong = rep.index[~agree]
    print(f"\n[{label}] 交易日 {len(rep)} | 仓位一致率 {agree.mean():.2%} | "
          f"实际持仓天数 {int(held.sum())} | 期望持仓天数 {int(want.sum())}")
    if len(wrong):
        print(f"  不一致 {len(wrong)} 天，前 10 天明细：")
        detail = pd.DataFrame({
            "实际权重": actual_w.reindex(wrong).head(10).round(3),
            "期望": exp.reindex(wrong).head(10),
            "t-1分数": score.reindex(rep.index).shift(1).reindex(wrong).head(10).round(6),
        })
        print(detail.to_string())
    # 持仓期收益 vs 标签的一致性（粗查）
    print(f"  平均权重 {actual_w.mean():.1%} | 换手天数 {int((rep['turnover'].fillna(0) > 0).sum())}")
