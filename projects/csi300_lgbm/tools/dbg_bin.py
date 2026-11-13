"""正确解析 qlib .bin：4 字节头=起始日历下标，之后每个日历日 1 个 float32。"""

from collections import Counter
from pathlib import Path

import numpy as np

DATA = Path(r"D:\Project\qlib\qlib_data\cn_data_2026")
cal = (DATA / "calendars" / "day.txt").read_text().split()


def info(sym, field="close"):
    p = DATA / "features" / sym / f"{field}.day.bin"
    if not p.exists():
        return None
    size = p.stat().st_size
    with open(p, "rb") as f:
        start = int(np.frombuffer(f.read(4), dtype="<f")[0])
    n = (size - 4) // 4
    end = start + n - 1
    last_date = cal[end] if 0 <= end < len(cal) else f"?{end}"
    return start, n, last_date


def main():
    print("日历末 4 天:", cal[-4:], "长度", len(cal))
    for s in ["sh600000", "sh600418", "sz002241", "sh000300", "sh601857"]:
        print(" ", s, info(s))

    mem = {}
    with open(DATA / "instruments" / "csi300.txt", encoding="utf-8") as f:
        for line in f:
            p = line.split("\t")
            if len(p) == 3:
                mem.setdefault(p[0], []).append((p[1], p[2]))
    latest = sorted({s for s, v in mem.items() if any(b >= "2026-10-27" for a, b in v)})
    cnt = Counter()
    missing = []
    for s in latest:
        t = info(s.lower())
        if t is None:
            cnt["无文件"] += 1
            missing.append(s)
            continue
        cnt[t[2]] += 1
    print(f"\n最新成分股 {len(latest)} 只，末日分布:")
    for d, c in sorted(cnt.items(), reverse=True):
        print(f"   {d}: {c}")
    if missing:
        print("无数据文件:", missing[:10], "…共", len(missing))


if __name__ == "__main__":
    main()
