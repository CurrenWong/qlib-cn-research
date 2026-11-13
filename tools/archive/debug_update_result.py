"""诊断：测试目录里 SH600418 为什么读不出数据。"""

from pathlib import Path

import numpy as np


def read_bin(path):
    arr = np.fromfile(path, dtype=np.float32)
    return int(arr[0]), arr[1:]


def main():
    d = Path(r"D:\Project\qlib\qlib_data\_test_update")
    cal = [x.strip() for x in (d / "calendars" / "day.txt").read_text().splitlines() if x.strip()]
    print("日历长度:", len(cal), "末日:", cal[-1], "| 2001-08-24 下标:", cal.index("2001-08-24") if "2001-08-24" in cal else "不在日历")

    for code in ["sh600418", "sh000300"]:
        fdir = d / "features" / code
        print(f"\n{code}:")
        for p in sorted(fdir.glob("*.bin")):
            si, vals = read_bin(p)
            nan = int(np.isnan(vals).sum())
            print(f"  {p.name:22s} 起 {si:5d} ({cal[si] if si < len(cal) else '越界'}) 长度 {len(vals):5d} "
                  f"→ 末 {cal[min(si+len(vals)-1, len(cal)-1)]}  NaN {nan}  首值 {vals[0]:.4f} 末值 {vals[-1]:.4f}")

    print("\ninstruments/all.txt 中的这两行:")
    for ln in (d / "instruments" / "all.txt").read_text().splitlines():
        if ln.upper().startswith(("SH600418", "SH000300")):
            print("  ", repr(ln))


if __name__ == "__main__":
    main()
