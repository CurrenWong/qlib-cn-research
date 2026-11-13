"""体检粗体：每个段落里最多一处 **粗体**（平台转换只保证第一处生效）。"""

import re
from pathlib import Path

p = Path(r"D:\Project\qlib\projects\csi300_lgbm\docs\post\article.md")
md = p.read_text(encoding="utf-8")
body = re.sub(r"(?s)^---\n.*?\n---\n", "", md)

blocks, cur = [], []
for line in body.splitlines():
    if line.strip() == "":
        if cur:
            blocks.append("\n".join(cur))
            cur = []
    else:
        cur.append(line)
if cur:
    blocks.append("\n".join(cur))

bad = []
for b in blocks:
    n = b.count("**")
    if n > 2 or (n == 1):
        bad.append((n, b[:110]))
print("总块数:", len(blocks))
print("粗体标记 >2 处 或落单的块：")
for n, t in bad:
    print(f"  [{n}] {t}")

listlead = [b for b in blocks if re.match(r"^\s*(>\s*)?[-*+]\s*\*\*", b)]
print("\n列表项开头的粗体:", len(listlead))
for b in listlead:
    print("   ", b[:100])
