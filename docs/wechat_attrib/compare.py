"""两个标的的同口径对比：江淮汽车 600418 vs 科大讯飞 002230。

同一套指标，方便文章里直接对撞：
  1) 涨跌停后的 T+1 / T+5 / T+20 超额与胜率
  2) 事件后的超额（全部 / 有事前证据 / 无事前证据）
  3) 有事前证据率（分时期）
  4) 公告类别事件研究（11 类，两标的并排）

产出：comparison.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\Project\qlib")
QLIB = ROOT / "qlib_data" / "cn_data_2026"
OUT = Path(__file__).resolve().parent / "comparison.json"

STOCKS = {
    "600418": {
        "name": "江淮汽车", "qlib_sym": "sh600418", "dir": ROOT / "projects" / "jac_600418" / "news_attribution",
    },
    "002230": {
        "name": "科大讯飞", "qlib_sym": "sz002230", "dir": ROOT / "projects" / "iflytek_002230" / "news_attribution",
    },
}


def cal() -> list[str]:
    return [x.strip() for x in (QLIB / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load(sym: str, field: str) -> pd.Series:
    arr = np.fromfile(QLIB / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    c = cal()
    start = int(arr[0])
    return pd.Series(arr[1:], index=pd.DatetimeIndex(c[start: start + len(arr) - 1]), dtype="float64")


def excess_series(sym: str) -> pd.Series:
    """超额收益序列（个股 - 沪深300），与各标的 REPORT/analysis.py 同口径：
    只保留个股与基准都有行情的交易日（自动跳过停牌日），T+N 指"之后的第 N 个有行情的交易日"。
    """
    df = pd.DataFrame({"px": load(sym, "adjclose"),
                       "bench": load("sh000300", "close")}).dropna()
    df["r"] = df["px"].pct_change()
    df["rb"] = df["bench"].pct_change()
    ex = (df["r"] - df["rb"]).dropna()
    ex.name = "excess"
    return ex


def blk(sub: pd.DataFrame, ex: pd.Series, idx: dict) -> dict:
    t1, t5, t20 = [], [], []
    for d in sub["date"]:
        i = idx.get(d)
        if i is None:
            continue
        t1.append(ex.iloc[i + 1] if i + 1 < len(ex) else np.nan)
        t5.append(ex.iloc[i + 5] if i + 5 < len(ex) else np.nan)
        t20.append(ex.iloc[i + 20] if i + 20 < len(ex) else np.nan)
    s1, s5, s20 = pd.Series(t1), pd.Series(t5), pd.Series(t20)
    return {
        "n": int(s1.notna().sum()),
        "T1超额%": round(s1.mean() * 100, 3),
        "T1胜率%": round((s1 > 0).mean() * 100, 1),
        "T5超额%": round(s5.mean() * 100, 3),
        "T5胜率%": round((s5 > 0).mean() * 100, 1),
        "T20超额%": round(s20.mean() * 100, 3),
        "T20胜率%": round((s20 > 0).mean() * 100, 1),
    }


def main():
    out = {}
    for code, cfg in STOCKS.items():
        d = cfg["dir"]
        ev = pd.read_csv(d / "events.csv")
        ev["date"] = ev["date"].astype(str)
        mt = pd.read_csv(d / "news_matches.csv")
        mt["event_date"] = mt["event_date"].astype(str)
        ev = ev.merge(mt[["event_date", "has_pre_evidence", "primary_category"]],
                      left_on="date", right_on="event_date", how="left")

        ex = excess_series(cfg["qlib_sym"])
        idx = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(ex.index)}

        rec = {"名称": cfg["name"], "代码": code,
               "事件区间": f"{ev['date'].min()} ~ {ev['date'].max()}",
               "事件总数": int(len(ev))}

        lim = ev[ev["is_limit"] == True]  # noqa: E712
        rec["涨跌停"] = {
            "总数": int(len(lim)),
            "涨停数": int((lim["ret"] > 0).sum()),
            "跌停数": int((lim["ret"] < 0).sum()),
            "涨停": blk(lim[lim["ret"] > 0], ex, idx),
            "跌停": blk(lim[lim["ret"] < 0], ex, idx),
        }

        rec["事件后续超额"] = {
            "全部": blk(ev, ex, idx),
            "有事前证据": blk(ev[ev["has_pre_evidence"] == True], ex, idx),  # noqa: E712
            "无事前证据": blk(ev[ev["has_pre_evidence"] == False], ex, idx),  # noqa: E712
        }
        rec["有证据率%"] = round(float(ev["has_pre_evidence"].mean() * 100), 1)

        # 分时期证据率
        ev["era"] = np.where(ev["date"] >= "2026-04-01", "2026-04起(有新闻)",
                             np.where(ev["date"] >= "2020-01-01", "2020-2026(仅公告)",
                                      "2001-2019(仅公告)"))
        rec["分时期证据率"] = {
            k: {"n": int(len(g)), "有证据率%": round(g["has_pre_evidence"].mean() * 100, 1)}
            for k, g in ev.groupby("era")
        }

        # 公告类别事件研究
        st = pd.read_csv(d / "event_study.csv")
        rec["类别事件研究"] = {
            r["category"]: {"n": int(r["n"]), "T0": round(float(r["t0_mean"]), 3),
                            "T1": round(float(r["t1_mean"]), 3),
                            "T1中位": round(float(r["t1_median"]), 3),
                            "T1胜率": round(float(r["t1_win"]), 1),
                            "T5": round(float(r["t5_mean"]), 3)}
            for _, r in st.iterrows()
        }

        # 主因类别 → 平均超额 / 胜率
        g = ev.groupby("primary_category").agg(
            n=("date", "count"),
            平均超额=("excess", lambda s: round(s.mean(), 2)),
            胜率=("excess", lambda s: round((s > 0).mean() * 100, 1)),
        ).sort_values("n", ascending=False)
        rec["主因类别表现"] = {k: {"n": int(v["n"]), "平均超额": float(v["平均超额"]),
                                "胜率": float(v["胜率"])} for k, v in g.iterrows()}

        # 年度收益 / 超额
        px = load(cfg["qlib_sym"], "adjclose")
        bench = load("sh000300", "close")
        df = pd.DataFrame({"px": px, "bench": bench}).dropna()
        df["r"] = df["px"].pct_change()
        df["rb"] = df["bench"].pct_change()
        df = df.dropna()
        yr = []
        for y, g2 in df.groupby(df.index.strftime("%Y")):
            yr.append({"year": int(y),
                       "个股%": round((g2["px"].iloc[-1] / g2["px"].iloc[0] - 1) * 100, 1),
                       "HS300%": round((g2["bench"].iloc[-1] / g2["bench"].iloc[0] - 1) * 100, 1),
                       "超额%": round((g2["r"].sum() - g2["rb"].sum()) * 100, 1),
                       "事件数": int((ev["date"].str[:4] == y).sum())})
        rec["分年度"] = yr
        n_years = (df.index[-1] - df.index[0]).days / 365.25
        tot = df["px"].iloc[-1] / df["px"].iloc[0] - 1
        totb = df["bench"].iloc[-1] / df["bench"].iloc[0] - 1
        cum = df["px"] / df["px"].iloc[0]
        rec["全历史"] = {
            "区间": f"{df.index[0].date()} ~ {df.index[-1].date()}",
            "交易日": int(len(df)),
            "累计%": round(tot * 100, 1),
            "基准累计%": round(totb * 100, 1),
            "年化%": round(((1 + tot) ** (1 / n_years) - 1) * 100, 2),
            "基准年化%": round(((1 + totb) ** (1 / n_years) - 1) * 100, 2),
            "最大回撤%": round(float((cum / cum.cummax() - 1).min() * 100), 1),
            "日波动%": round(float(df["r"].std() * 100), 2),
        }
        out[code] = rec

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for code, rec in out.items():
        print(f"\n===== {rec['名称']} {code} =====")
        print(f"区间 {rec['事件区间']} | 事件 {rec['事件总数']} | 有证据率 {rec['有证据率%']}%")
        print(f"全历史 {rec['全历史']}")
        print(f"涨跌停 {rec['涨跌停']['总数']}（涨{rec['涨跌停']['涨停数']}/跌{rec['涨跌停']['跌停数']}）")
        print(f"  涨停 {rec['涨跌停']['涨停']}")
        print(f"  跌停 {rec['涨跌停']['跌停']}")
        for k, v in rec["事件后续超额"].items():
            print(f"  {k}: {v}")
        print(f"  分时期: {rec['分时期证据率']}")
    print(f"\n已写入 {OUT}")


if __name__ == "__main__":
    main()
