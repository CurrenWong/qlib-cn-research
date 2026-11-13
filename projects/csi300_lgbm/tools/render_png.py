"""HTML → PNG（headless Chrome 截图 + 裁掉尾部空白）。

用法：..\\..\\..\\.venv\\Scripts\\python.exe render_png.py
输出：report/report.png
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent
REPORT = HERE / "report"
HTML = REPORT / (sys.argv[1] if len(sys.argv) > 1 else "report.html")
OUT = REPORT / (sys.argv[2] if len(sys.argv) > 2 else "report.png")

WIDTH = 1240
MAX_H = 26000

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
           "--force-device-scale-factor=2", f"--window-size={WIDTH}:{MAX_H}".replace(":", ","),
           f"--screenshot={tmp}", "--virtual-time-budget=12000", HTML.resolve().as_uri()]
    print("浏览器:", br)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
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
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
