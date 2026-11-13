"""查各平台发布凭据（只看变量名与长度，不打印明文）。"""

import os

KEYS = ["WECHAT", "WEIXIN", "ZHIHU", "XHS", "XIAOHONGSHU", "XUEQIU", "TOUTIAO",
        "BILIBILI", "WEIBO", "DOUYIN", "CSDN", "JIANSHU", "GZH", "TOKEN", "SECRET",
        "APPID", "APP_ID", "API_KEY", "COOKIE"]

hits = [k for k in os.environ if any(s in k.upper() for s in KEYS)]
print("相关环境变量：")
for k in sorted(hits):
    v = os.environ[k]
    print(f"   {k} = {'SET (len=%d)' % len(v) if v else 'EMPTY'}")
if not hits:
    print("   （无）")
