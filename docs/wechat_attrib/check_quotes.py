"""找出引号不成对的行（修复 fix_quotes 留下的落单引号）。"""

from pathlib import Path

p = Path(__file__).resolve().parent / "article.md"
for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    if line.count("“") != line.count("”"):
        print(f"{i}: 「{line}」  开{line.count('“')} 闭{line.count('”')}")
print("---- 末 5 行 ----")
for line in p.read_text(encoding="utf-8").splitlines()[-5:]:
    print(repr(line))
