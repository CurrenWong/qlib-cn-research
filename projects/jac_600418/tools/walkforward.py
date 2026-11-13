"""Walk-forward 策略选型。

协议（严格无泄漏）：
  - 折内训练只用折前数据，折内验证只用折内数据
  - 候选集合 = 模型族 × 规则 × 阈值，先验给定
  - 每个折算一次「相对沪深300 的信息比率」，跨折取平均
  - 全部折的年份 ≤ 2018，测试期(2019~2020) 完全不参与

输出：results/strategy_choice.json  （模型、规则、阈值）
"""

import itertools
import json
import os
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

OUT = cfg.RESULTS / "strategy_choice.json"

# ------------------------------------------------------------------ 数据
df = dm.fetch_data()
close = dm.stock_close()
bench = dm.bench_close()
COST = cfg.OPEN_COST + cfg.CLOSE_COST

MA_WINDOWS = (20, 60)
# 规则：{名字: (是否用模型分数, 趋势窗口(None=不用), 底仓)}
# 基线规则（全仓持有 / 纯趋势）必须留在候选池里，
# 否则选型没有"干脆别择时"这个退路，容易选出只在特定 regime 有效的高换手择时。
RULES = {
    "ML": (True, None, 0.0),
    "ML&MA20": (True, 20, 0.0),
    "ML&MA60": (True, 60, 0.0),
    "ML底仓": (True, None, 0.5),
    "ML&MA20底仓": (True, 20, 0.5),
    "MA20底仓": (False, 20, 0.5),
    "全仓持有": (False, None, 1.0),
    "MA20趋势": (False, 20, 0.0),
    "MA60趋势": (False, 60, 0.0),
}

# walk-forward 折：验证年份，默认为 2013~2018，可用 JAC_FOLDS 覆盖（逗号分隔）
# 每折训练窗口 = [max(TRAIN_START, 折年-9), 折年-1] 的滚动 9 年，验证 = 折年内
FOLD_YEARS = [int(x) for x in os.environ.get("JAC_FOLDS", "2013,2014,2015,2016,2017,2018").split(",")]


def fit_model(name, tr):
    """在 tr 上拟合，返回 predict 函数。"""
    X, y = tr[cfg.FEATURE_NAMES], tr["label"]
    if name.startswith("Ridge"):
        alpha = float(name.split("_a")[1])
        sc = StandardScaler().fit(X)
        r = Ridge(alpha=alpha).fit(sc.transform(X), y)
        return lambda D: r.predict(sc.transform(D[cfg.FEATURE_NAMES]))
    dtr = lgb.Dataset(X, label=y)
    m = lgb.train(cfg.LGB_PARAMS, dtr, num_boost_round=cfg.NUM_BOOST_ROUND,
                  callbacks=[lgb.log_evaluation(0)])
    return lambda D: m.predict(D[cfg.FEATURE_NAMES])


def simulate(pos, label):
    pos = pos.reindex(label.index).fillna(0.0)
    turn = pos.diff().abs().fillna(pos.abs())
    r = pos * label - turn * COST
    return (1 + r).cumprod()


def ir_vs_bench(nav, bser):
    nav = nav.dropna()
    b = bser.reindex(nav.index).ffill()
    b = b / b.iloc[0]
    d = pd.concat([nav.pct_change().rename("s"), b.pct_change().rename("b")], axis=1).dropna()
    ex = d["s"] - d["b"]
    if ex.std(ddof=1) == 0:
        return np.nan
    te = ex.std(ddof=1) * np.sqrt(cfg.TRADING_DAYS)
    return ((1 + ex.mean()) ** cfg.TRADING_DAYS - 1) / te


def ann_ret(nav):
    nav = nav.dropna()
    n = len(nav)
    return (nav.iloc[-1] / nav.iloc[0]) ** (cfg.TRADING_DAYS / n) - 1


# ------------------------------------------------------------------ 逐折评估
rows = []
for yr in FOLD_YEARS:
    # 训练窗口：从 max(全局训练起点, 折年-9) 到折年前一年
    tr_year = max(int(cfg.TRAIN_START[:4]), yr - 9)
    tr = df.loc[f"{tr_year}-01-01":f"{yr-1}-12-31"].dropna().iloc[:-cfg.LABEL_PURGE_BARS]
    va = df.loc[f"{yr}-01-01":f"{yr}-12-31"].dropna()
    if len(va) < 50:
        continue
    ma = {20: close.rolling(20).mean(), 60: close.rolling(60).mean()}
    bser = bench.reindex(va.index).ffill()

    for mname in ["Ridge_a1", "Ridge_a10", "Ridge_a100", "LightGBM"]:
        pred = fit_model(mname, tr)
        # 阈值用【训练集】分数的分位点定义，保证跨折可比（绝对阈值会随折漂移）
        tr_pred = pred(tr)
        tr_score_raw = pd.Series(tr_pred, index=tr.index)
        va_score_raw = pd.Series(pred(va), index=va.index)
        for smooth in [1, 5]:
            # smooth=1 用原始分数；smooth=5 用 5 日移动平均，降低换手与来回打脸
            if smooth == 1:
                tr_score, va_score = tr_score_raw, va_score_raw
            else:
                tr_score = tr_score_raw.rolling(smooth).mean().dropna()
                va_score = va_score_raw.rolling(smooth).mean().reindex(va.index)
            for rule, (use_ml, tw, floor) in RULES.items():
                trend = (close > ma[tw]) if tw else None
                for q in cfg.THRESHOLD_QUANTILES:
                    thr = float(np.quantile(tr_score, q))
                    ok = trend.reindex(va.index).fillna(False) if trend is not None else True
                    if use_ml:
                        hit = (va_score > thr) & ok
                    else:
                        hit = pd.Series(ok, index=va.index)
                    hit = hit.fillna(False)
                    pos = hit.astype(float) * (1.0 - floor) + floor
                    nav = simulate(pos, va["label"])
                    rows.append({
                        "fold": yr, "model": mname, "rule": rule, "q": q,
                        "smooth": smooth, "threshold": thr, "floor": floor,
                        "IR": ir_vs_bench(nav, bser),
                        "ann": ann_ret(nav), "expo": pos.mean(),
                        "n": len(va),
                    })
    print(f"[fold {yr}] train<{yr} n={len(tr)} valid n={len(va)} 完成", flush=True)

res = pd.DataFrame(rows)
res.to_csv(cfg.RESULTS / "walkforward_folds.csv", index=False, encoding="utf-8-sig")

# 跨折汇总
agg = res.groupby(["model", "rule", "q", "smooth"]).agg(
    IR_mean=("IR", "mean"), IR_std=("IR", "std"), IR_min=("IR", "min"),
    ann_mean=("ann", "mean"), expo_mean=("expo", "mean"), folds=("IR", "count"),
    folds_pos=("IR", lambda x: int((x > 0).sum())),
).reset_index()
agg = agg.sort_values(["IR_mean", "folds_pos"], ascending=False)

print("\n" + "=" * 110)
print("跨折汇总 Top15（按平均 IR 排序）")
print("=" * 110)
print(agg.head(15).to_string(index=False))

best = agg.iloc[0]
choice = {
    "model": best["model"],
    "rule": best["rule"],
    "q": float(best["q"]),
    "smooth": int(best["smooth"]),
    "IR_mean_walkforward": float(best["IR_mean"]),
    "IR_min_walkforward": float(best["IR_min"]),
    "folds": int(best["folds"]),
    "folds_positive": int(best["folds_pos"]),
    "avg_exposure": float(best["expo_mean"]),
    "selection": (f"walk-forward {FOLD_YEARS[0]}-{FOLD_YEARS[-1]}（每折训练窗口从 {cfg.TRAIN_START[:4]} 年起、滚动9年），"
                  f"阈值=训练集分数分位点，目标=相对沪深300的信息比率均值"),
}
OUT.write_text(json.dumps(choice, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n>>> 选定：{choice}")
print(f">>> 写入 {OUT}")

det = res[(res["model"] == best["model"]) & (res["rule"] == best["rule"])
          & (res["q"] == best["q"]) & (res["smooth"] == best["smooth"])]
print("\n选定组合逐折明细：")
print(det.to_string(index=False))
