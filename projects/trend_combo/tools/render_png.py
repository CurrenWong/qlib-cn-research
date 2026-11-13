"""HTML → PNG（headless Chrome 截图 + 裁掉尾部空白 + 分页，便于手机看）。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\render_png.py [输入html] [输出png]
默认：report\\trend_combo_report.html → report\\trend_combo_report.png
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent / "report"
HTML = REPORT / (sys.argv[1] if len(sys.argv) > 1 else "trend_combo_report.html")
OUT = REPORT / (sys.argv[2] if len(sys.argv) > 2 else "trend_combo_report.png")

WIDTH = 1240
MAX_H = 30000
PAGE_H = 3200

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    for p in CANDIDATES:
        if Path(p).exists():
            return p
    for name in ("chrome", "msedge"):
        exe = shutil.which(name)
        if exe:
            return exe
    raise SystemExit("找不到 Chrome / Edge")


def main():
    br = find_browser()
    tmp = REPORT / "_full.png"
    cmd = [br, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=2", f"--window-size={WIDTH},{MAX_H}",
           f"--screenshot={tmp}", "--virtual-time-budget=15000", HTML.resolve().as_uri()]
    print("浏览器:", br)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if not tmp.exists():
        print("截图失败:", r.stdout[-800:], r.stderr[-800:])
        sys.exit(1)

    im = Image.open(tmp).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = px[2, h - 5]
    print(f"原始截图 {w}×{h}，底部背景 {bg}")

    def row_diff(y):
        return any(abs(px[x, y][0] - bg[0]) + abs(px[x, y][1] - bg[1]) +
                   abs(px[x, y][2] - bg[2]) > 12 for x in range(0, w, 3))

    bottom = h
    for y in range(h - 1, -1, -1):
        if row_diff(y):
            bottom = min(h, y + 40)
            break
    im = im.crop((0, 0, w, bottom))
    im.save(OUT, optimize=True)
    print(f"报告 PNG: {OUT}  {im.size}  {OUT.stat().st_size/1024:.0f} KB")

    # 分页（手机看更舒服）
    pages = []
    y, i = 0, 1
    while y < im.size[1]:
        cut = min(y + PAGE_H, im.size[1])
        if cut < im.size[1]:
            for yy in range(cut, max(y + PAGE_H // 2, y), -1):
                if not row_diff(yy):
                    cut = yy
                    break
        p = REPORT / f"trend_combo_p{i}.png"
        im.crop((0, y, w, cut)).save(p, optimize=True)
        pages.append(p)
        print(f"  分页 {i}: y={y}~{cut}  {p.stat().st_size/1024:.0f} KB")
        y, i = cut, i + 1
    print(f"共 {len(pages)} 页")
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
