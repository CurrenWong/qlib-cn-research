"""片段 1：数据层 —— qlib.init / D.calendar / D.instruments / D.features

⚠️ Windows 必读：qlib 的 D.features 在多标的时会用 joblib 起子进程，
   脚本必须写成 `if __name__ == "__main__":` 保护，否则会无限 fork 报
   "An attempt has been made to start a new process before the current process has finished its bootstrapping phase"。

运行：..\\.venv\\Scripts\\python.exe snippets\\snippet_01_data.py
"""

import pandas as pd

import qlib
from qlib.constant import REG_CN
from qlib.data import D

PROVIDER_URI = r"D:\Project\qlib\qlib_data\cn_data"


def main():
    qlib.init(provider_uri=PROVIDER_URI, region=REG_CN)

    # ---- 1. 交易日历 ----
    cal = D.calendar(freq="day")          # 返回 numpy.datetime64 数组
    cal = pd.DatetimeIndex(cal)           # 转成 DatetimeIndex 才好用 pandas 方法
    print(f"[日历] {cal[0].date()} ~ {cal[-1].date()}，共 {len(cal)} 个交易日")
    print("  2020 年前 5 个交易日：", [str(d.date()) for d in cal[cal.year == 2020][:5]])

    # ---- 2. 股票池 ----
    inst = D.instruments("csi300")
    members = D.list_instruments(
        inst, start_time="2020-01-01", end_time="2020-03-31", as_list=True
    )
    print(f"\n[股票池] csi300 在 2020Q1 的成分股数量 = {len(members)}")
    print("  前 5 只：", members[:5])

    # as_list=False 时返回 dict{instrument: [(start, end), ...]}（不是 DataFrame）
    raw_members = D.list_instruments(
        inst, start_time="2020-01-01", end_time="2020-03-31", as_list=False
    )
    print("  dict 形式类型：", type(raw_members).__name__, "，示例：",
          dict(list(raw_members.items())[:1]))

    # ---- 3. 特征表达式 ----
    codes = ["SH600000", "SH600519"]
    fields = [
        "$close",                       # 收盘价
        "$volume",                      # 成交量
        "Ref($close,1)/$close-1",       # 昨日反转
        "Mean($close,20)/$close-1",     # 20 日均线偏离
        "$high-$low",                   # 日内振幅
    ]
    df = D.features(codes, fields, start_time="2020-01-01", end_time="2020-03-31", freq="day")
    print(f"\n[特征] shape={df.shape}，索引层级={df.index.names}")
    print(df.head(8).to_string())

    # ---- 4. 单标的取整表 ----
    one = D.features(["SH600000"], ["$close"], start_time="2020-03-01", end_time="2020-03-10", freq="day")
    print(f"\n[单标的] 类型={type(one).__name__}，MultiIndex 层级={one.index.names}")
    flat = one.xs("SH600000", level="instrument")   # 丢掉 instrument 层级
    print(flat.to_string())


if __name__ == "__main__":
    main()
