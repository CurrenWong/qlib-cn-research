"""取数、训练、预测。

数据链路：qlib 表达式引擎（D.features）→ pandas → LightGBM。
"""

from typing import Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd

import config as cfg
from qlib.constant import REG_CN
from qlib.data import D


def init_qlib() -> None:
    import qlib

    qlib.init(provider_uri=cfg.PROVIDER_URI, region=REG_CN)


def fetch_data() -> pd.DataFrame:
    """抓取因子 + 标签。返回 datetime 索引的 DataFrame。"""
    exprs = list(cfg.FACTORS.values()) + [cfg.LABEL]
    df = D.features(
        [cfg.INSTRUMENT],
        exprs,
        start_time=cfg.DATA_START,
        end_time=cfg.DATA_END,
        freq="day",
    )
    df.columns = cfg.FEATURE_NAMES + ["label"]
    df = df.xs(cfg.INSTRUMENT, level="instrument").sort_index()
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def split_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """切成训练 / 验证 / 测试三段，并清除标签跨段泄漏。"""
    train = df.loc[cfg.TRAIN_START : cfg.TRAIN_END].dropna()
    # 标签 Ref(-2)/Ref(-1) 会用到区间外 2 天的价格，砍掉末尾几行防止泄漏
    train = train.iloc[: -cfg.LABEL_PURGE_BARS]
    valid = df.loc[cfg.VALID_START : cfg.VALID_END].dropna()
    test = df.loc[cfg.TEST_START : cfg.TEST_END].dropna()
    return train, valid, test


def train_model(train: pd.DataFrame, valid: pd.DataFrame) -> lgb.Booster:
    """用训练集拟合，验证集做早停。"""
    dtrain = lgb.Dataset(train[cfg.FEATURE_NAMES], label=train["label"])
    dvalid = lgb.Dataset(valid[cfg.FEATURE_NAMES], label=valid["label"], reference=dtrain)
    model = lgb.train(
        cfg.LGB_PARAMS,
        dtrain,
        num_boost_round=cfg.NUM_BOOST_ROUND,
        valid_sets=[dvalid],
        valid_names=["valid"],
        callbacks=[
            lgb.early_stopping(cfg.EARLY_STOPPING_ROUNDS, verbose=False),
            lgb.log_evaluation(100),
        ],
    )
    return model


def predict(model: lgb.Booster, df: pd.DataFrame) -> pd.Series:
    """对全部可用样本打，返回 datetime 索引的分数序列。"""
    clean = df.dropna(subset=cfg.FEATURE_NAMES)
    score = pd.Series(model.predict(clean[cfg.FEATURE_NAMES]), index=clean.index, name="score")
    return score.sort_index()


def build_signal(score: pd.Series) -> pd.Series:
    """转成 qlib 信号需要的 MultiIndex(instrument, datetime)。"""
    sig = pd.DataFrame(
        {"instrument": cfg.INSTRUMENT, "datetime": score.index, "score": score.values}
    ).set_index(["instrument", "datetime"])["score"]
    return sig.sort_index()


def bench_close(start: str = cfg.DATA_START, end: str = cfg.DATA_END) -> pd.Series:
    """沪深300 收盘价（基准）。"""
    df = D.features([cfg.BENCHMARK], ["$close"], start_time=start, end_time=end, freq="day")
    return df.xs(cfg.BENCHMARK, level="instrument")["$close"].sort_index()


def stock_close(start: str = cfg.DATA_START, end: str = cfg.DATA_END) -> pd.Series:
    """江淮汽车收盘价（买入持有基准）。"""
    df = D.features([cfg.INSTRUMENT], ["$close"], start_time=start, end_time=end, freq="day")
    return df.xs(cfg.INSTRUMENT, level="instrument")["$close"].sort_index()


# ------------------------------------------------------------------ 候选模型
def fit_candidates(train: pd.DataFrame, valid: pd.DataFrame) -> dict:
    """候选模型集合：Ridge（多组正则强度）+ LightGBM。

    单只股票样本量小（训练集 ~1700 行），树模型极易过拟合，
    所以把线性模型一并放进候选池，用验证集比选。
    """
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    cands: dict = {}
    for alpha in cfg.RIDGE_ALPHAS:
        sc = StandardScaler().fit(train[cfg.FEATURE_NAMES])
        r = Ridge(alpha=alpha).fit(sc.transform(train[cfg.FEATURE_NAMES]), train["label"])
        cands[f"Ridge(alpha={alpha:g})"] = {
            "model": r,
            "scaler": sc,
            "predict": lambda X, r=r, sc=sc: r.predict(sc.transform(X)),
        }
    m = train_model(train, valid)
    cands["LightGBM"] = {
        "model": m,
        "scaler": None,
        "predict": lambda X, m=m: m.predict(X),
    }
    return cands


def ic_stats(pred: pd.Series, label: pd.Series) -> dict:
    """IC 与其显著性 t 值：t = r*sqrt((n-2)/(1-r^2))。"""
    n = len(pred)
    r = float(pred.corr(label))
    t = r * np.sqrt((n - 2) / (1 - r ** 2)) if abs(r) < 1 else np.nan
    return {"IC": r, "IC_t": t, "n": n}


def select_model(candidates: dict, train: pd.DataFrame, valid: pd.DataFrame):
    """按验证集 IC 显著性选模型；训练集 IC 一并记录，用于观察过拟合。"""
    rows = []
    for name, c in candidates.items():
        pv = pd.Series(c["predict"](valid[cfg.FEATURE_NAMES]), index=valid.index)
        pt = pd.Series(c["predict"](train[cfg.FEATURE_NAMES]), index=train.index)
        sv = ic_stats(pv, valid["label"])
        st = ic_stats(pt, train["label"])
        rows.append(
            {
                "model": name,
                "IC_valid": sv["IC"],
                "IC_t_valid": sv["IC_t"],
                "IC_train": st["IC"],
                "n_valid": sv["n"],
                "n_train": st["n"],
            }
        )
    table = pd.DataFrame(rows).sort_values("IC_t_valid", ascending=False)
    best = table.iloc[0]["model"]
    return best, candidates[best], table

