"""只读核验公众号草稿：位置 / 结构计数 / 与本地构建稿逐字比对 / 回读存盘。"""

import difflib
import json
import os
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
API = "https://api.weixin.qq.com/cgi-bin"
MID = (HERE / "wechat_draft_id.txt").read_text(encoding="utf-8").strip()


def post(url, **kw):
    kw.setdefault("timeout", 120)
    r = requests.post(url, **kw)
    return json.loads(r.content.decode("utf-8", errors="replace"))


at = post(f"{API}/stable_token", json={
    "grant_type": "client_credential", "appid": os.environ["WECHAT_APP_ID"],
    "secret": os.environ["WECHAT_APP_SECRET"], "force_refresh": False})["access_token"]

idx = total = None
offset = 0
while True:
    r = post(f"{API}/draft/batchget", params={"access_token": at},
             data=json.dumps({"offset": offset, "count": 20, "no_content": 1},
                             ensure_ascii=False).encode("utf-8"),
             headers={"Content-Type": "application/json"})
    total = r.get("total_count", 0)
    for i, it in enumerate(r.get("item", [])):
        if it["media_id"] == MID:
            idx = offset + i
    if idx is not None or offset >= total or not r.get("item"):
        break
    offset += 20

r = post(f"{API}/draft/get", params={"access_token": at},
         data=json.dumps({"media_id": MID}).encode("utf-8"),
         headers={"Content-Type": "application/json"})
news = r["news_item"][0]
title, content, digest = news["title"], news["content"], news.get("digest", "")

print(f"草稿总数          : {total}")
print(f"位置              : 第 {idx + 1 if idx is not None else '?'} 条（按更新时间倒序）")
print(f"title({len(title)})        : {title}")
print(f"digest({len(digest)})       : {digest}")
print(f"content 字节       : {len(content.encode('utf-8'))}")
print(f"title 有 \\u 转义  : {'\\u' in title}")
print(f"content 有 \\uXXXX : {bool(re.search(r'\\\\u[0-9a-f]{4}', content))}")

print("---- 结构 ----")
print("img 标签数        :", content.count("<img"))
print("mmbiz.qpic.cn 数  :", content.count("mmbiz.qpic.cn"))
print("data-src 数       :", content.count("data-src"))
print("table 数          :", len(re.findall(r"<table", content)))
print("h2 橙色竖线数     :", content.count("border-left:4px solid #E67E22"))
print("strong 数         :", len(re.findall(r"<strong", content)))

render = content.replace("data-src=", "src=")
out = HERE / "draft_render.html"
out.write_text("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
               "<title>draft render</title></head><body style='max-width:677px;"
               "margin:0 auto;padding:24px 18px;background:#fff;'>" + render +
               "</body></html>", encoding="utf-8")
print("draft_render.html :", out, out.stat().st_size, "bytes")


def strip(h):
    h = re.sub(r"<title>.*?</title>", "", h, flags=re.S)
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", h))


local = (HERE / "wechat_content_uploaded.html").read_text(encoding="utf-8")
a, b = strip(local), strip(render)
print(f"纯文本长度 local/render : {len(a)} / {len(b)}  一致={a == b}")
if a != b:
    for line in list(difflib.unified_diff([a], [b], lineterm=""))[:8]:
        print("  ", line[:400])
    sys.exit(1)
