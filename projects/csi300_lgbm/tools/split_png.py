"""把长图切成便于阅读的页（2x 尺度下每页 4200px ≈ 2100 CSS px），并出一张缩略全图用于自检。"""

from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent
REPORT = HERE / "report"
SRC = REPORT / "report.png"
PAGE_H = 4200

im = Image.open(SRC).convert("RGB")
w, h = im.size
print(f"整图 {w}×{h}，{SRC.stat().st_size/1024:.0f}KB")

# 缩略全图（自检用）
th = im.copy()
th.thumbnail((900, 40000))
th.save(REPORT / "report_thumb.png", optimize=True)
print("缩略:", th.size, f"{(REPORT/'report_thumb.png').stat().st_size/1024:.0f}KB")

y, i = 0, 1
while y < h:
    cut = min(y + PAGE_H, h)
    p = REPORT / f"report_p{i}.png"
    im.crop((0, y, w, cut)).save(p, optimize=True)
    print(f"  第 {i} 页: y={y}~{cut}  {p.stat().st_size/1024:.0f}KB")
    y = cut
    i += 1
print(f"共 {i-1} 页")
