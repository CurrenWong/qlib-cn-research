"""科大讯飞（002230）结构性分析：18 年行情解剖 + 涨跌停赚钱效应 + 关键窗口对比。

用 qlib 的 adjclose（复权收益率口径）+ 沪深300 做基准，收益全部是**超额收益**。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

HERE = Path(__file__).resolve().parent
QLIB = Path(_ROOT + r"/qlib_data/cn_data_2026")
OUT = HERE / "analysis.json"


def cal() -> list[str]:
    return [x.strip() for x in (QLIB / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load(sym: str, field: str) -> pd.Series:
    arr = np.fromfile(QLIB / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    c = cal()
    start = int(arr[0])
    return pd.Series(arr[1:], index=pd.DatetimeIndex(c[start: start + len(arr) - 1]),
                      dtype="float64")


def main():
    c = cal()
    px = load("sz002230", "adjclose")
    bench = load("sh000300", "close")
    df = pd.DataFrame({"px": px, "bench": bench}).dropna()
    df["ret"] = df["px"].pct_change()
    df["ret_b"] = df["bench"].pct_change()
    df["exc"] = df["ret"] - df["ret_b"]
    df = df.dropna()

    out: dict = {}

    # ---------- 1. 全历史统计 ----------
    n_years = (df.index[-1] - df.index[0]).days / 365.25
    total = df["px"].iloc[-1] / df["px"].iloc[0] - 1
    total_b = df["bench"].iloc[-1] / df["bench"].iloc[0] - 1
    cum = df["px"] / df["px"].iloc[0]
    dd = (cum / cum.cummax() - 1).min()
    cum_b = df["bench"] / df["bench"].iloc[0]
    dd_b = (cum_b / cum_b.cummax() - 1).min()
    out["全历史"] = {
        "区间": f"{df.index[0]} ~ {df.index[-1]}",
        "交易日": int(len(df)),
        "年数": round(n_years, 1),
        "累计涨跌%": round(total * 100, 1),
        "基准累计%": round(total_b * 100, 1),
        "年化%": round(((1 + total) ** (1 / n_years) - 1) * 100, 2),
        "基准年化%": round(((1 + total_b) ** (1 / n_years) - 1) * 100, 2),
        "日波动%": round(df["ret"].std() * 100, 2),
        "超额日波动%": round(df["exc"].std() * 100, 2),
        "最大回撤%": round(dd * 100, 1),
        "基准最大回撤%": round(dd_b * 100, 1),
        "年化超额%": round((((1 + total) ** (1 / n_years) - 1)
                            - ((1 + total_b) ** (1 / n_years) - 1)) * 100, 2),
    }

    # ---------- 2. 分年度：收益 / 超额 / 波动 / 事件数 ----------
    ev = pd.read_csv(HERE / "events.csv")
    ev["date"] = ev["date"].astype(str)
    ev["year"] = ev["date"].str[:4]
    rows = []
    for y, g in df.groupby(df.index.strftime("%Y")):
        r = g["ret"]
        b = g["ret_b"]
        rows.append({
            "year": y,
            "交易日": len(g),
            "个股%": round((g["px"].iloc[-1] / g["px"].iloc[0] - 1) * 100, 1),
            "HS300%": round((g["bench"].iloc[-1] / g["bench"].iloc[0] - 1) * 100, 1),
            "超额%": round((r.sum() - b.sum()) * 100, 1),
            "日波动%": round(r.std() * 100, 2),
            "最大回撤%": round(((g["px"] / g["px"].cummax() - 1).min()) * 100, 1),
            "事件数": int((ev["year"] == y).sum()),
            "涨停": int(((ev["year"] == y) & (ev["is_limit"] == True) & (ev["ret"] > 0)).sum()),
            "跌停": int(((ev["year"] == y) & (ev["is_limit"] == True) & (ev["ret"] < 0)).sum()),
        })
    yr = pd.DataFrame(rows)
    out["分年度"] = yr.to_dict("records")

    # ---------- 3. 涨跌停的赚钱效应（次日/5日超额） ----------
    def fwd(df, i, k):
        return df["exc"].iloc[i + k] if i + k < len(df) else np.nan

    idx_map = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(df.index)}
    lim = ev[ev["is_limit"] == True].copy()
    lim["t1"] = [fwd(df, idx_map[d], 1) if d in idx_map else np.nan for d in lim["date"]]
    lim["t5"] = [fwd(df, idx_map[d], 5) if d in idx_map else np.nan for d in lim["date"]]
    lim["t20"] = [fwd(df, idx_map[d], 20) if d in idx_map else np.nan for d in lim["date"]]
    up_lim, dn_lim = lim[lim["ret"] > 0], lim[lim["ret"] < 0]
    out["涨跌停赚钱效应"] = {
        "涨停": {
            "n": int(len(up_lim)),
            "T1超额%": round(up_lim["t1"].mean() * 100, 3),
            "T1胜率%": round((up_lim["t1"] > 0).mean() * 100, 1),
            "T5超额%": round(up_lim["t5"].mean() * 100, 3),
            "T5胜率%": round((up_lim["t5"] > 0).mean() * 100, 1),
            "T20超额%": round(up_lim["t20"].mean() * 100, 3),
            "T20胜率%": round((up_lim["t20"] > 0).mean() * 100, 1),
        },
        "跌停": {
            "n": int(len(dn_lim)),
            "T1超额%": round(dn_lim["t1"].mean() * 100, 3),
            "T1胜率%": round((dn_lim["t1"] > 0).mean() * 100, 1),
            "T5超额%": round(dn_lim["t5"].mean() * 100, 3),
            "T5胜率%": round((dn_lim["t5"] > 0).mean() * 100, 1),
            "T20超额%": round(dn_lim["t20"].mean() * 100, 3),
            "T20胜率%": round((dn_lim["t20"] > 0).mean() * 100, 1),
        },
    }

    # 全部事件的后续超额（对照）
    ev["t1"] = [fwd(df, idx_map[d], 1) if d in idx_map else np.nan for d in ev["date"]]
    ev["t5"] = [fwd(df, idx_map[d], 5) if d in idx_map else np.nan for d in ev["date"]]
    ev["exc"] = ev["excess"] / 100

    # 按「有无事前证据」拆开：这是全篇最关键的一组对照
    mt = pd.read_csv(HERE / "news_matches.csv")
    mt["event_date"] = mt["event_date"].astype(str)
    ev = ev.merge(mt[["event_date", "has_pre_evidence", "primary_category"]].rename(
        columns={"event_date": "date"}), on="date", how="left")

    def blk(sub):
        # 胜率只统计"有有效 T+1"的事件：停牌日（qlib adjclose=NaN）和序列末尾的事件
        # 不该被当成亏损计入分母。
        s1, s5 = sub["t1"].dropna(), sub["t5"].dropna()
        return {
            "n": int(s1.notna().sum()),
            "T1超额%": round(s1.mean() * 100, 3),
            "T1胜率%": round((s1 > 0).mean() * 100, 1),
            "T5超额%": round(s5.mean() * 100, 3),
            "T5胜率%": round((s5 > 0).mean() * 100, 1),
        }

    has = ev[ev["has_pre_evidence"] == True]  # noqa: E712
    nohas = ev[ev["has_pre_evidence"] == False]  # noqa: E712
    out["事件后续超额"] = {
        "全部事件": blk(ev),
        "有事前证据": blk(has),
        "无事前证据": blk(nohas),
        "有证据_平均绝对涨跌%": round(has["ret"].abs().mean(), 2),
        "无证据_平均绝对涨跌%": round(nohas["ret"].abs().mean(), 2),
    }

    # ---------- 4. 关键窗口超额对比 ----------
    windows = [
        ("2008-05~2009-06", "2008-05-12", "2009-06-30", "上市首年"),
        ("2009-07~2015-06", "2009-07-01", "2015-06-12", "大牛市（创业板大牛+重组）"),
        ("2015-06~2016-01", "2015-06-12", "2016-01-31", "股灾"),
        ("2016-02~2019-12", "2016-02-01", "2019-12-31", "AI 冷板凳期"),
        ("2020-01~2022-12", "2020-01-01", "2022-12-31", "疫情+信创"),
        ("2023-01~2023-12", "2023-01-01", "2023-12-31", "ChatGPT→国产大模型"),
        ("2024-01~2024-09-24", "2024-01-01", "2024-09-24", "AI 调整"),
        ("2024-09-25~2025-12", "2024-09-25", "2025-12-31", "924 行情→DeepSeek→华为"),
        ("2026-01~2026-10", "2026-01-01", "2026-10-29", "2026 回调"),
    ]
    wins = []
    for name, s, e, note in windows:
        g = df.loc[s:e]
        if len(g) < 5:
            continue
        wins.append({
            "窗口": name, "说明": note,
            "交易日": int(len(g)),
            "个股%": round((g["px"].iloc[-1] / g["px"].iloc[0] - 1) * 100, 1),
            "HS300%": round((g["bench"].iloc[-1] / g["bench"].iloc[0] - 1) * 100, 1),
            "超额%": round((g["ret"].sum() - g["ret_b"].sum()) * 100, 1),
            "日波动%": round(g["ret"].std() * 100, 2),
            "事件数": int(((ev["date"] >= s) & (ev["date"] <= e)).sum()),
        })
    out["关键窗口"] = wins

    # ---------- 5. 事件密度 vs 当年波动 ----------
    out["波动与事件密度"] = [
        {"year": int(r["year"]), "日波动%": r["日波动%"], "事件数": r["事件数"],
         "日波动×事件数": round(r["日波动%"] * r["事件数"], 1)}
        for _, r in yr.iterrows()
    ]

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n已写入 {OUT}")


if __name__ == "__main__":
    main()
