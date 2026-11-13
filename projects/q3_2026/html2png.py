"""article.html → PNG（headless Chrome 截图 + PIL 裁掉尾部空白 + 切成便于手机阅读的分页）。

用法：..\\..\\.venv\\Scripts\\python.exe html2png.py
输出：shots/article_full.png（整篇长图） + shots/article_p1..pN.png（分页）
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)
HTML = HERE / "article.html"

WIDTH = 720
MAX_H = 26000
PAGE_H = 3600

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
    print("浏览器:", br)
    tmp = SHOTS / "_full.png"
    cmd = [
        br, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",
        f"--window-size={WIDTH},{MAX_H}",
        f"--screenshot={tmp}",
        "--virtual-time-budget=8000",
        HTML.resolve().as_uri(),
    ]
    print("执行:", " ".join(cmd[:6]), "…")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not tmp.exists():
        print("截图失败：", r.stdout[-800:], r.stderr[-800:])
        sys.exit(1)

    im = Image.open(tmp).convert("RGB")
    w, h = im.size
    print(f"原始截图 {w}×{h}")

    px = im.load()
    bg = px[2, h - 5]           # 页面底部背景色（.wrap 之外的 body 底色）
    print("底部背景色:", bg)

    def row_diff(y):
        """这一行是否"有内容"：与页面底色不同即算有内容。"""
        return any(abs(px[x, y][0] - bg[0]) + abs(px[x, y][1] - bg[1]) +
                   abs(px[x, y][2] - bg[2]) > 12 for x in range(0, w, 3))

    def row_flat(y):
        """这一行是否"整行同色"（可以安全下刀，不会切断文字/表格线）。"""
        first = px[2, y]
        return all(max(abs(px[x, y][i] - first[i]) for i in range(3)) <= 6
                   for x in range(0, w, 3))

    bottom = h
    for y in range(h - 1, -1, -1):
        if row_diff(y):
            bottom = min(h, y + 40)
            break
    print(f"内容底边: {bottom}px（背景 {h}px）")

    im = im.crop((0, 0, w, bottom))
    full = SHOTS / "article_full.png"
    im.save(full, optimize=True)
    print(f"整篇长图: {full}  {im.size}  {full.stat().st_size/1024:.0f} KB")

    # 分页
    pages = []
    y = 0
    i = 1
    while y < im.size[1]:
        cut = min(y + PAGE_H, im.size[1])
        if cut < im.size[1]:
            for yy in range(cut, max(y + PAGE_H // 2, y), -1):
                if row_flat(yy):
                    cut = yy
                    break
        p = SHOTS / f"article_p{i}.png"
        im.crop((0, y, w, cut)).save(p, optimize=True)
        pages.append(p)
        print(f"  分页 {i}: y={y}~{cut}  {p.stat().st_size/1024:.0f} KB")
        y = cut
        i += 1
    # 尾部页太矮就并进上一页
    if len(pages) > 1:
        last = Image.open(pages[-1])
        if last.size[1] < 520:
            prev = Image.open(pages[-2])
            merged = Image.new("RGB", (w, prev.size[1] + last.size[1]),
                               (237, 237, 237))
            merged.paste(prev, (0, 0))
            merged.paste(last, (0, prev.size[1]))
            merged.save(pages[-2], optimize=True)
            print(f"  末尾 {last.size[1]}px 并入第 {len(pages) - 1} 页"
                  f"（现 {merged.size[1]}px）")
            pages[-1].unlink(missing_ok=True)
            pages.pop()
    print(f"共 {len(pages)} 页 -> {SHOTS}")
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
