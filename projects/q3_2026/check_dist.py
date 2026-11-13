"""对比真根源与各平台适配稿：正文是否被改坏（只读检查）。"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src" / "article.md"


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
    f = HERE / "dist" / p / "article.md"
    if not f.exists():
        print(f"{p:<10} 缺失")
        continue
    body = norm(split_fm(f.read_text(encoding="utf-8")))
    # 平台稿可能插入导语/文末版权块 → 判断真根源正文是否被完整包含
    core = base
    contained = core in body
    # 逐段核对：把真根源按空行切段，看每段是否都在平台稿里
    paras = [p2 for p2 in core.split("\n\n") if len(p2.strip()) > 20]
    missing = [p2 for p2 in paras if p2 not in body]
    print(f"{p:<10} 字数{len(body):>5}  h2 {body.count(chr(10) + '## '):>2}  "
          f"图 {body.count('!['):>2}  段{len(paras)}  缺段 {len(missing)}  "
          f"整体包含={contained}")
    for m in missing[:3]:
        print(f"    ✗ 缺段: {m[:90]}…")
