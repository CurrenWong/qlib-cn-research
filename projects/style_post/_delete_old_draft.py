"""删掉被取代的旧公众号草稿（只删我们自己刚建的那份，内容本地都有，可随时重建）。"""
import json
import os

import requests

API = "https://api.weixin.qq.com/cgi-bin"
APPID = os.environ["WECHAT_APP_ID"]
SECRET = os.environ["WECHAT_APP_SECRET"]
OLD = "633r9_pjAyxR8atzJ8UNcieRQw-k9MVl-HORx7w5ZC_Vj_MQO5R9x3aImGNjWLMQ"


def post(url, **kw):
    kw.setdefault("timeout", 120)
    return json.loads(requests.post(url, **kw).content.decode("utf-8", errors="replace"))


at = post(f"{API}/stable_token", json={"grant_type": "client_credential", "appid": APPID,
                                       "secret": SECRET, "force_refresh": False})["access_token"]
r = post(f"{API}/draft/delete", params={"access_token": at},
         data=json.dumps({"media_id": OLD}).encode("utf-8"),
         headers={"Content-Type": "application/json"})
print("draft/delete ->", json.dumps(r, ensure_ascii=False))
