"""把长图切成页 + 出缩略图。用法：python split_any.py portfolio_v2.png [页高]"""

import sys
from pathlib import Path

from PIL import Image

REPORT = Path(__file__).resolve().parent.parent / "report"
src = REPORT / (sys.argv[1] if len(sys.argv) > 1 else "portfolio_v2.png")
page_h = int(sys.argv[2]) if len(sys.argv) > 2 else 4200

im = Image.open(src).convert("RGB")
w, h = im.size
stem = src.stem
print(f"整图 {w}×{h}，{src.stat().st_size/1024:.0f}KB")
th = im.copy()
th.thumbnail((900, 40000))
th.save(REPORT / f"{stem}_thumb.png", optimize=True)
print("缩略:", th.size)

y, i = 0, 1
while y < h:
    cut = min(y + page_h, h)
    p = REPORT / f"{stem}_p{i}.png"
    im.crop((0, y, w, cut)).save(p, optimize=True)
    print(f"  第 {i} 页: y={y}~{cut}  {p.stat().st_size/1024:.0f}KB")
    y = cut
    i += 1
print(f"共 {i-1} 页")
