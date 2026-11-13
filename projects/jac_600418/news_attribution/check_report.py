"""报告数字自检：REPORT.md 里引用的关键数字 vs 产出文件。"""

import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
rep = (HERE / "REPORT.md").read_text(encoding="utf-8")
summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
stats = json.loads((HERE / "stats.json").read_text(encoding="utf-8"))
study = pd.read_csv(HERE / "event_study.csv")
mt = pd.read_csv(HERE / "news_matches.csv")
ev = pd.read_csv(HERE / "events.csv")
val = pd.read_csv(HERE / "validation.csv")

checks = []


def chk(name, claimed, actual, tol=0.0):
    ok = (claimed == actual) if tol == 0 else abs(claimed - actual) <= tol
    checks.append((name, claimed, actual, "OK" if ok else "MISMATCH"))


chk("事件总数 772", 772, int(len(mt)))
chk("有事前证据 232", 232, summary["有事前证据"])
chk("无事前证据 540", 540, summary["无事前证据"])
chk("有证据率 30.1", 30.1, summary["有事前证据占比%"], 0.05)
chk("涨跌停 130", 130, summary["涨跌停事件"])
chk("涨跌停有证据 40", 40, summary["涨跌停有事前证据"])
chk("涨跌停占比 30.8", 30.8, summary["涨跌停有事前证据占比%"], 0.05)
chk("原始事件 773", 773, int(len(ev)))
chk("校验表行数 773", 773, int(len(val)))

# 分时期
era = stats["分时期证据率"]
chk("2001-2019 23.4", 23.4, era["2001-2019(仅公告)"]["有证据率%"], 0.05)
chk("2020-2026 32.4", 32.4, era["2020-2026(仅公告)"]["有证据率%"], 0.05)
chk("2026-04起 94.1", 94.1, era["2026-04起(有新闻)"]["有证据率%"], 0.05)

# 幅度
amp = stats["证据与幅度"]
chk("有证据平均幅度 6.37", 6.37, amp["True"]["平均绝对涨跌%"], 0.01)
chk("无证据平均幅度 6.52", 6.52, amp["False"]["平均绝对涨跌%"], 0.01)

# 事件研究
for cat, n, t1m, t1win, t5m in [
    ("业绩/财报", 205, -0.244, 45.4, 0.096),
    ("产销数据", 217, 0.142, 43.8, 0.071),
    ("资本运作", 170, -0.148, 37.6, -0.334),
    ("股东行为", 468, -0.0, 43.6, 0.267),
    ("合作/新产品", 64, -0.251, 43.8, -0.559),
    ("股价异动/停复牌", 38, -0.001, 39.5, 0.693),
    ("分红派息", 22, 0.542, 63.6, 0.151),
]:
    r = study[study["category"] == cat].iloc[0]
    chk(f"{cat} n={n}", n, int(r["n"]))
    chk(f"{cat} T1={t1m}", t1m, round(float(r["t1_mean"]), 3), 0.005)
    chk(f"{cat} T1胜率={t1win}", t1win, round(float(r["t1_win"]), 1), 0.05)
    chk(f"{cat} T5={t5m}", t5m, round(float(r["t5_mean"]), 3), 0.005)

# 主因分布
dist = summary["按主因类别分布"]
for cat, n in [("股东行为", 44), ("产销数据", 43), ("业绩/财报", 31), ("媒体报道", 25),
               ("股价异动/停复牌", 20), ("合作/新产品", 12)]:
    chk(f"主因 {cat}={n}", n, dist[cat])

# 复权残差
flagged = val[val["data_flag"].fillna("") != ""]
chk("复权残差假事件 1 条", 1, int(len(flagged)))
if len(flagged):
    print(f"被剔除的事件: {flagged.iloc[0]['date']}  qlib {flagged.iloc[0]['qlib_ret%']:.2f}%  "
          f"新浪 {flagged.iloc[0]['sina_qfq_ret%']:.2f}%")

# REPORT.md 里确实提到了这些数字
for token in ["772", "232", "30.1%", "130", "40", "94.1%", "23.4%", "0.4831",
              "2309", "2005-12-14", "0.99779"]:
    present = token in rep
    checks.append((f"报告含「{token}」", token, "present" if present else "missing",
                   "OK" if present else "MISSING"))

bad = [c for c in checks if c[3] != "OK"]
print(f"\n检查 {len(checks)} 项，失败 {len(bad)} 项")
for name, claimed, actual, status in checks:
    if status != "OK":
        print(f"  [{status}] {name}: 报告/预期={claimed}  实际={actual}")
if not bad:
    print("全部一致 ✓")
