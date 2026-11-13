"""给当前实盘持仓打趋势分（落地演示）：价量分 / 基本面分 / 事件分 → 混合总分 + 排名。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\score_holdings.py
产出：results\\holdings_score.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
DATA = PROJ / "data"
RESULTS = PROJ / "results"
POS = Path(r"D:\Project\qlib\projects\csi300_lgbm\results\positions_A.json")


def main():
    res = json.loads((RESULTS / "ic_results.json").read_text(encoding="utf-8"))
    wp, wf, we = res["selected"]["wp"], res["selected"]["wf"], res["selected"]["we"]

    df = pd.read_parquet(DATA / "scores.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    as_of = df["datetime"].max()
    day = df[df["datetime"] == as_of].copy()
    print(f"截面日期 {as_of.date()}  {len(day)} 只")

    book = json.loads(POS.read_text(encoding="utf-8"))
    hold = {p["symbol"]: p for p in book["positions"]}
    day["symbol"] = day["symbol"].astype(str)
    sub = day[day["symbol"].isin(hold)].copy()
    # 个别标的当日可能停牌/缺数据 → 逐只回退到它自己的最近有数据日
    for s in list(hold):
        cur = sub[sub["symbol"] == s]
        if len(cur) and cur["price_score"].notna().all():
            continue
        hist = df[(df["symbol"] == s)].sort_values("datetime")
        hist = hist[hist["price_score"].notna()]
        if len(hist):
            row = hist.iloc[[-1]].copy()
            sub = pd.concat([sub, row], ignore_index=True)
            print(f"  {s} 当日无有效数据 → 用 {pd.Timestamp(row['datetime'].iloc[0]).date()}")
        else:
            print(f"  {s} 全程无分数")

    sub["total"] = wp * sub["price_score"] + wf * sub["fund_score"] + we * sub["event_score"]
    sub = sub.sort_values("total", ascending=False)
    sub["rank"] = np.arange(1, len(sub) + 1)

    show = ["symbol", "name", "price_score", "fund_score", "event_score", "total", "rank",
            "roe", "rev_yoy", "np_yoy", "pe_ttm", "pe_pct_3y", "gross_margin",
            "days_since_report", "mom_20", "vol_20"]
    rows = []
    for _, r in sub.iterrows():
        rec = {"symbol": r["symbol"], "name": hold[r["symbol"]]["name"],
               "price_score": _f(r["price_score"]), "fund_score": _f(r["fund_score"]),
               "event_score": _f(r["event_score"]), "total": _f(r["total"]),
               "rank": int(r["rank"])}
        for c in show[7:]:
            rec[c] = _f(r[c]) if c in sub.columns else None
        rows.append(rec)

    out = {"as_of": str(pd.Timestamp(as_of).date()), "weights": {"price": wp, "fund": wf,
                                                                "event": we},
           "n": len(rows), "rows": rows}
    (RESULTS / "holdings_score.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写出 holdings_score.json（{len(rows)} 只）")
    for r in rows:
        t = r["total"]
        ts = f"{t:+.3f}" if t is not None else "  n/a "
        p = r["price_score"]
        f_ = r["fund_score"]
        e = r["event_score"]
        ps = f"{p:+.3f}" if p is not None else " n/a "
        fs = f"{f_:+.3f}" if f_ is not None else " n/a "
        es = f"{e:+.3f}" if e is not None else " n/a "
        print(f"  {r['rank']:>2}. {r['name']:<8} 总分 {ts} (价量 {ps} / 基本面 {fs} / 事件 {es})")
    missing = [r["name"] for r in rows if r["total"] is None]
    if missing:
        print(f"  ⚠️ 无分数（截面缺数据）: {missing}")


def _f(x):
    try:
        v = float(x)
        return None if not np.isfinite(v) else round(v, 4)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
