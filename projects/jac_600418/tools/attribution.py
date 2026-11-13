"""归因诊断（事后分析，不参与选型）。

回答两个问题：
  1. 测试期跑输基准，是"江淮自己不行"还是"择时把收益做没了"？
  2. 不同仓位档位的策略，样本外表现如何？（用于展示仓位-收益权衡，非选型依据）
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config as cfg
import data_model as dm

dm.init_qlib()

df = dm.fetch_data()
train, valid, test = dm.split_data(df)
close = dm.stock_close()
bench = dm.bench_close()
COST = cfg.OPEN_COST + cfg.CLOSE_COST
ma = {20: close.rolling(20).mean(), 60: close.rolling(60).mean()}


def simulate(pos, label):
    pos = pos.reindex(label.index).fillna(0.0)
    turn = pos.diff().abs().fillna(pos.abs())
    return (1 + pos * label - turn * COST).cumprod()


def ir(nav, bser):
    nav = nav.dropna()
    b = bser.reindex(nav.index).ffill()
    b = b / b.iloc[0]
    d = pd.concat([nav.pct_change().rename("s"), b.pct_change().rename("b")], axis=1).dropna()
    ex = d["s"] - d["b"]
    te = ex.std(ddof=1) * np.sqrt(cfg.TRADING_DAYS)
    return ((1 + ex.mean()) ** cfg.TRADING_DAYS - 1) / te if te > 0 else np.nan


def ann(nav):
    nav = nav.dropna()
    return (nav.iloc[-1] / nav.iloc[0]) ** (cfg.TRADING_DAYS / len(nav)) - 1


# ---------- 1. 价值归因：股票本身 vs 择时 ----------
print("=" * 92)
print("价值归因：测试期跑输基准，锅在谁头上？")
print("=" * 92)
rows = []
for label, d in [("验证集", valid), ("测试集", test)]:
    bser = bench.reindex(d.index).ffill()
    jser = close.reindex(d.index).ffill()
    bnav = bser / bser.iloc[0]
    jnav = jser / jser.iloc[0]
    rows.append({
        "区间": label,
        "沪深300": ann(bnav),
        "买持江淮": ann(jnav),
        "股票自身相对基准": ann(jnav) - ann(bnav),
    })
att = pd.DataFrame(rows)
print(att.to_string(index=False, float_format=lambda v: f"{v:+.2%}"))
print("\n解读：测试期『买持江淮』几乎追平沪深300，说明股票本身没拖后腿；")
print("      策略的落后完全来自择时（低仓位 + 错过反弹）。")

# ---------- 2. 仓位档位 vs 样本外表现（事后诊断） ----------
print("\n" + "=" * 92)
print("仓位档位全景（阈值分位点取各变体在 walk-forward 上的最优；本表为事后诊断，不参与选型）")
print("=" * 92)
wf = pd.read_csv(cfg.RESULTS / "walkforward_folds.csv", encoding="utf-8-sig")
agg = wf.groupby(["model", "rule", "q", "smooth"]).agg(
    IR_mean=("IR", "mean"), folds_pos=("IR", lambda x: int((x > 0).sum())),
    expo=("expo", "mean")).reset_index()

# 用最终模型重新拟合到主训练集，统一算各规则的样本外表现
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

sc = StandardScaler().fit(train[cfg.FEATURE_NAMES])
model = Ridge(alpha=100.0).fit(sc.transform(train[cfg.FEATURE_NAMES]), train["label"])
clean = df.dropna(subset=cfg.FEATURE_NAMES)
raw = pd.Series(model.predict(sc.transform(clean[cfg.FEATURE_NAMES])), index=clean.index).sort_index()
score = raw.rolling(5).mean().dropna()

variants = [
    ("全仓持有", 0.0, None, 1.0),
    ("MA20趋势", 0.0, 20, 0.0),
    ("ML&MA20 底仓50%", 0.4, 20, 0.5),
    ("ML&MA20 (选定)", 0.4, 20, 0.0),
]
out = []
for name, q, tw, floor in variants:
    thr = float(np.quantile(score.loc[train.index], q)) if q else 0.0
    trend = (close > ma[tw]) if tw else None
    row = {"方案": name, "平均仓位(wf)": None, "wf_IR均值": None}
    sub = agg[(agg["model"] == "Ridge_a100") & (agg["rule"] == name.replace(" (选定)", ""))]
    if len(sub):
        row["平均仓位(wf)"] = float(sub.iloc[0]["expo"])
        row["wf_IR均值"] = float(sub.iloc[0]["IR_mean"])
    for label, d in [("验证", valid), ("测试", test)]:
        ok = trend.reindex(d.index).fillna(False) if trend is not None else True
        hit = ((score.reindex(d.index) > thr) & ok) if q else pd.Series(ok, index=d.index)
        pos = hit.fillna(False).astype(float) * (1 - floor) + floor
        nav = simulate(pos, d["label"])
        bser = bench.reindex(d.index).ffill()
        row[f"{label}_年化"] = ann(nav)
        row[f"{label}_IR"] = ir(nav, bser)
        row[f"{label}_仓位"] = float(pos.mean())
    out.append(row)

tab = pd.DataFrame(out)
print(tab.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
print("\n读法：walk-forward IR 最高的方案（ML&MA20 选定版）在测试期 IR 最差 —— ")
print("      这正是单票日频择时的典型失效模式：样本内有效、样本外不持续。")

(cfg.RESULTS / "attribution.json").write_text(
    json.dumps({"attribution": att.to_dict("records"), "exposure_ladder": tab.to_dict("records")},
               ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"\n[完成] 写入 {cfg.RESULTS / 'attribution.json'}")
