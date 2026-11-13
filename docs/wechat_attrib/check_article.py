"""文章数字自检：article.md 里引用的每个数字 vs comparison.json / 两份报告。

用法：..\\..\\.venv\\Scripts\\python.exe check_article.py
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ART = (HERE / "article.md").read_text(encoding="utf-8")
CMP = json.loads((HERE / "comparison.json").read_text(encoding="utf-8"))
J = CMP["600418"]
I = CMP["002230"]

checks = []


def has(label, token):
    checks.append((label, token, "-", "present" if token in ART else "MISSING"))


def eq(label, claimed, actual, tol=0.0):
    ok = abs(claimed - actual) <= tol if tol else claimed == actual
    checks.append((label, claimed, actual, "OK" if ok else "MISMATCH"))


# ---- 规模类 ----
eq("江淮事件数 773", 773, J["事件总数"])
eq("讯飞事件数 574", 574, I["事件总数"])
eq("事件合计 1347", 1347, J["事件总数"] + I["事件总数"])
eq("江淮有证据率 30.1", 30.1, J["有证据率%"], 0.05)
eq("讯飞有证据率 22.3", 22.3, I["有证据率%"], 0.05)
eq("江淮证据数 232", 232, J["事件总数"] * J["有证据率%"] / 100, 1.2)
eq("讯飞证据数 128", 128, I["事件总数"] * I["有证据率%"] / 100, 1.2)

# ---- 分时期证据率 ----
for code, rec, tag in [("江淮", J, "J"), ("讯飞", I, "I")]:
    e = rec["分时期证据率"]
    eq(f"{code} 2001-2019 率", e["2001-2019(仅公告)"]["有证据率%"],
       {"江淮": 23.4, "讯飞": 21.5}[code], 0.05)
    eq(f"{code} 2020-2026 率", e["2020-2026(仅公告)"]["有证据率%"],
       {"江淮": 32.4, "讯飞": 23.9}[code], 0.05)
    eq(f"{code} 2026-04起 率", e["2026-04起(有新闻)"]["有证据率%"],
       {"江淮": 94.1, "讯飞": 66.7}[code], 0.05)

# ---- 涨跌停 ----
for code, rec, vals in [("江淮", J, {"t1u": 1.93, "w1u": 56.5, "t20u": 0.06, "w20u": 41.3,
                                      "t1d": -0.63, "w1d": 48.6, "t20d": -0.46, "w20d": 34.3,
                                      "n_up": 92, "n_dn": 35}),
                        ("讯飞", I, {"t1u": 1.21, "w1u": 56.9, "t20u": 0.14, "w20u": 50.0,
                                      "t1d": -2.14, "w1d": 32.1, "t20d": 0.19, "w20d": 39.3,
                                      "n_up": 58, "n_dn": 28})]:
    lim = rec["涨跌停"]
    eq(f"{code} 涨停 n", vals["n_up"], lim["涨停"]["n"])
    eq(f"{code} 跌停 n", vals["n_dn"], lim["跌停"]["n"])
    eq(f"{code} 涨停 T1", vals["t1u"], lim["涨停"]["T1超额%"], 0.005)
    eq(f"{code} 涨停 T1胜率", vals["w1u"], lim["涨停"]["T1胜率%"], 0.05)
    eq(f"{code} 涨停 T20", vals["t20u"], lim["涨停"]["T20超额%"], 0.005)
    eq(f"{code} 涨停 T20胜率", vals["w20u"], lim["涨停"]["T20胜率%"], 0.05)
    eq(f"{code} 跌停 T1", vals["t1d"], lim["跌停"]["T1超额%"], 0.005)
    eq(f"{code} 跌停 T1胜率", vals["w1d"], lim["跌停"]["T1胜率%"], 0.05)
    eq(f"{code} 跌停 T20", vals["t20d"], lim["跌停"]["T20超额%"], 0.005)
    eq(f"{code} 跌停 T20胜率", vals["w20d"], lim["跌停"]["T20胜率%"], 0.05)

# ---- 事件后续超额 ----
eq("江淮 有证据 T1胜率 46.2", 46.2, J["事件后续超额"]["有事前证据"]["T1胜率%"], 0.05)
eq("讯飞 有证据 T1胜率 49.6", 49.6, I["事件后续超额"]["有事前证据"]["T1胜率%"], 0.05)
eq("江淮 全部 T1胜率 45.6", 45.6, J["事件后续超额"]["全部"]["T1胜率%"], 0.05)
eq("讯飞 全部 T1胜率 44.9", 44.9, I["事件后续超额"]["全部"]["T1胜率%"], 0.05)

# ---- 类别 ----
CAT = {
    ("江淮", "分红派息"): (22, 0.54, 63.6), ("江淮", "业绩/财报"): (205, -0.24, 45.4),
    ("江淮", "股东行为"): (468, -0.00, 43.6), ("江淮", "资本运作"): (170, -0.15, 37.6),
    ("江淮", "人事治理"): (290, 0.09, 46.2), ("江淮", "合作/新产品"): (64, -0.25, 43.8),
    ("江淮", "股权激励"): (37, -0.39, 40.5), ("江淮", "产销数据"): (217, 0.14, 43.8),
    ("讯飞", "分红派息"): (24, 1.02, 62.5), ("讯飞", "业绩/财报"): (187, 0.27, 51.3),
    ("讯飞", "股东行为"): (363, 0.24, 49.0), ("讯飞", "资本运作"): (236, 0.37, 47.5),
    ("讯飞", "人事治理"): (341, 0.40, 48.1), ("讯飞", "合作/新产品"): (174, -0.16, 40.8),
    ("讯飞", "股权激励"): (222, -0.25, 36.9),
}
for (code, cat), (n, t1, w) in CAT.items():
    st = (J if code == "江淮" else I)["类别事件研究"][cat]
    eq(f"{code} {cat} n", n, st["n"])
    eq(f"{code} {cat} T1", t1, st["T1"], 0.006)
    eq(f"{code} {cat} 胜率", w, st["T1胜率"], 0.05)

# ---- 全历史 ----
eq("江淮 年化 12.14", 12.14, J["全历史"]["年化%"], 0.005)
eq("江淮 基准年化 6.66", 6.66, J["全历史"]["基准年化%"], 0.005)
eq("江淮 累计 1115.4", 1115.4, J["全历史"]["累计%"], 0.05)
eq("江淮 最大回撤 -78.2", -78.2, J["全历史"]["最大回撤%"], 0.05)
eq("讯飞 年化 16.07", 16.07, I["全历史"]["年化%"], 0.005)
eq("讯飞 基准年化 0.27", 0.27, I["全历史"]["基准年化%"], 0.005)
eq("讯飞 累计 1465.2", 1465.2, I["全历史"]["累计%"], 0.05)
eq("讯飞 最大回撤 -64.5", -64.5, I["全历史"]["最大回撤%"], 0.05)
eq("讯飞 交易日 4396", 4396, I["全历史"]["交易日"])
eq("江淮 交易日 5129", 5129, J["全历史"]["交易日"])

# ---- 江淮 8 个事件（图 4）----
import pandas as pd  # noqa: E402

JAC_DIR = ROOT / "projects" / "jac_600418" / "news_attribution"
_ev = pd.read_csv(JAC_DIR / "events.csv")
_ev["date"] = _ev["date"].astype(str)
_mt = pd.read_csv(JAC_DIR / "news_matches.csv")
_mt["event_date"] = _mt["event_date"].astype(str)
_m = _ev.merge(_mt[["event_date", "primary_title"]], left_on="date",
               right_on="event_date", how="left")
JAC_EVENTS = {
    "2018-03-23": (-7.07, -4.20, "控股股东增持计划"),
    "2020-06-12": (9.97, 9.79, "投资协议"),
    "2020-11-04": (9.95, 9.19, "江淮大众合资合作事项的进展公告"),
    "2020-11-26": (-8.15, -8.33, "同一措辞"),
    "2020-12-03": (10.02, 10.22, "交割完成"),
    "2024-07-10": (6.21, 6.53, "业绩预增"),
    "2025-04-08": (-3.92, -5.62, "拟增持"),
    "2026-07-07": (-6.75, -5.72, "首次回购"),
}
for d, (ret, exc, kw) in JAC_EVENTS.items():
    r = _m[_m["date"] == d]
    eq(f"江淮事件 {d} 涨跌", ret, float(r["ret"].iloc[0]), 0.005)
    eq(f"江淮事件 {d} 超额", exc, float(r["excess"].iloc[0]), 0.005)
    has(f"江淮事件 {d} 在文中", d)
    has(f"江淮事由「{kw}」", kw)

# ---- 文章里必须出现的关键表述 ----
for token in ["1347", "4665", "603", "30.1%", "22.3%", "94.1%", "66.7%", "23.4%", "21.5%",
              "32.4%", "23.9%", "0.999738", "2005-12-14", "+7.32%", "-6.18%",
              "773 次", "574 次", "2309 条", "2356 条", "354 条", "249 条",
              "+262.7", "+61.4", "+7.9", "-10.8", "1263.3", "35.2", "38.5", "-28.9",
              "-0.551%", "32.1%"]:
    has(f"含「{token}」", token)

# ---- 不该出现的：代码路径 / 复现承诺 ----
for token in ["D:\\Project", "check_report.py", "一键复跑", "复现"]:
    checks.append((f"不含「{token}」", token, "-",
                   "OK" if token not in ART else "STILL_PRESENT"))

bad = [c for c in checks if c[-1] not in ("OK", "present")]
print(f"\n检查 {len(checks)} 项，失败 {len(bad)} 项")
for name, claimed, actual, status in checks:
    if status not in ("OK", "present"):
        print(f"  [{status}] {name}: 文章/预期={claimed}  实际={actual}")
if not bad:
    print("全部一致 ✓")
