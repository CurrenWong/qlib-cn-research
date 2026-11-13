"""检查并修掉公众号/多平台 Markdown 的两个已知坑（来自 multi-platform-post 坑 16）：

  ① 加粗里带句末标点（。？！，、；：）→ 把标点挪到加粗外面
  ② 加粗跨行（某一行 ** 数量为奇数）→ 报告出来人工处理

用法：..\\..\\.venv\\Scripts\\python.exe fix_bold.py [--check]
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = [HERE / "article.md", HERE / "src" / "article.md"]
PUNCT = "。？！，、；：…"


def fix_text(t):
    out = []
    changed = 0
    # **xxx。** → **xxx**。
    def repl(m):
        nonlocal changed
        inner, punct = m.group(1), m.group(2)
        changed += 1
        return f"**{inner}**{punct}"
    t2 = re.sub(r"\*\*([^*\n]*?)([" + PUNCT + r"]+)\*\*", repl, t)
    return t2, changed


def check(t):
    problems = []
    for i, line in enumerate(t.split("\n"), 1):
        if line.count("**") % 2 == 1:
            problems.append((i, line.strip()[:90]))
    return problems


def main():
    check_only = "--check" in sys.argv
    for f in FILES:
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        t2, n = fix_text(t)
        probs = check(t2)
        if check_only:
            print(f"{f.name}: 需修 {n} 处，跨行加粗 {len(probs)} 处")
            for i, s in probs:
                print(f"   行{i}: {s}")
        else:
            if n:
                f.write_text(t2, encoding="utf-8")
            print(f"{f.name}: 修掉句末标点 {n} 处，跨行加粗 {len(probs)} 处")
            for i, s in probs:
                print(f"   ⚠️ 行{i}: {s}")


if __name__ == "__main__":
    main()
