"""模型对比实验：LightGBM vs Ridge，1 日 vs 5 日标签。只用验证集选型，测试集仅作最终确认。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import config as cfg
import data_model as dm

dm.init_qlib()

df = dm.fetch_data()
train, valid, test = dm.split_data(df)
Xtr, Xva, Xte = train[cfg.FEATURE_NAMES], valid[cfg.FEATURE_NAMES], test[cfg.FEATURE_NAMES]
ytr, yva, yte = train["label"], valid["label"], test["label"]

print(f"train {len(train)} valid {len(valid)} test {len(test)}\n")


def ic(a, b):
    return float(a.corr(b))


def report(name, pred_tr, pred_va, pred_te):
    print(f"{name:28s} IC  train {ic(pred_tr, ytr):+.4f}  valid {ic(pred_va, yva):+.4f}  test {ic(pred_te, yte):+.4f}")


# ---- 1) LightGBM（当前配置）
model = dm.train_model(train, valid)
p_tr = pd.Series(model.predict(Xtr), index=train.index)
p_va = pd.Series(model.predict(Xva), index=valid.index)
p_te = pd.Series(model.predict(Xte), index=test.index)
report("LightGBM(当前)", p_tr, p_va, p_te)

# ---- 2) Ridge（标准化）
for alpha in [1.0, 10.0, 100.0, 1000.0]:
    sc = StandardScaler().fit(Xtr)
    r = Ridge(alpha=alpha).fit(sc.transform(Xtr), ytr)
    report(f"Ridge alpha={alpha:g}", pd.Series(r.predict(sc.transform(Xtr)), index=train.index),
           pd.Series(r.predict(sc.transform(Xva)), index=valid.index),
           pd.Series(r.predict(sc.transform(Xte)), index=test.index))

# ---- 3) 5 日标签版本（每周调仓的信号基础）
label5 = "Ref($close,-6)/Ref($close,-1)-1"
df5 = dm.D.features([cfg.INSTRUMENT], list(cfg.FACTORS.values()) + [label5],
                    start_time=cfg.DATA_START, end_time=cfg.DATA_END, freq="day")
df5.columns = cfg.FEATURE_NAMES + ["label"]
df5 = df5.xs(cfg.INSTRUMENT, level="instrument").sort_index().replace([np.inf, -np.inf], np.nan)
tr5 = df5.loc[cfg.TRAIN_START:cfg.TRAIN_END].dropna().iloc[:-6]
va5 = df5.loc[cfg.VALID_START:cfg.VALID_END].dropna()
te5 = df5.loc[cfg.TEST_START:cfg.TEST_END].dropna()

dtr = lgb.Dataset(tr5[cfg.FEATURE_NAMES], label=tr5["label"])
dva = lgb.Dataset(va5[cfg.FEATURE_NAMES], label=va5["label"], reference=dtr)
m5 = lgb.train(cfg.LGB_PARAMS, dtr, num_boost_round=cfg.NUM_BOOST_ROUND, valid_sets=[dva],
               callbacks=[lgb.early_stopping(cfg.EARLY_STOPPING_ROUNDS, verbose=False), lgb.log_evaluation(0)])
report("LightGBM 5日标签", pd.Series(m5.predict(tr5[cfg.FEATURE_NAMES]), index=tr5.index),
       pd.Series(m5.predict(va5[cfg.FEATURE_NAMES]), index=va5.index),
       pd.Series(m5.predict(te5[cfg.FEATURE_NAMES]), index=te5.index))

sc = StandardScaler().fit(tr5[cfg.FEATURE_NAMES])
r5 = Ridge(alpha=100.0).fit(sc.transform(tr5[cfg.FEATURE_NAMES]), tr5["label"])
report("Ridge 5日标签", pd.Series(r5.predict(sc.transform(tr5[cfg.FEATURE_NAMES])), index=tr5.index),
       pd.Series(r5.predict(sc.transform(va5[cfg.FEATURE_NAMES])), index=va5.index),
       pd.Series(r5.predict(sc.transform(te5[cfg.FEATURE_NAMES])), index=te5.index))

# ---- 4) factor 数据检查（回测撮合要用）
fac = dm.D.features([cfg.INSTRUMENT], ["$factor"], start_time="2016-01-01", end_time=cfg.DATA_END, freq="day")
f = fac.xs(cfg.INSTRUMENT, level="instrument")["$factor"]
print(f"\nfactor: n={len(f)} nan={f.isna().sum()} first={f.iloc[0]} last={f.iloc[-1]}")
print("factor nan 区间:", f[f.isna()].index[:3], "...", f[f.isna()].index[-3:] if f.isna().any() else "无")
