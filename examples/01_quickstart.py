"""Qlib 官方 Quick Start 示例（对应 README「Initialization」+「Get stock data」）。

数据源：D:\\Project\\qlib\\qlib_data\\cn_data（脚本 get_data.py qlib_data 下载后解压）
"""

import qlib
from qlib.constant import REG_CN
from qlib.data import D

PROVIDER_URI = r"D:\Project\qlib\qlib_data\cn_data"

# 1. 初始化
qlib.init(provider_uri=PROVIDER_URI, region=REG_CN)

# 2. 交易日历
print("\n=== calendar ===")
print(D.calendar(start_time="2010-01-01", end_time="2017-12-31", freq="day")[:2])

# 3. 股票池
print("\n=== instruments (csi500) ===")
inst = D.instruments("csi500")
print(D.list_instruments(instruments=inst, start_time="2010-01-01", end_time="2017-12-31", as_list=True)[:6])

# 4. 特征表达式
print("\n=== features ===")
instruments = ["SH600000"]
fields = ["$close", "$volume", "Ref($close, 1)", "Mean($close, 3)", "$high-$low"]
df = D.features(instruments, fields, start_time="2010-01-01", end_time="2017-12-31", freq="day")
print(df.head())
print("\nrows:", len(df))
