"""修 fix_bold.py 的算法 bug + 修复已损坏的 3 处加粗标记。

**bug**：`\\*\\*(.+?)([。，；！？：])\\*\\*` 是非贪婪的，但 `(.+?)` 可以**跨过已经闭合的 `**`**，
于是会从一处加粗的开标记一路吃到后一处的标点，把中间的内容整段吞进加粗。
真实案例：
    原文  任一…不超过 15%；**BIAS120 > +20% …不超过 20%**——
    错误  任一…不超过 15%**；BIAS120 > +20% …不超过 20%**——   ← 「15%」被卷进加粗，标点跑到加粗外
**正确算法**：先按 `\\*\\*(.+?)\\*\\*` 把每个加粗片段（非贪婪，天然不跨段）切出来，
再看片段**结尾**是不是句末标点，是就把标点挪到片段外面。
"""

import re
import sys
from pathlib import Path

# ---- 1. 修复文章里已经损坏的 3 处 ----
BAD_TO_GOOD = [
    ("分位 95**，最热的一个**。", "分位 95，**最热的一个**。"),
    ("任一申万一级行业权重不超过 15%**；BIAS120 > +20% 的（极热的）行业合计不超过 20%**——",
     "任一申万一级行业权重不超过 15%；**BIAS120 > +20% 的（极热的）行业合计不超过 20%**——"),
    ("如果某个行业 BIAS120 已经 < -30%（极度超卖）**，不要因为它跌了就砍**——",
     "如果某个行业 BIAS120 已经 < -30%（极度超卖），**不要因为它跌了就砍**——"),
]

NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def fix_bold(text: str) -> str:
    """把加粗片段**结尾**的句末标点挪到片段外面（不跨段）。"""
    span = re.compile(r"\*\*(.+?)\*\*", re.S)

    def repl(m):
        c = m.group(1)
        if c and c[-1] in "。，；！？：":
            return "**" + c[:-1] + "**" + c[-1]
        return m.group(0)

    return span.sub(repl, text)


def main() -> int:
    targets = [Path(p) for p in sys.argv[1:]] or [
        Path(r"projects\style_post\article.md"),
        Path(r"projects\style_post\src\article.md"),
        Path(r"projects\style_post\dist\zhihu\article.md"),
        Path(r"projects\style_post\dist\csdn\article.md"),
        Path(r"projects\style_post\dist\juejin\article.md"),
        Path(r"projects\style_post\dist\baijiahao\article.md"),
        Path(r"projects\style_post\dist\bilibili\article.md"),
    ]
    bad = 0
    for p in targets:
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        before = NUM.findall(t)
        for a, b in BAD_TO_GOOD:
            n = t.count(a)
            if n:
                t = t.replace(a, b)
                print(f"  {p.name}: 修 {n} 处「{a[:22]}…」")
        t2 = fix_bold(t)
        changed = t2 != t
        t = t2
        after = NUM.findall(t)
        # 校验：没有奇数个 ** 的行
        odd = [i + 1 for i, ln in enumerate(t.splitlines()) if ln.count("**") % 2]
        if odd:
            print(f"  ⚠ {p}: 还有 {len(odd)} 行 ** 为奇数: {odd[:5]}")
            bad += 1
        if before != after:
            print(f"  ✗ {p}: 数字序列变了！")
            bad += 1
        p.write_text(t, encoding="utf-8")
        print(f"{p}: 写入（标点外移改动 {changed} 处，数字 {len(after)} 个不变，** 奇数行 {len(odd)}）")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
