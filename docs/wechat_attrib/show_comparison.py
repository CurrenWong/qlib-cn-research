"""把 comparison.json 打印成文章可直接引用的表（并做 NaN 口径修正）。"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "comparison.json").read_text(encoding="utf-8"))

for code, v in d.items():
    print(f"===== {v['名称']} {code} | 事件 {v['事件总数']} | 有证据率 {v['有证据率%']}% "
          f"| 区间 {v['事件区间']}")
    print("  全历史:", json.dumps(v["全历史"], ensure_ascii=False))
    lim = v["涨跌停"]
    print(f"  涨跌停 {lim['总数']}（涨{lim['涨停数']}/跌{lim['跌停数']}）")
    print("    涨停:", json.dumps(lim["涨停"], ensure_ascii=False))
    print("    跌停:", json.dumps(lim["跌停"], ensure_ascii=False))
    for k, vv in v["事件后续超额"].items():
        print(f"    {k}: {json.dumps(vv, ensure_ascii=False)}")
    print("  分时期证据率:", json.dumps(v["分时期证据率"], ensure_ascii=False))
    print()

print("===== 类别事件研究并排 =====")
cats = sorted(set(d["600418"]["类别事件研究"]) | set(d["002230"]["类别事件研究"]),
              key=lambda c: -d["002230"]["类别事件研究"].get(c, {}).get("n", 0))
print(f"{'类别':<14}{'江淮n':>6}{'江淮T1':>9}{'江淮胜率':>9}"
      f"{'讯飞n':>7}{'讯飞T1':>9}{'讯飞胜率':>9}")
for c in cats:
    a = d["600418"]["类别事件研究"].get(c, {})
    b = d["002230"]["类别事件研究"].get(c, {})
    print(f"{c:<14}{a.get('n', '-'):>6}{a.get('T1', '-'):>9}{a.get('T1胜率', '-'):>9}"
          f"{b.get('n', '-'):>7}{b.get('T1', '-'):>9}{b.get('T1胜率', '-'):>9}")

print("\n===== 主因类别表现并排 =====")
for code, v in d.items():
    print(f"-- {v['名称']}")
    for k, vv in list(v["主因类别表现"].items())[:8]:
        print(f"   {k:<14} n={vv['n']:<5} 平均超额{vv['平均超额']:>6}  胜率{vv['胜率']}%")
