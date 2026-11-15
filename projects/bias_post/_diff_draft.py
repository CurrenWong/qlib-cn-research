"""看回传正文和本地上传 HTML 的纯文本到底差在哪。"""
import difflib
import json
import os
import re

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.weixin.qq.com/cgi-bin"
APPID = os.environ["WECHAT_APP_ID"]
SECRET = os.environ["WECHAT_APP_SECRET"]


def post(url, **kw):
    kw.setdefault("timeout", 120)
    return json.loads(requests.post(url, **kw).content.decode("utf-8", errors="replace"))


def plain(h):
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", h))


at = post(f"{API}/stable_token", json={"grant_type": "client_credential", "appid": APPID,
                                       "secret": SECRET, "force_refresh": False})["access_token"]
mid = open(os.path.join(HERE, "wechat_draft_id.txt"), encoding="utf-8").read().strip()
r = post(f"{API}/draft/get", params={"access_token": at},
         data=json.dumps({"media_id": mid}).encode("utf-8"),
         headers={"Content-Type": "application/json"})
remote = plain(r["news_item"][0]["content"])
local = plain(open(os.path.join(HERE, "wechat_content_uploaded.html"), encoding="utf-8").read())

sm = difflib.SequenceMatcher(None, local, remote)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    print(f"{tag:8} local[{i1}:{i2}]={local[i1:i2]!r}  remote[{j1}:{j2}]={remote[j1:j2]!r}")
    ctx = local[max(0, i1 - 25):i2 + 25]
    print(f"         上下文: …{ctx}…")
