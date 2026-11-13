"""把 docs/post/wechat_article.html 推送到微信公众号草稿箱（只建草稿，不群发）。

沿用澄 2026-10-26 跑通的 publish_climbcolor.py 流程：
token 用 stable_token；封面必须是 type=thumb 的永久素材（<64KB）；
正文图走 media/uploadimg，HTML 里用 <img data-src="url">；
请求体必须裸 UTF-8（json= 会 ensure_ascii，微信不还原 → 存成 \\uXXXX）。
"""

import io
import json
import os
import re
import sys
import time

import requests
from PIL import Image

POST = r"D:\Project\qlib\projects\csi300_lgbm\docs\post"
HTML = os.path.join(POST, "wechat_article.html")
COVER = os.path.join(POST, "cover.png")
ASSETS = os.path.join(POST, "img")
MEDIA_ID_FILE = os.path.join(POST, "draft_media_id.txt")

TITLE = "沪深300×LightGBM选股复盘：验证期+20.86%，测试期-2.13%"
AUTHOR = "Curren"
DIGEST = "选股模型失败复盘：放宽有效，拉长无效"
COVER_MAX = 63000


def jj(resp):
    b = resp.content
    try:
        return json.loads(b.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(b.decode("latin-1"))


def post_json(url, at, obj, timeout=60):
    return jj(requests.post(
        url, params={"access_token": at},
        data=json.dumps(obj, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, timeout=timeout))


def stable_token(appid, secret):
    r = jj(requests.post("https://api.weixin.qq.com/cgi-bin/stable_token",
                         json={"grant_type": "client_credential", "appid": appid,
                               "secret": secret, "force_refresh": False}, timeout=30))
    if "access_token" not in r:
        raise SystemExit("token 失败: " + json.dumps(r, ensure_ascii=False))
    print("token ok, expires_in", r.get("expires_in"))
    return r["access_token"]


def shrink_cover(path):
    im = Image.open(path).convert("RGB")
    for q in (90, 86, 82, 76, 70, 64):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        data = buf.getvalue()
        if len(data) <= COVER_MAX:
            return data, im.size
    while len(data) > COVER_MAX and im.width > 400:
        im = im.resize((int(im.width * 0.9), int(im.height * 0.9)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=86, optimize=True)
        data = buf.getvalue()
    return data, im.size


def main():
    dry = "--dry" in sys.argv
    at = stable_token(os.environ["WECHAT_APP_ID"], os.environ["WECHAT_APP_SECRET"])

    r = jj(requests.post("https://api.weixin.qq.com/cgi-bin/draft/batchget",
                         params={"access_token": at},
                         json={"offset": 0, "count": 20, "no_content": 1}, timeout=30))
    same = [it["media_id"] for it in r.get("item", [])
            for n in it.get("content", {}).get("news_item", [])
            if n.get("title") == TITLE]
    print(f"草稿箱总数 {r.get('total_count')}，同名旧稿 {len(same)} 篇: {same}")
    if dry:
        return

    data, size = shrink_cover(COVER)
    r = jj(requests.post("https://api.weixin.qq.com/cgi-bin/material/add_material",
                         params={"access_token": at, "type": "thumb"},
                         files={"media": ("cover.jpg", data, "image/jpeg")}, timeout=120))
    if "media_id" not in r:
        raise SystemExit("封面上传失败: " + json.dumps(r, ensure_ascii=False))
    thumb = r["media_id"]
    print(f"封面 ok {len(data)//1024}KB {size} -> {thumb[:20]}…")

    html = open(HTML, encoding="utf-8").read()
    names, seen = [], set()
    for n in re.findall(r"__IMG:([^_]+(?:_[^_]+)*?)__", html):
        if n not in seen:
            seen.add(n)
            names.append(n)
    url_map = {}
    for n in names:
        p = os.path.join(ASSETS, n)
        if not os.path.exists(p):
            p = os.path.join(POST, n)
        mime = "image/png" if n.lower().endswith(".png") else "image/jpeg"
        with open(p, "rb") as fh:
            rr = jj(requests.post("https://api.weixin.qq.com/cgi-bin/media/uploadimg",
                                  params={"access_token": at},
                                  files={"media": (n, fh, mime)}, timeout=120))
        if "url" not in rr:
            raise SystemExit(f"上传 {n} 失败: " + json.dumps(rr, ensure_ascii=False))
        url_map[n] = rr["url"]
        print(f"  {n:24s} {os.path.getsize(p)//1024:4d}KB -> ok")
        time.sleep(0.3)

    for n, u in url_map.items():
        html = html.replace(f"__IMG:{n}__", u)
    assert "__IMG:" not in html, "仍有未替换的图片占位符"
    n_img = html.count("<img")
    n_mm = len(re.findall(r'data-src="https?://mmbiz\.qpic\.cn', html))
    assert n_img == n_mm, f"图片数不一致: img={n_img} data-src={n_mm}"
    print(f"正文图 {len(names)} 张，<img> {n_img} / mmbiz {n_mm}")

    article = {
        "title": TITLE, "author": AUTHOR, "digest": DIGEST, "content": html,
        "thumb_media_id": thumb, "need_open_comment": 1, "only_fans_can_comment": 0,
    }
    r = post_json("https://api.weixin.qq.com/cgi-bin/draft/add", at,
                  {"articles": [article]}, timeout=60)
    if "media_id" not in r:
        raise SystemExit("draft/add 失败: " + json.dumps(r, ensure_ascii=False))
    mid = r["media_id"]
    open(MEDIA_ID_FILE, "w").write(mid)
    print("DRAFT_ID:", mid)

    g = post_json("https://api.weixin.qq.com/cgi-bin/draft/get", at,
                  {"media_id": mid}, timeout=60)
    item = g["news_item"][0]
    c = item["content"]
    print("回读 title  :", item["title"])
    print("回读 digest :", item.get("digest"))
    print("回读 thumb  :", item.get("thumb_media_id") == thumb)
    print("回读 img    :", c.count("<img"), "/ mmbiz", c.count("mmbiz.qpic.cn"))
    print("回读 table  :", c.count("<table"), "个表,", c.count("<blockquote"), "个引用块")
    print("正文长度    :", len(html), "->", len(c))


if __name__ == "__main__":
    main()
