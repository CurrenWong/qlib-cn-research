"""归因结果的统计维度汇总（供 REPORT.md 取数）。"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
mt = pd.read_csv(HERE / "news_matches.csv")
mt["date"] = mt["event_date"].astype(str)
mt["decade"] = mt["date"].str[:3] + "0s"
mt["abs_ret"] = mt["ret"].abs()

out = {}

# 1) 有/无事前证据 的幅度对比
g = mt.groupby("has_pre_evidence")["abs_ret"].agg(["count", "mean", "median"])
out["证据与幅度"] = {
    str(k): {"n": int(v["count"]), "平均绝对涨跌%": round(v["mean"], 2),
             "中位绝对涨跌%": round(v["median"], 2)}
    for k, v in g.iterrows()
}

# 2) 分年代：有事前证据率（注意覆盖偏差：新闻只覆盖 2026-04 起）
dec = mt.groupby("decade").agg(
    n=("event_date", "count"),
    有证据率=("has_pre_evidence", lambda s: round(s.mean() * 100, 1)),
    平均绝对涨跌=("abs_ret", lambda s: round(s.mean(), 2)),
    涨跌停数=("is_limit", "sum"),
)
out["分年代"] = {k: {kk: (int(vv) if kk in ("n", "涨跌停数") else float(vv))
                     for kk, vv in v.items()} for k, v in dec.iterrows()}

# 3) 主因类别 → 平均超额/胜率
cat = mt.groupby("primary_category").agg(
    n=("event_date", "count"),
    平均超额=("excess", lambda s: round(s.mean(), 2)),
    胜率=("excess", lambda s: round((s > 0).mean() * 100, 1)),
    平均绝对涨跌=("abs_ret", lambda s: round(s.mean(), 2)),
).sort_values("n", ascending=False)
out["主因类别表现"] = {k: {kk: (int(vv) if kk == "n" else float(vv)) for kk, vv in v.items()}
                       for k, v in cat.iterrows()}

# 4) 涨跌停事件：有/无事前证据
lim = mt[mt["is_limit"] == True]  # noqa: E712
out["涨跌停"] = {
    "总数": int(len(lim)),
    "有事前证据": int(lim["has_pre_evidence"].sum()),
    "无事前证据": int((~lim["has_pre_evidence"]).sum()),
    "有证据占比%": round(float(lim["has_pre_evidence"].mean() * 100), 1),
    "涨停数": int((lim["ret"] > 0).sum()),
    "跌停数": int((lim["ret"] < 0).sum()),
}

# 5) 月度产销快报：公告日与事件日的重合情况
ann = json.loads((HERE / "news_cache" / "cninfo.json").read_text(encoding="utf-8"))
sx = pd.DataFrame(ann)
sx["date"] = sx["date"].astype(str).str[:10]
sx_monthly = sx[sx["title"].str.contains("产、销|产销快报", regex=True)]
out["月度产销快报"] = {
    "公告条数": int(len(sx_monthly)),
    "覆盖年份": f"{sx_monthly['date'].min()[:4]}~{sx_monthly['date'].max()[:4]}",
}

# 6) 2026 年有新闻覆盖的事件 vs 2001-2019 只有公告覆盖的事件
mt["era"] = "2001-2019(仅公告)"
mt.loc[mt["date"] >= "2020-01-01", "era"] = "2020-2026(仅公告)"
mt.loc[mt["date"] >= "2026-04-01", "era"] = "2026-04起(有新闻)"
era = mt.groupby("era").agg(n=("event_date", "count"),
                            有证据率=("has_pre_evidence", lambda s: round(s.mean() * 100, 1)))
out["分时期证据率"] = {k: {"n": int(v["n"]), "有证据率%": float(v["有证据率"])} for k, v in era.iterrows()}

(HERE / "stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2))
