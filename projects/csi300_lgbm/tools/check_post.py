"""体检 article.md：结构、图片引用是否落地、表格数。"""

import re
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

POST = Path(_ROOT + r"/projects/csi300_lgbm/docs/post")
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
