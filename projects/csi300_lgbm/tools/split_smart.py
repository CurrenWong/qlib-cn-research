"""按"空白带"切长图：不切断文字行。

在目标 y 附近找一个整行接近纯白的带（段落/表格之间的空隙），从空隙中间切。
用法：python split_smart.py portfolio_v2.png [目标页高]
"""

import sys
from pathlib import Path

from PIL import Image

REPORT = Path(__file__).resolve().parent.parent / "report"
src = REPORT / (sys.argv[1] if len(sys.argv) > 1 else "portfolio_v2.png")
target = int(sys.argv[2]) if len(sys.argv) > 2 else 4200
SEARCH = 700          # 在目标点上下各找多远
TOL = 10              # 行内像素与背景的最大偏差


def main():
    im = Image.open(src).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = px[w // 2, 4]
    stem = src.stem
    print(f"整图 {w}×{h}，{src.stat().st_size/1024:.0f}KB")

    def is_blank(y):
        for x in range(2, w - 2, 4):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > TOL:
                return False
        return True

    blank = [is_blank(y) for y in range(h)]

    cuts = [0]
    y = target
    while y < h - 200:
        best, best_len = None, 0
        for yy in range(max(cuts[-1] + 800, y - SEARCH), min(h, y + SEARCH)):
            if not blank[yy]:
                continue
            ln = 0
            k = yy
            while k < h and blank[k]:
                ln += 1
                k += 1
            if ln > best_len:
                best_len, best = ln, yy + ln // 2
        if best is None:
            best = min(y, h - 1)
            print(f"  ! y={y} 附近没有空白带，硬切于 {best}")
        cuts.append(best)
        y = best + target

    cuts.append(h)
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        p = REPORT / f"{stem}_p{i+1}.png"
        crop = im.crop((0, a, w, b))
        pad_t, pad_b = (0 if a == 0 else 26), 30
        canvas = Image.new("RGB", (w, crop.size[1] + pad_t + pad_b), (255, 255, 255))
        canvas.paste(crop, (0, pad_t))
        canvas.save(p, optimize=True)
        print(f"  第 {i+1} 页: y={a}~{b} ({b-a}px)  {p.stat().st_size/1024:.0f}KB")
    print(f"共 {len(cuts)-1} 页")


if __name__ == "__main__":
    main()
