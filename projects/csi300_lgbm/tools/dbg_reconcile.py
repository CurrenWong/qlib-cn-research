"""对齐口径：全日 vs 每20日调仓日，top10/top3% 的前瞻收益 vs 池内。"""

import numpy as np
import pandas as pd

import model_core as mc

oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
ctx = mc.load_all()
dpos = {d: i for i, d in enumerate(ctx["dates"])}


def run(label, start, end, freq=20):
    o = oos[(oos["datetime"] >= start) & (oos["datetime"] <= end)].dropna(subset=["pred", "y"]).copy()
    o["dec"] = o.groupby("datetime")["pred"].rank(pct=True)
    all_dates = sorted(o["datetime"].unique())
    reb_dates = all_dates[::freq]
    print(f"\n=== {label}（{len(o)} 行，{len(all_dates)} 个交易日，调仓日 {len(reb_dates)} 个）===")
    for tag, ds in (("全部交易日", all_dates), ("每20日调仓日", reb_dates)):
        g = o[o["datetime"].isin(ds)]
        t3 = g[g["dec"] > 0.967]["y"].mean()
        t10 = g[g["dec"] > 0.9]["y"].mean()
        pool = g["y"].mean()
        # 逐日 IC
        ics = []
        for d, x in g.groupby("datetime"):
            if len(x) < 10:
                continue
            ics.append(x["pred"].rank().corr(x["y"].rank()))
        ic = np.nanmean(ics)
        # 池内等权（每日等权再平衡口径：池内平均日收益 × 5 天）
        daily = g.groupby("datetime")["y"].mean()
        print(f"  {tag}: top3% {t3*100:+.3f}%  top10% {t10*100:+.3f}%  池内 {pool*100:+.3f}%  "
              f"IC {ic:+.4f}  | 池内5日均值×(5/1)= {daily.mean()*5*100:+.3f}%")
        # 组合口径：每 20 日取 top10 等权，持有一期（用 5 日前瞻近似）→ 与策略一致
        port = []
        for d in ds:
            x = o[o["datetime"] == d]
            if len(x) < 50:
                continue
            port.append(x.nlargest(10, "pred")["y"].mean())
        print(f"      调仓日 top10 等权前瞻5日: {np.mean(port)*100:+.3f}%  "
              f"（同期池内 {np.mean([o[o['datetime']==d]['y'].mean() for d in ds])*100:+.3f}%）")


run("测试期 2023-2026", mc.TEST_START, "2026-10-30")
run("验证期 2020-2022", mc.VALID_START, mc.VALID_END)
run("全期 2018-2026", "2018-01-01", "2026-10-30")
