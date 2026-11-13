"""比对真根源与各平台适配稿（路径适配版：dist/trend_combo/<平台>）。"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src" / "article.md"
DIST = HERE / "dist" / "trend_combo"


def split_fm(t):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", t, re.S)
    return (m.group(2) if m else t)


def norm(t):
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


base = norm(split_fm(SRC.read_text(encoding="utf-8")))
print(f"真根源正文 {len(base)} 字，h2 {base.count(chr(10) + '## ')}，"
      f"表格行 {base.count(chr(10) + '|')}，图 {base.count('![')}\n")

for p in ["zhihu", "csdn", "juejin", "baijiahao", "bilibili"]:
    f = DIST / p / "article.md"
    if not f.exists():
        print(f"{p:<10} 缺失")
        continue
    body = norm(split_fm(f.read_text(encoding="utf-8")))
    paras = [q for q in base.split("\n\n") if len(q.strip()) > 20]
    missing = [q for q in paras if q not in body]
    print(f"{p:<10} 字数{len(body):>5}  h2 {body.count(chr(10) + '## '):>2}  "
          f"图 {body.count('!['):>2}  段{len(paras)}  缺段 {len(missing)}  "
          f"整体包含={base in body}")
    for m in missing[:3]:
        print(f"    ✗ 缺段: {m[:90]}…")
