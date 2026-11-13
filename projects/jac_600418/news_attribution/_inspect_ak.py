import inspect
import re

import akshare as ak

fns = [
    n
    for n in dir(ak)
    if re.search(r"news|telegraph|global|disclosure|report_cninfo|announce", n)
]
print("akshare 相关函数:")
for n in fns:
    print("   ", n)

print("\n--- stock_news_em 源码 ---")
print(inspect.getsource(ak.stock_news_em))
