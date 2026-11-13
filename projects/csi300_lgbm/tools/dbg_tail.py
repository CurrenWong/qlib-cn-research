"""检查股票 .bin 是否真的有 2026-10-28~30 的数据（Windows: D.features 必须有 __main__ 保护）。"""

from pathlib import Path

import numpy as np
import pandas as pd


def main():
    DATA = Path(r"D:\Project\qlib\qlib_data\cn_data_2026")
    cal = (DATA / "calendars" / "day.txt").read_text().split()
    print("日历最后 6 天:", cal[-6:], "总天数", len(cal))
    for s in ["sh600000", "sh600418", "sz002241", "sh000300"]:
        f = DATA / "features" / s / "day" / "$close.day.bin"
        if not f.exists():
            print(s, "无 $close.day.bin")
            continue
        arr = np.fromfile(f, dtype=np.float32)
        print(f"{s}: bin 长度 {len(arr)}（日历 {len(cal)}，差 {len(cal)-len(arr)}）末尾 8 值: "
              f"{np.round(arr[-8:], 4)}")

    import qlib
    from qlib.data import D
    qlib.init(provider_uri=str(DATA), region="cn")
    df = D.features(["SH600000", "SH600418", "SZ002241", "SH000300"], ["$close"],
                    start_time="2026-10-20", end_time="2026-10-31", freq="day")
    print(df["$close"].unstack(level=0).to_string())


if __name__ == "__main__":
    main()
