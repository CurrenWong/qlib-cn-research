"""核验分发包：每个平台的 article.md 里，图片引用是否都能在本目录找到、结构是否齐。

期望值**从真源 article.md 现算**（不写死）——否则换一篇文章就得改这个脚本，
上一期就是被写死的「h2=8、代码块 1」卡住过。

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
SRC = HERE / "article.md"

# ---- 期望值：从真源现算 ----
if SRC.exists():
    src = SRC.read_text(encoding="utf-8")
    EXP_H2 = len(re.findall(r"^##\s", src, flags=re.M))
    EXP_ROWS = sum(1 for line in src.splitlines() if line.strip().startswith("|"))
    EXP_CODE = src.count("```") // 2
    EXP_IMGS = len(re.findall(r"【插图\s*\d+：", src))
else:
    EXP_H2 = EXP_ROWS = EXP_CODE = EXP_IMGS = -1

print(f"真源期望：图 {EXP_IMGS} 张 / h2 {EXP_H2} / 表格行 {EXP_ROWS} / 代码块 {EXP_CODE}")
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
    # CSDN 会自动多插一张封面首图，所以图片数允许 +1
    if len(refs) not in (EXP_IMGS, EXP_IMGS + 1):
        note.append(f"图 {len(refs)}(期望 {EXP_IMGS})")
        bad_total += 1
    if h2 != EXP_H2:
        note.append(f"h2={h2}(期望 {EXP_H2})")
        bad_total += 1
    if code != EXP_CODE:
        note.append(f"代码块 {code}(期望 {EXP_CODE})")
        bad_total += 1
    if not (d / "meta.json").exists():
        note.append("缺 meta.json")
        bad_total += 1
    if not (d / "checklist.md").exists():
        note.append("缺 checklist.md")
        bad_total += 1
    print(f"{p:10} {len(refs):4} {len(missing):4} {h2:3} {rows:5} {code:4}  {'; '.join(note) or 'ok'}")

print(f"\n共 {len(PLATFORMS)} 个平台，问题 {bad_total} 处")
ck = list(DIST.glob("publish-*.log"))
print("发布日志:", ", ".join(sorted(c.name for c in ck)) or "无")
sys.exit(1 if bad_total else 0)
