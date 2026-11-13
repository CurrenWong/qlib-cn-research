"""体检 article.md：结构、图片引用是否落地、表格数。"""

import re
from pathlib import Path

POST = Path(r"D:\Project\qlib\projects\csi300_lgbm\docs\post")
md = (POST / "article.md").read_text(encoding="utf-8")

print("字符数:", len(md))
print("\n== 标题结构 ==")
for m in re.finditer(r"(?m)^(#{1,3}) (.+)$", md):
    print("  " * (len(m.group(1)) - 1) + m.group(2))

imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
print(f"\n== 图片 {len(imgs)} 处 ==")
missing = []
for p in imgs:
    ok = (POST / p).exists()
    if not ok:
        missing.append(p)
    print(("  ✓ " if ok else "  ✗ ") + p)
print("缺图:", missing or "无")

tables = len(re.findall(r"(?m)^\|.*\|$", md))
print("\n表格行数:", tables)
print("代码块:", md.count("```"))
print("引用块行:", len(re.findall(r"(?m)^> ", md)))
