"""探针：002230 科大讯飞 在 cn_data_2026 里的数据可得性。"""

import qlib
from qlib.data import D

qlib.init(provider_uri="D:/Project/qlib/qlib_data/cn_data_2026", region="cn")

insts = D.instruments(market="all")
df = D.features(
    ["SZ002230"],
    ["$close", "$factor", "$volume", "$change"],
    start_time="2026-01-01",
    end_time="2026-12-31",
)
print("行数", len(df))
print(df.head(3))
print(df.tail(3))
print("有 factor 的天数", int(df["$factor"].notna().sum()))
print("末日 close/factor", float(df["$close"].iloc[-1]), float(df["$factor"].iloc[-1]))
print("换手反推的原始价 = close/factor:", float(df["$close"].iloc[-1] / df["$factor"].iloc[-1]))

# 交易日历端点
cal = D.calendar(start_time="2026-01-01", end_time="2026-12-31")
print("日历", cal[0], "->", cal[-1], len(cal))
