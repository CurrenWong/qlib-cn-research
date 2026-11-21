"""HTML → PNG（headless Chrome 截图 + 裁掉尾部空白）。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\render_update_png.py <html> <png> [宽度]
默认：report\\update_20261120\\update_report.html → report\\update_20261120\\update_report.png
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
DEFAULT_DIR = PROJ / "report" / "update_20261120"

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser() -> str:
    for p in CANDIDATES:
        if Path(p).exists():
            return p
    for name in ("chrome", "msedge"):
        exe = shutil.which(name)
        if exe:
            return exe
    raise SystemExit("找不到 Chrome / Edge")


def main() -> int:
    html = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR / "update_report.html"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DIR / "update_report.png"
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1240
    max_h = int(sys.argv[4]) if len(sys.argv) > 4 else 24000

    br = find_browser()
    tmp = out.with_name(out.stem + "_full.png")
    cmd = [br, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1.6", f"--window-size={width},{max_h}",
           f"--screenshot={tmp}", "--virtual-time-budget=20000", html.resolve().as_uri()]
    print("浏览器:", br)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if not tmp.exists():
        print("截图失败:", r.stdout[-800:], r.stderr[-800:])
        return 1

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
    im.save(out, optimize=True)
    print(f"报告 PNG: {out}  {im.size}  {out.stat().st_size/1024:.0f} KB")
    tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
