"""把长图 PNG 压到能直接在聊天里预览的尺寸（≤2MB）。

用法：..\\..\\.venv\\Scripts\\python.exe tools\\shrink_png.py
产出：report\\trend_combo_report_small.png
"""

from pathlib import Path

from PIL import Image

REPORT = Path(__file__).resolve().parent.parent / "report"
src = REPORT / "trend_combo_report.png"
out = REPORT / "trend_combo_report_small.png"

im = Image.open(src).convert("RGB")
w, h = im.size
target_w = 1500
new_h = int(h * target_w / w)
im = im.resize((target_w, new_h), Image.LANCZOS)
im.save(out, optimize=True)
print(f"{src.name} {w}×{h} → {out.name} {im.size}  {out.stat().st_size/1024:.0f} KB")

if out.stat().st_size > 2 * 1024 * 1024:
    q = REPORT / "trend_combo_report_small.jpg"
    im2 = im.resize((1250, int(im.size[1] * 1250 / im.size[0])), Image.LANCZOS)
    im2.save(q, quality=76, optimize=True)
    print(f"仍偏大，另存 JPEG：{q.name}  {im2.size}  {q.stat().st_size/1024:.0f} KB")
