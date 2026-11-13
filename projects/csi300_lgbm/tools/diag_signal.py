"""信号诊断：按预测分档看未来 5 日收益（验证期 vs 测试期），解释"IC 为正但 top10 不行"。"""

import json

import numpy as np
import pandas as pd

import model_core as mc

OUT = mc.RESULTS / "signal_diag.json"


def analyse(oos, ctx, label, start, end):
    o = oos[(oos["datetime"] >= start) & (oos["datetime"] <= end)].dropna(subset=["pred", "y"]).copy()
    o["dec"] = o.groupby("datetime")["pred"].rank(pct=True)
    bins = [0, 0.033, 0.1, 0.2, 0.35, 0.65, 0.8, 0.9, 0.967, 1.001]
    # 注意：dec 是"预测值从小到大"的百分位，所以高分位 = 模型最看好的票
    labels = ["后3%", "3-10%", "10-20%", "20-35%", "35-65%", "65-80%", "80-90%", "90-97%", "前3%"]
    o["bucket"] = pd.cut(o["dec"], bins=bins, labels=labels, include_lowest=True)
    g = o.groupby("bucket", observed=True)["y"].agg(["mean", "count", "std"])
    g["win"] = o.groupby("bucket", observed=True)["y"].apply(lambda s: (s > 0).mean())
    res = {"buckets": {k: {"mean_fwd5": float(v["mean"]), "n": int(v["count"]),
                           "win": float(v["win"])} for k, v in g.iterrows()},
           "pool_mean": float(o["y"].mean()),
           "top3pct_mean": float(o[o["dec"] > 0.967]["y"].mean()),
           "top10pct_mean": float(o[o["dec"] > 0.9]["y"].mean()),
           "bottom10pct_mean": float(o[o["dec"] < 0.1]["y"].mean()),
           "n_rows": int(len(o))}
    # 分年
    yearly = {}
    for y, gg in o.groupby(o["datetime"].dt.year):
        gg = gg.copy()
        gg["d10"] = gg.groupby("datetime")["pred"].rank(pct=True)
        yearly[int(y)] = {
            "top10_mean": float(gg[gg["d10"] > 0.9]["y"].mean()),
            "pool_mean": float(gg["y"].mean()),
            "ic": float(gg.groupby("datetime").apply(
                lambda x: x["pred"].rank().corr(x["y"].rank()) if len(x) > 10 else np.nan).mean()),
        }
    res["yearly"] = yearly
    print(f"\n== {label} ==")
    print(g.to_string())
    print(f"池内均值 {res['pool_mean']*100:+.3f}% | 前3% {res['top3pct_mean']*100:+.3f}% | "
          f"前10% {res['top10pct_mean']*100:+.3f}% | 后10% {res['bottom10pct_mean']*100:+.3f}%")
    for y, v in yearly.items():
        print(f"   {y}: top10 {v['top10_mean']*100:+.3f}%  池内 {v['pool_mean']*100:+.3f}%  "
              f"IC {v['ic']:.4f}")
    return res


def main():
    ctx = mc.load_all()
    oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
    out = {"valid": analyse(oos, ctx, "验证期 2020-2022", mc.VALID_START, mc.VALID_END),
           "test": analyse(oos, ctx, "测试期 2023-2026", mc.TEST_START, "2026-10-30")}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写出 {OUT}")


if __name__ == "__main__":
    main()
