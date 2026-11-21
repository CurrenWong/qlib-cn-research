"""核验分发包：每个平台的 article.md 里，图片引用是否都能在本目录找到、结构是否齐。

配合 check_article.py <path> 使用（那个查数字，这个查文件与结构）。
用法：..\\..\\.venv\\Scripts\\python.exe check_dist.py
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
PLATFORMS = ["zhihu", "csdn", "juejin", "baijiahao", "bilibili"]
IMG = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

print(f"{'平台':10} {'图片':>4} {'缺失':>4} {'h2':>3} {'表格行':>5} {'代码块':>4}  说明")
bad_total = 0
for p in PLATFORMS:
    d = DIST / p
    art = d / "article.md"
    if not art.exists():
        print(f"{p:10} 缺 article.md")
        bad_total += 1
        continue
    txt = art.read_text(encoding="utf-8")
    refs = IMG.findall(txt)
    missing = [r for r in refs if not (d / r).exists()]
    h2 = len(re.findall(r"^##\s", txt, flags=re.M))
    rows = sum(1 for line in txt.splitlines() if line.strip().startswith("|")) 
    code = txt.count("```") // 2
    note = []
    if missing:
        note.append(f"缺图 {missing}")
        bad_total += len(missing)
    if h2 != 8:
        note.append(f"h2={h2}(期望 8)")
        bad_total += 1
    if code < 1:
        note.append("无代码块")
        bad_total += 1
    print(f"{p:10} {len(refs):4} {len(missing):4} {h2:3} {rows:5} {code:4}  {'; '.join(note) or 'ok'}")

print(f"\n共 {len(PLATFORMS)} 个平台，问题 {bad_total} 处")
ck = list(DIST.glob("publish-*.log"))
print("发布日志:", ", ".join(sorted(c.name for c in ck)) or "无")
sys.exit(1 if bad_total else 0)
