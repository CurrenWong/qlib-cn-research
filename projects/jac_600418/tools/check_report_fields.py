"""核对 qlib report 字段口径：cost / total_cost / turnover / total_turnover。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config as cfg
import data_model as dm
from run_backtest import run_bt, CHOICE_PATH
import json

dm.init_qlib()
choice = json.loads(CHOICE_PATH.read_text(encoding="utf-8"))
use_ml, trend_win, floor = cfg.RULE_SPEC[choice["rule"]]

df = dm.fetch_data()
train, valid, test = dm.split_data(df)
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sc = StandardScaler().fit(train[cfg.FEATURE_NAMES])
m = Ridge(alpha=10.0).fit(sc.transform(train[cfg.FEATURE_NAMES]), train["label"])
clean = df.dropna(subset=cfg.FEATURE_NAMES)
score = pd.Series(m.predict(sc.transform(clean[cfg.FEATURE_NAMES])), index=clean.index).sort_index()
signal = dm.build_signal(score)
thr = float(np.quantile(score.loc[train.index], float(choice["q"])))
close = dm.stock_close()
trend = (close > close.rolling(trend_win).mean()).shift(1).dropna() if trend_win else None

rep, _, _ = run_bt(signal, cfg.TEST_START, cfg.TEST_END, thr, trend, floor)
pd.set_option("display.width", 200)
print(rep[["account", "return", "turnover", "total_turnover", "cost", "total_cost", "value", "cash"]].head(8).to_string())
print("...")
print(rep[["account", "return", "turnover", "total_turnover", "cost", "total_cost", "value", "cash"]].tail(5).to_string())
print("\n列含义核对：")
print("  cost 列合计 =", rep["cost"].sum(), " | total_cost 末值 =", rep["total_cost"].iloc[-1])
print("  turnover 合计 =", rep["turnover"].sum(), " | total_turnover 末值 =", rep["total_turnover"].iloc[-1])
print("  非零 turnover 天数 =", int((rep['turnover'].fillna(0) > 0).sum()))
print("  初始资金 =", cfg.ACCOUNT, " 末值 =", rep['account'].iloc[-1])
