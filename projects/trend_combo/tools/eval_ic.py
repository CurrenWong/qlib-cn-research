"""验证：因子级 IC → 自动定向 → 分域合成 → 跨域权重网格 → 测试期一次性评估。

协议（沿用本仓库老规矩，**测试期绝不参与选型**）：
  训练 2016-2019（定方向、筛因子） / 验证 2020-2022（定跨域权重） / 测试 2023-2026（只跑一次）

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\eval_ic.py
产出：results\\ic_results.json / results\\factor_ic.csv / results\\ic_yearly.csv / results\\weight_grid.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_panel import FUND_GROUPS, PRICE_GROUPS, EVENT_FIELDS, FUND_DIRECTION
from composite import PRICE_DIRECTION

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
DATA = PROJ / "data"
RESULTS = PROJ / "results"

TRAIN = ("2016-01-01", "2019-12-31")
VALID = ("2020-01-01", "2022-12-31")
TEST = ("2023-01-01", "2026-12-31")

IC_THRESH = 0.008        # 训练期 |RankIC| 门槛
T_THRESH = 2.0           # 训练期 |t| 门槛
PRIOR = {**PRICE_DIRECTION, **FUND_DIRECTION}


def rank_ic(dates, score, label, min_n=20):
    """逐交易日 Spearman RankIC（向量化）。"""
    d = pd.DataFrame({"d": np.asarray(dates), "s": np.asarray(score, dtype=float),
                      "y": np.asarray(label, dtype=float)}).dropna()
    if d.empty:
        return pd.Series(dtype=float)
    cnt = d.groupby("d")["s"].transform("size")
    d = d[cnt >= min_n]
    if d.empty:
        return pd.Series(dtype=float)
    d["pr"] = d.groupby("d")["s"].rank()
    d["yr"] = d.groupby("d")["y"].rank()
    for c in ("pr", "yr"):
        mu = d.groupby("d")[c].transform("mean")
        sd = d.groupby("d")[c].transform("std")
        d[c] = (d[c] - mu) / sd.replace(0, np.nan)
    return d.groupby("d").apply(lambda x: float((x["pr"] * x["yr"]).mean()),
                                include_groups=False).dropna()


def ic_stats(ic):
    ic = ic.dropna()
    n = len(ic)
    if n < 5:
        return {"n": n}
    m, s = float(ic.mean()), float(ic.std(ddof=1))
    return {"n": n, "ic_mean": m, "ic_std": s,
            "icir": m / s if s > 0 else 0.0,
            "t_stat": m / s * np.sqrt(n) if s > 0 else 0.0,
            "win_ratio": float((ic > 0).mean())}


def rng(ic, r):
    return ic[(ic.index >= pd.Timestamp(r[0])) & (ic.index <= pd.Timestamp(r[1]))]


def domain_of(f):
    for g, cols in PRICE_GROUPS.items():
        if f in cols:
            return "price:" + g
    for g, cols in FUND_GROUPS.items():
        if f in cols:
            return "fund:" + g
    if f in EVENT_FIELDS:
        return "event"
    return "other"


def main():
    print("① 读分数面板 …")
    df = pd.read_parquet(DATA / "scores.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    factors = [c[2:] for c in df.columns if c.startswith("z_")]
    print(f"   {df.shape}  {len(factors)} 个因子")

    dates = df["datetime"]
    labels = {"fwd5": df["label_fwd5"], "fwd20": df["label_fwd20"]}

    # ---------- 阶段 A：因子级 IC ----------
    print("② 因子级 RankIC（原始 z，不含方向）…")
    rows = []
    for f in factors:
        z = df["z_" + f]
        rec = {"factor": f, "domain": domain_of(f), "prior_dir": PRIOR.get(f, 1)}
        for lname, lab in labels.items():
            ic = rank_ic(dates, z, lab)
            rec[f"{lname}_train_ic"] = ic_stats(rng(ic, TRAIN)).get("ic_mean", np.nan)
            rec[f"{lname}_train_t"] = ic_stats(rng(ic, TRAIN)).get("t_stat", np.nan)
            rec[f"{lname}_valid_ic"] = ic_stats(rng(ic, VALID)).get("ic_mean", np.nan)
            rec[f"{lname}_test_ic"] = ic_stats(rng(ic, TEST)).get("ic_mean", np.nan)
        rows.append(rec)
    fdf = pd.DataFrame(rows)
    fdf["auto_dir"] = np.where(fdf["fwd5_train_ic"] >= 0, 1, -1)
    fdf["keep"] = ((fdf["fwd5_train_ic"].abs() >= IC_THRESH)
                   & (fdf["fwd5_train_t"].abs() >= T_THRESH))
    fdf["prior_agrees"] = (np.sign(fdf["fwd5_train_ic"]) == np.sign(fdf["prior_dir"]))
    fdf.to_csv(RESULTS / "factor_ic.csv", index=False, encoding="utf-8-sig")
    print(f"   因子表写出：{len(fdf)} 个因子，其中训练期通过筛选 {int(fdf['keep'].sum())} 个，"
          f"先验方向与训练期符号一致 {int(fdf['prior_agrees'].sum())} 个")

    # ---------- 阶段 B：分域合成（等权 / IC 加权） ----------
    dirs = dict(zip(fdf["factor"], fdf["auto_dir"]))
    kept = [f for f in fdf.loc[fdf["keep"], "factor"]]
    train_ic = dict(zip(fdf["factor"], fdf["fwd5_train_ic"].fillna(0)))

    def dom_cols(dom):
        if dom == "price":
            return [f for f in PRICE_GROUPS["trend"] + PRICE_GROUPS["reversal"]
                    + PRICE_GROUPS["risk"] + PRICE_GROUPS["flow"]]
        if dom == "fund":
            return [f for g in FUND_GROUPS.values() for f in g]
        return list(EVENT_FIELDS)

    def build_domain_scores(weight_mode):
        out = {}
        for dom in ("price", "fund", "event"):
            cols = [f for f in dom_cols(dom) if f in kept and f"z_{f}" in df.columns]
            if not cols:
                out[dom] = pd.Series(np.nan, index=df.index)
                continue
            mats = [df["z_" + f] * dirs.get(f, 1) for f in cols]
            m = pd.concat(mats, axis=1)
            if weight_mode == "equal":
                out[dom] = m.mean(axis=1)
            else:
                w = np.array([abs(train_ic.get(f, 0)) for f in cols])
                w = w / w.sum() if w.sum() > 0 else np.ones(len(cols)) / len(cols)
                out[dom] = m.mul(w, axis=1).sum(axis=1)
        return out

    results = {"splits": {"train": TRAIN, "valid": VALID, "test": TEST},
               "n_factors": len(factors), "n_kept": len(kept),
               "kept": kept, "factor_table": fdf.to_dict("records"),
               "ic_threshold": IC_THRESH, "t_threshold": T_THRESH}

    best = None
    for wmode in ("equal", "icw"):
        doms = build_domain_scores(wmode)
        grid = []
        for wp in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            for wf in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                for we in [0.0, 0.05, 0.10]:
                    if abs(wp + wf + we - 1.0) > 1e-9:
                        continue
                    # 注意：0 × NaN = NaN，权重为 0 的域若缺数据会把整行剔掉，
                    # 所以网格行的数字略高于「纯单域」变体；报告以变体表为准。
                    s = wp * doms["price"] + wf * doms["fund"] + we * doms["event"]
                    ic5 = rank_ic(dates, s, labels["fwd5"])
                    ic20 = rank_ic(dates, s, labels["fwd20"])
                    grid.append({"wmode": wmode, "wp": wp, "wf": wf, "we": we,
                                 "valid_ic_f5": ic_stats(rng(ic5, VALID)).get("ic_mean", np.nan),
                                 "valid_icir_f5": ic_stats(rng(ic5, VALID)).get("icir", np.nan),
                                 "train_ic_f5": ic_stats(rng(ic5, TRAIN)).get("ic_mean", np.nan),
                                 "test_ic_f5": ic_stats(rng(ic5, TEST)).get("ic_mean", np.nan),
                                 "test_icir_f5": ic_stats(rng(ic5, TEST)).get("icir", np.nan),
                                 "valid_ic_f20": ic_stats(rng(ic20, VALID)).get("ic_mean", np.nan),
                                 "test_ic_f20": ic_stats(rng(ic20, TEST)).get("ic_mean", np.nan),
                                 "test_icir_f20": ic_stats(rng(ic20, TEST)).get("icir", np.nan)})
        gdf = pd.DataFrame(grid)
        gdf = gdf.sort_values("valid_icir_f5", ascending=False)
        gdf.to_csv(RESULTS / f"weight_grid_{wmode}.csv", index=False, encoding="utf-8-sig")
        print(f"③ {wmode} 权重网格：验证期最优 {gdf.iloc[0]['wp']:.2f}/"
              f"{gdf.iloc[0]['wf']:.2f}/{gdf.iloc[0]['we']:.2f} "
              f"valid ICIR {gdf.iloc[0]['valid_icir_f5']:.3f} "
              f"→ test IC {gdf.iloc[0]['test_ic_f5']:.4f}")
        if best is None or gdf.iloc[0]["valid_icir_f5"] > best["row"]["valid_icir_f5"]:
            best = {"wmode": wmode, "row": gdf.iloc[0].to_dict(), "gdf": gdf}

    # ---------- 阶段 C：测试期只跑一次 ----------
    doms = build_domain_scores(best["wmode"])
    w = best["row"]
    s_price = doms["price"]
    s_fund = doms["fund"]
    s_event = doms["event"]
    s_mix = w["wp"] * s_price + w["wf"] * s_fund + w["we"] * s_event

    variants = {"price_only": s_price, "fund_only": s_fund, "event_only": s_event,
                "mix_selected": s_mix,
                "price_prior_dir": df["price_score"], "fund_prior_dir": df["fund_score"]}
    out_v = {}
    ic_store = {}
    for vn, s in variants.items():
        out_v[vn] = {}
        for lname, lab in labels.items():
            ic = rank_ic(dates, s, lab)
            ic_store[(vn, lname)] = ic
            out_v[vn][lname] = {"train": ic_stats(rng(ic, TRAIN)),
                                "valid": ic_stats(rng(ic, VALID)),
                                "test": ic_stats(rng(ic, TEST)),
                                "all": ic_stats(ic)}
    results["variants"] = out_v
    results["selected"] = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                           for k, v in w.items()}
    results["selected"]["wmode"] = best["wmode"]

    # 分年
    yrows = []
    for vn in ["price_only", "fund_only", "event_only", "mix_selected"]:
        for lname in labels:
            ic = ic_store[(vn, lname)]
            for y, g in ic.groupby(ic.index.year):
                yrows.append({"variant": vn, "label": lname, "year": int(y), **ic_stats(g)})
    pd.DataFrame(yrows).to_csv(RESULTS / "ic_yearly.csv", index=False, encoding="utf-8-sig")
    results["yearly"] = yrows

    # 分档（测试期 fwd20）
    te = pd.DataFrame({"d": dates, "s": s_mix.to_numpy(),
                       "y": labels["fwd20"].to_numpy()})
    te = te[(te["d"] >= pd.Timestamp(TEST[0])) & (te["d"] <= pd.Timestamp(TEST[1]))].dropna()
    te["q"] = te.groupby("d")["s"].transform(
        lambda x: pd.qcut(x.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]))
    bk = te.groupby("q", observed=True)["y"].agg(["mean", "count"]).to_dict("index")
    results["buckets_test_fwd20"] = {str(k): v for k, v in bk.items()}

    (RESULTS / "ic_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print("④ 写出 results/ic_results.json")

    print("\n%-22s %-24s %-24s %-24s" % ("变体", "训练 IC(fwd5)", "验证 IC(fwd5)", "测试 IC(fwd5)"))
    for vn in ["price_only", "fund_only", "event_only", "mix_selected",
               "price_prior_dir", "fund_prior_dir"]:
        e = out_v[vn]["fwd5"]
        print("%-22s %-24s %-24s %-24s" % (
            vn,
            f"{e['train'].get('ic_mean', 0):+.4f} (IR {e['train'].get('icir', 0):+.2f})",
            f"{e['valid'].get('ic_mean', 0):+.4f} (IR {e['valid'].get('icir', 0):+.2f})",
            f"{e['test'].get('ic_mean', 0):+.4f} (IR {e['test'].get('icir', 0):+.2f})"))
    print("\n选中权重:", {k: results["selected"][k] for k in ("wmode", "wp", "wf", "we")})


if __name__ == "__main__":
    main()
