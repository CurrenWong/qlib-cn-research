# -*- coding: utf-8 -*-
"""下载巨潮 PDF 并抽文本。"""
import subprocess
import sys
from pathlib import Path

import requests

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

OUT = Path(_ROOT + r"/projects/q3_2026/pdf")
OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
     "Referer": "http://www.cninfo.com.cn/"}

DOCS = {
    "002230_2026Q3": "http://static.cninfo.com.cn/finalpage/2026-10-20/1225611744.pdf",
    "600418_2026Q3": "http://static.cninfo.com.cn/finalpage/2026-10-31/1225648639.PDF",
}

for name, url in DOCS.items():
    f = OUT / f"{name}.pdf"
    if not (f.exists() and f.stat().st_size > 50000):
        r = requests.get(url, headers=H, timeout=180)
        print(f"{name}: HTTP {r.status_code} {len(r.content) // 1024}KB", end=" ")
        if r.content[:4] != b"%PDF":
            print("不是 PDF:", r.content[:120])
            continue
        f.write_bytes(r.content)
        print("ok")
    else:
        print(f"{name}: 已存在 {f.stat().st_size // 1024}KB")

# 抽文本
import pdfplumber  # noqa: E402

for f in sorted(OUT.glob("*.pdf")):
    txt = OUT / (f.stem + ".txt")
    if txt.exists() and txt.stat().st_size > 1000:
        print(f"{f.name}: 文本已存在 {txt.stat().st_size // 1024}KB")
        continue
    pages = []
    with pdfplumber.open(f) as pdf:
        for i, pg in enumerate(pdf.pages):
            pages.append(f"\n===== PAGE {i + 1} =====\n" + (pg.extract_text() or ""))
    body = "\n".join(pages)
    txt.write_text(body, encoding="utf-8")
    print(f"{f.name}: {len(pdf.pages)} 页 -> {len(body)} 字")
