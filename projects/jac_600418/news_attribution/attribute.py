"""事件 ↔ 新闻/公告匹配（v2：带因果方向判定）+ 公告类别事件研究。

v2 相比 v1 的关键改进：
  1. **因果方向**：区分「事前证据」（T-1 / T 开盘前，可以是原因）与「事后报道」
     （T 盘中 / T 收盘后 / T+1，多半是结果）。归因只用事前证据，事后单列。
  2. **证据强度排序**：标题里点名「江淮/600418」的强于列表类点名文章；
     泛行业综述（"融资客控盘比例超一成个股""主力动向"）降权。
  3. 巨潮公告只有日期，按"披露日 ≤ 事件日"处理（收盘后披露 → 影响次日）。

产出：news_matches.csv / event_study.csv / summary.json
"""

from __future__ import annotations

import json
import sys
from bisect import bisect_left
from pathlib import Path

import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# ------------------------------------------------------------------ 公告类别
CATEGORY_RULES: list[tuple[str, list[str], int]] = [
    ("业绩/财报", ["业绩预告", "业绩快报", "年度报告", "半年度报告", "季度报告",
                "净利润", "营业收入", "预增", "预亏", "亏损", "扭亏", "业绩说明会"], 95),
    ("风险/监管", ["诉讼", "仲裁", "立案", "处罚", "问询函", "关注函", "监管函",
                "违规", "失信", "被执行", "风险提示", "担保", "债务", "冻结"], 90),
    ("股价异动/停复牌", ["异常波动", "停牌", "复牌", "重点监控", "严重异常"], 88),
    ("产销数据", ["产、销", "产销快报", "销量快报", "产销量"], 70),
    ("合作/新产品", ["合作", "战略合作", "协议", "中标", "订单", "车型", "量产",
                 "上市", "发布", "工厂", "基地", "智能网联", "研发"], 75),
    ("资本运作", ["非公开发行", "定向增发", "可转债", "配股", "募集资金", "发行股份",
                "募投", "现金管理", "对外投资", "设立"], 72),
    ("股东行为", ["回购", "增持", "减持", "解除限售", "限售股上市流通", "股份质押",
                "股东", "权益变动", "举牌"], 70),
    ("股权激励", ["股权激励", "限制性股票", "股票期权", "员工持股"], 68),
    ("分红派息", ["利润分配", "分红", "派息", "转增", "权益分派"], 45),
    ("人事治理", ["辞职", "聘任", "选举", "董事会", "监事会", "高管"], 40),
    ("股东会决议", ["股东会", "股东大会决议", "章程"], 35),
]
CATEGORY_ORDER = [c for c, _, _ in CATEGORY_RULES]

ENTITY_WORDS = ["江淮", "600418", "JAC", "合肥", "瑞风", "星锐", "同悦",
                "江淮大众", "江淮蔚来", "悍途", "嘉悦", "尊界"]

# 泛行业/点名列表类文章：提到江淮但不是关于江淮的报道
GENERIC_PATTERNS = ["名单", "附股", "个股", "净流出", "净流入", "特大单", "融资客",
                    "主力动向", "定增累计", "累计募资", "收评", "午评", "开盘",
                    "收盘综述", "板块", "行业", "复盘", "涨幅榜", "跌幅榜"]


def classify(title: str) -> str:
    for cat, kws, _ in CATEGORY_RULES:
        for kw in kws:
            if kw in title:
                return cat
    return "其他"


def priority(cat: str) -> int:
    for c, _, p in CATEGORY_RULES:
        if c == cat:
            return p
    return 20


def mentions_co(title: str) -> bool:
    t = title.upper()
    return any(w.upper() in t for w in ENTITY_WORDS)


def is_generic(title: str) -> bool:
    return any(p in title for p in GENERIC_PATTERNS)


def load_news(name: str) -> pd.DataFrame:
    p = HERE / "news_cache" / f"{name}.json"
    rows = json.loads(p.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)
    df["date"] = df["date"].astype(str).str[:10]
    return df


def build_daily_frame() -> pd.Series:
    """完整交易日的超额收益序列（600418 - 沪深300）。"""
    import numpy as np

    qlib_dir = Path(_ROOT + r"/qlib_data/cn_data_2026")
    calendar = [x.strip() for x in (qlib_dir / "calendars" / "day.txt").read_text().splitlines() if x.strip()]

    def load(sym, field):
        arr = np.fromfile(qlib_dir / "features" / sym / f"{field}.day.bin", dtype=np.float32)
        start = int(arr[0])
        return pd.Series(arr[1:], index=calendar[start : start + len(arr) - 1], dtype="float64")

    excess = load("sh600418", "adjclose").pct_change() - load("sh000300", "close").pct_change()
    excess.name = "excess"
    return excess


def main():
    # 用 validation.csv（已与新浪前复权交叉校验），剔除复权残差造成的假事件
    ev = pd.read_csv(HERE / "validation.csv")
    n_all = len(ev)
    ev = ev[ev["data_flag"].fillna("") == ""].copy()
    print(f"事件 {n_all} 条 → 剔除复权残差假事件 {n_all - len(ev)} 条 → 有效 {len(ev)} 条")
    ev["date"] = ev["date"].astype(str)
    ann = load_news("cninfo")
    news = load_news("em_news")
    ann["category"] = ann["title"].map(classify)

    # 公告按日期索引
    ann_by_date: dict[str, list[dict]] = {}
    for _, r in ann.iterrows():
        ann_by_date.setdefault(r["date"], []).append(
            {"dt": r["date"] + " 00:00:00", "title": r["title"], "url": r["url"],
             "source": "巨潮公告", "category": r["category"]}
        )
    news_by_date: dict[str, list[dict]] = {}
    for _, r in news.iterrows():
        if not mentions_co(r["title"]) and not mentions_co(str(r["content"])[:200]):
            continue
        news_by_date.setdefault(r["date"], []).append(
            {"dt": r["date"], "title": r["title"], "url": r["url"],
             "source": f"新闻/{r['media']}", "category": "媒体报道",
             "content": str(r["content"])[:400]}
        )

    rows = []
    for _, e in ev.iterrows():
        t = e["date"]
        prev = (pd.Timestamp(t) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        nxt = (pd.Timestamp(t) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        # ---------- 候选池 ----------
        cands = []
        for d in (prev, t):
            for c in ann_by_date.get(d, []):
                rel = "T-1公告" if d == prev else "T日公告"
                cands.append({**c, "relation": rel, "kind": "公告"})
        for c in news_by_date.get(t, []):
            ts = c["dt"][11:16] if len(c["dt"]) > 15 else "00:00"
            if ts < "09:30":
                rel = "T盘前"
            elif ts <= "15:00":
                rel = "T盘中"
            else:
                rel = "T盘后"
            cands.append({**c, "relation": rel, "kind": "新闻"})
        for c in news_by_date.get(prev, []):
            cands.append({**c, "relation": "T-1新闻", "kind": "新闻"})
        post = [{**c, "relation": "T+1", "kind": "新闻"} for c in news_by_date.get(nxt, [])]

        # ---------- 打分 ----------
        for c in cands:
            s = priority(c["category"])
            if c["kind"] == "新闻":
                if mentions_co(c["title"]):
                    s += 45
                else:
                    s += 10
                if is_generic(c["title"]):
                    s -= 40
                if c["relation"] in ("T盘前", "T-1新闻"):
                    s += 20
                elif c["relation"] == "T盘中":
                    s += 0
                else:
                    s -= 30
            else:
                s += 25 if c["relation"] == "T-1公告" else 15
            c["score"] = s

        cands.sort(key=lambda c: -c["score"])
        pre = [c for c in cands if c["relation"] in ("T-1公告", "T日公告", "T盘前", "T-1新闻", "T盘中")]
        primary = pre[0] if pre else None

        rows.append(
            {
                "event_date": t,
                "tier": e["tier"],
                "ret": e["ret"],
                "ret_bench": e["ret_bench"],
                "excess": e["excess"],
                "vol_ratio": e["vol_ratio"],
                "is_limit": e["is_limit"],
                "fwd5": e["fwd5"],
                "has_pre_evidence": bool(pre),
                "primary_relation": primary["relation"] if primary else "",
                "primary_kind": primary["kind"] if primary else "",
                "primary_category": primary["category"] if primary else "无事前证据",
                "primary_title": primary["title"] if primary else "",
                "primary_source": primary["source"] if primary else "",
                "primary_url": primary["url"] if primary else "",
                "primary_score": primary["score"] if primary else 0,
                "n_pre": len(pre),
                "n_post": len(post),
                "post_titles": " | ".join(c["title"][:50] for c in post[:3]),
                "all_pre_titles": " | ".join(c["title"][:70] for c in pre[:5]),
            }
        )

    mt = pd.DataFrame(rows)
    mt.to_csv(HERE / "news_matches.csv", index=False, encoding="utf-8-sig")

    # ---------------- 公告类别事件研究 ----------------
    study = build_event_study(ann)
    study.to_csv(HERE / "event_study.csv", index=False, encoding="utf-8-sig")

    lim = mt[mt["is_limit"] == True]  # noqa: E712
    summary = {
        "事件总数": int(len(mt)),
        "有事前证据": int(mt["has_pre_evidence"].sum()),
        "无事前证据": int((~mt["has_pre_evidence"]).sum()),
        "有事前证据占比%": round(float(mt["has_pre_evidence"].mean() * 100), 1),
        "涨跌停事件": int(len(lim)),
        "涨跌停有事前证据": int(lim["has_pre_evidence"].sum()),
        "涨跌停有事前证据占比%": round(float(lim["has_pre_evidence"].mean() * 100), 1),
        "按主因类别分布": mt["primary_category"].value_counts().to_dict(),
        "涨跌停按主因分布": lim["primary_category"].value_counts().to_dict(),
        "公告类别事件研究": {
            r["category"]: {
                "n": int(r["n"]),
                "T0超额%": round(float(r["t0_mean"]), 3),
                "T1超额%": round(float(r["t1_mean"]), 3),
                "T1中位%": round(float(r["t1_median"]), 3),
                "T1胜率%": round(float(r["t1_win"]), 1),
                "T5超额%": round(float(r["t5_mean"]), 3),
            }
            for _, r in study.iterrows()
        },
    }
    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def build_event_study(ann: pd.DataFrame) -> pd.DataFrame:
    """公告类别 → 公告后超额收益（T0 当日 / T1 次日 / T5 五日后）。"""
    full = build_daily_frame()
    cal = list(full.index)
    vals = full.to_numpy()

    out = []
    for cat in CATEGORY_ORDER:
        sub = ann[ann["category"] == cat]
        if not len(sub):
            continue
        t0, t1, t5 = [], [], []
        for date in sub["date"]:
            idx = bisect_left(cal, str(date)[:10])
            if idx >= len(cal):
                continue
            if pd.notna(vals[idx]):
                t0.append(vals[idx])
            if idx + 1 < len(cal) and pd.notna(vals[idx + 1]):
                t1.append(vals[idx + 1])
            if idx + 5 < len(cal) and pd.notna(vals[idx + 5]):
                t5.append(vals[idx + 5])
        if not t1:
            continue
        s0, s1 = pd.Series(t0), pd.Series(t1)
        s5 = pd.Series(t5) if t5 else pd.Series([float("nan")])
        out.append(
            {
                "category": cat,
                "n": len(s1),
                "t0_mean": s0.mean() * 100,
                "t0_win": (s0 > 0).mean() * 100,
                "t1_mean": s1.mean() * 100,
                "t1_median": s1.median() * 100,
                "t1_win": (s1 > 0).mean() * 100,
                "t5_mean": s5.mean() * 100,
                "t5_win": (s5 > 0).mean() * 100,
            }
        )
    return pd.DataFrame(out)


if __name__ == "__main__":
    main()
