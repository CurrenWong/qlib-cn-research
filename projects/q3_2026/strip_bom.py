# -*- coding: utf-8 -*-
"""去掉 article.md 的 BOM，并把开头的 H1 摘出来交给模板（正文不再重复标题）。"""
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

p = Path(_ROOT + r"/projects/q3_2026/article.md")
raw = p.read_bytes()
had_bom = raw.startswith(b"\xef\xbb\xbf")
t = raw.decode("utf-8-sig")
lines = t.splitlines()
while lines and not lines[0].strip():
    lines.pop(0)
if lines[0].startswith("# "):
    print("摘掉 H1:", lines[0][2:].strip())
    lines.pop(0)
while lines and not lines[0].strip():
    lines.pop(0)
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("原文件有 BOM:", had_bom, "| 现首行:", lines[0][:40])
print("现在是否还有 BOM:", p.read_bytes().startswith(b"\xef\xbb\xbf"))
