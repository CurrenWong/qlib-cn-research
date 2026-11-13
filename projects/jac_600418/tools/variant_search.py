"""策略变体实验。

协议（严格）：
  1. 变体集合先验给定，不看测试集
  2. 每个变体在【验证集】上选阈值，选型标准 = 相对沪深300 的信息比率
  3. 选定变体 + 阈值后【冻结】，再看测试集

先用向量化模拟快速比选（交易成本近似），最终数字以 qlib 撮合回测为准。
"""

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

# 收盘价 & 均线（全部只用历史数据）
close = dm.stock_close()
ma = {w: close.rolling(w).mean() for w in (20, 60, 120)}

# 候选模型
cands = dm.fit_candidates(train, valid)
best_name, best, table = dm.select_model(cands, train, valid)
print(f"选定模型：{best_name}\n")
score = pd.Series(best["predict"](df.dropna(subset=cfg.FEATURE_NAMES)[cfg.FEATURE_NAMES]),
                  index=df.dropna(subset=cfg.FEATURE_NAMES).index).sort_index()

bench = dm.bench_close()
COST = cfg.OPEN_COST + cfg.CLOSE_COST


def simulate(pos: pd.Series, label: pd.Series) -> pd.Series:
    """pos[t] 为 t 日信号决定的仓位（持有 t+1→t+2），label[t] 是对应收益。"""
    pos = pos.reindex(label.index).fillna(0.0)
    turn = pos.diff().abs().fillna(pos.abs())
    r = pos * label - turn * COST
    return (1 + r).cumprod()


def metrics(nav: pd.Series, bnav: pd.Series) -> dict:
    nav = nav.dropna()
    bnav = bnav.reindex(nav.index).ffill().dropna()
    nav, bnav = nav.reindex(bnav.index), bnav
    r = nav.pct_change().dropna()
    br = bnav.pct_change().dropna()
    ex = (r - br).dropna()
    n = len(r)
    years = n / cfg.TRADING_DAYS
    ann = (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1
    te = ex.std(ddof=1) * np.sqrt(cfg.TRADING_DAYS)
    ann_ex = (1 + ex.mean()) ** cfg.TRADING_DAYS - 1
    return {
        "年化": ann,
        "最大回撤": (nav / nav.cummax() - 1).min(),
        "IR": ann_ex / te if te > 0 else np.nan,
        "超额年化": ann_ex,
        "仓位": (pos_used[pos_used.index.intersection(nav.index)]).mean() if False else np.nan,
    }


def eval_variant(name: str, pos_fn, period_df, bench_series):
    """在给定区间上评估变体（阈值网格在区间内选）。"""
    idx = period_df.index
    lab = period_df["label"]
    tr_score = score.loc[train.index]
    rows = []
    for q in cfg.THRESHOLD_QUANTILES:
        thr = float(np.quantile(tr_score, q))
        pos = pos_fn(thr).reindex(idx).fillna(0.0)
        nav = simulate(pos, lab)
        bnav = (bench_series.reindex(idx).ffill() / bench_series.reindex(idx).ffill().iloc[0])
        m = metrics(nav, bnav)
        m.update({"name": name, "q": q, "thr": thr, "expo": pos.mean(),
                  "n": len(idx)})
        rows.append(m)
    return pd.DataFrame(rows)


# ---- 变体定义（先验）
def pos_score_only(thr):
    return (score > thr).astype(float)


def make_trend_variant(w):
    def f(thr):
        return ((score > thr) & (close > ma[w])).astype(float)
    return f


def pos_trend_only(thr):
    return (close > ma[60]).astype(float)


VARIANTS = {
    "V1 仅ML分数": pos_score_only,
    "V2 ML+MA20趋势": make_trend_variant(20),
    "V3 ML+MA60趋势": make_trend_variant(60),
    "V4 ML+MA120趋势": make_trend_variant(120),
    "V5 仅MA60趋势": pos_trend_only,
}

# ---------- 验证集选型 ----------
print("=" * 96)
print("验证集（2017-01 ~ 2018-12）上选阈值 / 选变体")
print("=" * 96)
valid_rows = []
for name, fn in VARIANTS.items():
    dfv = eval_variant(name, fn, valid, bench)
    best = dfv.loc[dfv["IR"].idxmax()]
    valid_rows.append(best)
    print(f"{name:16s} 最优 q={best['q']:.1f} 仓位 {best['expo']:5.1%} "
          f"年化 {best['年化']:+7.2%} 回撤 {best['最大回撤']:+7.2%} "
          f"超额 {best['超额年化']:+7.2%} IR {best['IR']:+6.3f}")

vsel = pd.DataFrame(valid_rows).sort_values("IR", ascending=False)
winner = vsel.iloc[0]
print(f"\n>>> 验证集选定：{winner['name']}  q={winner['q']}  thr={winner['thr']:+.5f}")

# ---------- 冻结后看测试集 ----------
print("\n" + "=" * 96)
print("冻结后（同一变体 + 同一阈值）看测试集 2019-01 ~ 2020-09")
print("=" * 96)
fn = VARIANTS[winner["name"]]
thr = float(winner["thr"])
for label, d in [("验证集", valid), ("测试集", test)]:
    pos = fn(thr).reindex(d.index).fillna(0.0)
    nav = simulate(pos, d["label"])
    bser = bench.reindex(d.index).ffill()
    bnav = bser / bser.iloc[0]
    jser = close.reindex(d.index).ffill()
    jnav = jser / jser.iloc[0]
    m = metrics(nav, bnav)
    jm = metrics(jnav, bnav)
    print(f"\n[{label}] 仓位 {pos.mean():.1%}")
    print(f"  策略      年化 {m['年化']:+7.2%}  回撤 {m['最大回撤']:+7.2%}  超额 {m['超额年化']:+7.2%}  IR {m['IR']:+6.3f}")
    print(f"  沪深300   年化 {metrics(bnav, bnav)['年化']:+7.2%}  回撤 {metrics(bnav, bnav)['最大回撤']:+7.2%}")
    print(f"  买持江淮  年化 {jm['年化']:+7.2%}  回撤 {jm['最大回撤']:+7.2%}  超额 {jm['超额年化']:+7.2%}")

# ---------- 参考：各变体在验证/测试上的表现矩阵（诊断用） ----------
print("\n" + "=" * 96)
print("诊断矩阵：各变体（各自用验证集最优阈值）在验证 / 测试的表现")
print("=" * 96)
for name, f in VARIANTS.items():
    line = [f"{name:16s}"]
    for label, d in [("验证", valid), ("测试", test)]:
        pos = f(thr) if False else None
        # 每行变体都用它自己在验证集选出的阈值
        q_row = [r for r in valid_rows if r["name"] == name][0]
        p = f(float(q_row["thr"])).reindex(d.index).fillna(0.0)
        nav = simulate(p, d["label"])
        bser = bench.reindex(d.index).ffill()
        m = metrics(nav, bser / bser.iloc[0])
        line.append(f"{label}: 年化 {m['年化']:+7.2%} IR {m['IR']:+6.3f} 仓位 {p.mean():5.1%}")
    print("  ".join(line))
