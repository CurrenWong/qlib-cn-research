"""只读核验：草稿元信息 / 今日新增条目 / 正文首段 / 表格与图片清单。"""
import json
import os
import re
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
API = "https://api.weixin.qq.com/cgi-bin"
MID = (HERE / "wechat_draft_id.txt").read_text(encoding="utf-8").strip()


def post(url, **kw):
    kw.setdefault("timeout", 120)
    return json.loads(requests.post(url, **kw).content.decode("utf-8", errors="replace"))


at = post(f"{API}/stable_token", json={
    "grant_type": "client_credential", "appid": os.environ["WECHAT_APP_ID"],
    "secret": os.environ["WECHAT_APP_SECRET"], "force_refresh": False})["access_token"]


def ts(u):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(u))


all_items, offset, total = [], 0, None
while True:
    r = post(f"{API}/draft/batchget", params={"access_token": at},
             data=json.dumps({"offset": offset, "count": 20, "no_content": 1},
                             ensure_ascii=False).encode("utf-8"),
             headers={"Content-Type": "application/json"})
    total = r.get("total_count", 0)
    all_items += r.get("item", [])
    if not r.get("item") or offset + 20 >= total:
        break
    offset += 20

print(f"TOTAL_DRAFT_COUNT = {total}")
print(f"本次 media_id 在列表中出现的次数 = "
      f"{sum(1 for it in all_items if it['media_id'] == MID)}")
me = [it for it in all_items if it["media_id"] == MID][0]
pos = all_items.index(me) + 1
print(f"位置 = 第 {pos} 条")
print(f"media_id = {MID}")
print(f"title = {me['content']['news_item'][0]['title']}")
print(f"update_time(raw) = {me.get('update_time')}  -> {ts(me['update_time'])}")
print(f"content.create_time = {me.get('content', {}).get('create_time')}")

print("\n---- 草稿箱前 6 条（media_id 后 8 位 / 更新时间 / 标题前 24 字）----")
for i, it in enumerate(all_items[:6], 1):
    t = it["content"]["news_item"][0]["title"]
    print(f"{i:>2}. …{it['media_id'][-8:]}  {ts(it['update_time'])}  {t[:24]}")

print("\n---- 今日（本地时区）更新过的草稿 ----")
today = time.strftime("%Y-%m-%d", time.localtime())
hits = [it for it in all_items if ts(it["update_time"]).startswith(today)]
print(f"count = {len(hits)}")
for it in hits:
    print("   ", ts(it["update_time"]), it["media_id"], it["content"]["news_item"][0]["title"][:30])

# 正文
r = post(f"{API}/draft/get", params={"access_token": at},
         data=json.dumps({"media_id": MID}).encode("utf-8"),
         headers={"Content-Type": "application/json"})
content = r["news_item"][0]["content"]

plain = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", content))
print("\n---- 正文 ----")
print("首 30 字 =", repr(plain[:30]))
print("全文字数 =", len(plain))
print("是否含 climb / ClimbColor / 攀岩 =",
      any(k in plain for k in ("Climb", "climb", "攀岩", "抱石")))

print("\n---- 7 个表格（表头）----")
for i, tb in enumerate(re.findall(r"<table.*?</table>", content, re.S), 1):
    ths = [re.sub(r"<[^>]+>", "", x) for x in re.findall(r"<th[^>]*>(.*?)</th>", tb, re.S)]
    rows = len(re.findall(r"<tr", tb))
    print(f"  表{i}: {rows} 行 | 表头 {ths}")

print("\n---- 6 张图（按出现顺序）----")
for i, u in enumerate(re.findall(r'data-src="([^"]+)"', content), 1):
    print(f"  img{i}: {u}")

print("\n---- 文件 ----")
f = HERE / "draft_render.html"
st = f.stat()
print("PATH =", f)
print(f"SIZE = {st.st_size} bytes   MTIME = {ts(st.st_mtime)}")
