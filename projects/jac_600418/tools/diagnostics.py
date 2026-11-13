"""生成策略文档所需的诊断数据：基线对比、季度归因、回撤区间。"""

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
bench = dm.bench_close()

sc = StandardScaler().fit(train[cfg.FEATURE_NAMES])
model = Ridge(alpha=float(choice["model"].split("_a")[1])).fit(
    sc.transform(train[cfg.FEATURE_NAMES]), train["label"])
clean = df.dropna(subset=cfg.FEATURE_NAMES)
raw = pd.Series(model.predict(sc.transform(clean[cfg.FEATURE_NAMES])), index=clean.index).sort_index()
score = raw.rolling(smooth).mean().dropna() if smooth > 1 else raw
thr = float(np.quantile(score.loc[train.index], q))
trend = (close > close.rolling(trend_win).mean()).shift(1).dropna() if trend_win else None
signal = dm.build_signal(score)

out = {}

# ---------- 1) walk-forward 基线对比 ----------
res = pd.read_csv(cfg.RESULTS / "walkforward_folds.csv", encoding="utf-8-sig")
agg = res.groupby(["model", "rule", "q", "smooth"]).agg(
    IR_mean=("IR", "mean"), IR_std=("IR", "std"), ann_mean=("ann", "mean"),
    expo_mean=("expo", "mean"), folds_pos=("IR", lambda x: int((x > 0).sum())),
).reset_index()
print("=== walk-forward（2013-2018 六折）基线对比 ===")
base = agg[(agg["model"] == choice["model"]) & (agg["smooth"] == smooth)]
keep = base[base["rule"].isin(["ML&MA20", "全仓持有", "MA20趋势", "MA60趋势", "ML&MA20底仓"])]
keep = keep.sort_values("IR_mean", ascending=False)
print(keep[["rule", "q", "IR_mean", "IR_std", "ann_mean", "expo_mean", "folds_pos"]].to_string(index=False))
out["walkforward_baselines"] = keep.to_dict("records")

# ---------- 2) 季度归因 ----------
print("\n=== 季度归因（策略 vs 沪深300 vs 买持江淮） ===")
qrows = []
for label, (s, e) in {"验证集": (cfg.VALID_START, cfg.VALID_END),
                      "测试集": (cfg.TEST_START, cfg.TEST_END)}.items():
    rep, _, _ = run_bt(signal, s, e, thr, trend, floor)
    nav = rep["account"] / rep["account"].iloc[0]
    b = bench.reindex(rep.index).ffill()
    bnav = b / b.iloc[0]
    j = close.reindex(rep.index).ffill()
    jnav = j / j.iloc[0]
    w = (rep["value"] / rep["account"]).fillna(0.0)
    for period, grp in rep.groupby(rep.index.to_period("Q")):
        qrows.append({
            "区间": label, "季度": str(period),
            "策略": nav.loc[grp.index[-1]] / nav.loc[grp.index[0]] - 1,
            "沪深300": bnav.loc[grp.index[-1]] / bnav.loc[grp.index[0]] - 1,
            "买持江淮": jnav.loc[grp.index[-1]] / jnav.loc[grp.index[0]] - 1,
            "平均仓位": w.loc[grp.index].mean(),
        })
qdf = pd.DataFrame(qrows)
for c in ["策略", "沪深300", "买持江淮", "平均仓位"]:
    qdf[c] = qdf[c].map(lambda v: f"{v:.2%}")
print(qdf.to_string(index=False))
out["quarterly"] = qdf.to_dict("records")

# ---------- 3) 回撤区间 ----------
print("\n=== 策略最大回撤区间（测试集） ===")
rep, _, _ = run_bt(signal, cfg.TEST_START, cfg.TEST_END, thr, trend, floor)
nav = rep["account"] / rep["account"].iloc[0]
dd = nav / nav.cummax() - 1
trough = dd.idxmin()
peak = nav.loc[:trough].idxmax()
after = nav.loc[trough:]
rec = after[after >= nav.loc[peak]]
print(f"  峰值 {peak.date()} 净值 {nav.loc[peak]:.3f} → 谷底 {trough.date()} 净值 {nav.loc[trough]:.3f} "
      f"（最大回撤 {dd.loc[trough]:.2%}）")
if len(rec):
    print(f"  修复日 {rec.index[0].date()}（历时 {(rec.index[0]-trough).days} 天）")

print("\n=== 策略最大回撤区间（验证集） ===")
rep2, _, _ = run_bt(signal, cfg.VALID_START, cfg.VALID_END, thr, trend, floor)
nav2 = rep2["account"] / rep2["account"].iloc[0]
dd2 = nav2 / nav2.cummax() - 1
trough2 = dd2.idxmin()
peak2 = nav2.loc[:trough2].idxmax()
after2 = nav2.loc[trough2:]
rec2 = after2[after2 >= nav2.loc[peak2]]
print(f"  峰值 {peak2.date()} 净值 {nav2.loc[peak2]:.3f} → 谷底 {trough2.date()} 净值 {nav2.loc[trough2]:.3f} "
      f"（最大回撤 {dd2.loc[trough2]:.2%}）")
if len(rec2):
    print(f"  修复日 {rec2.index[0].date()}（历时 {(rec2.index[0]-trough2).days} 天）")

(cfg.RESULTS / "diagnostics.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n[完成] 诊断数据写入 {cfg.RESULTS / 'diagnostics.json'}")
