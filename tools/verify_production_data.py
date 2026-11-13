"""验证正式目录 cn_data_2026 已含 2026-10-28，且历史未被破坏。"""

import qlib
from qlib.constant import REG_CN
from qlib.data import D


def main():
    qlib.init(provider_uri=r"D:\Project\qlib\qlib_data\cn_data_2026", region=REG_CN)

    for code in ["SH600418", "SH000300"]:
        df = D.features([code], ["$close", "$volume", "$factor"],
                        start_time="2026-10-20", end_time="2026-10-31", freq="day")
        print(f"\n{code} 最近几日：")
        print(df.tail(8).to_string())

        full = D.features([code], ["$close"], start_time="2015-01-01", end_time="2026-12-31", freq="day")
        s = full.xs(code, level="instrument")["$close"]
        print(f"  区间: {s.index[0].date()} ~ {s.index[-1].date()}  共 {len(s)} 行  "
              f"末日收盘 {s.iloc[-1]:.4f}")

    # 关键历史日期抽查（应与文档里的数字一致）
    print("\n历史抽查（应与此前分析一致）：")
    checks = [("SH600418", "2018-12-28"), ("SH600418", "2020-09-24"), ("SH600418", "2024-12-31")]
    for code, d in checks:
        df = D.features([code], ["$close"], start_time=d, end_time=d, freq="day")
        if len(df):
            print(f"  {code} {d}: {float(df['$close'].iloc[0]):.4f}")
        else:
            print(f"  {code} {d}: 无数据（非交易日或缺失）")


if __name__ == "__main__":
    main()
