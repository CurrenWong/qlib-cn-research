"""把 article.md 正文里的 ASCII 直引号成对替换成中文弯引号（“ ”）。"""

import re
from pathlib import Path

p = Path(__file__).resolve().parent / "article.md"
text = p.read_text(encoding="utf-8")

out, open_q = [], True
for ch in text:
    if ch == '"':
        out.append("“" if open_q else "”")
        open_q = not open_q
    else:
        out.append(ch)
new = "".join(out)
if open_q:
    print("警告：引号数量为奇数，未完全配对")
n = text.count('"')
p.write_text(new, encoding="utf-8")
print(f"替换 {n} 个直引号 -> {new.count('“')} 对中文引号")
