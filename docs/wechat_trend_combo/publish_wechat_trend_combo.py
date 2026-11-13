"""把 docs/wechat_trend_combo/article.md 推进公众号草稿箱（只建草稿，不群发）。

沿用 docs/wechat_attrib/publish_wechat_attrib.py 的流程与两个接口坑的解法：
  stable_token → 查同名旧稿（只报告不删）→ 正文图 uploadimg
  → 封面 material/add_material(type=thumb) → draft/add（裸 UTF-8 JSON）

用法：
  set "WECHAT_APP_ID=..." & set "WECHAT_APP_SECRET=..." & python publish_wechat_trend_combo.py
"""

import io
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "wechat"))
from wechat_html import MARKER, md_to_html  # noqa: E402

APPID = os.environ["WECHAT_APP_ID"]
SECRET = os.environ["WECHAT_APP_SECRET"]
API = "https://api.weixin.qq.com/cgi-bin"

TITLE = "方向定错了，信号就是反的：基本面 + 高频价量的混合打分"
DIGESTS = [
    "教科书给的方向让 IC 变成 -0.0074，交给数据之后是 +0.0332。",
    "45 个因子的混合打分：IC、换手与一次诚实的回测",
    "先验方向让信号变反，混合分测试期年化 +5.87%",
]
COVER = HERE / "img" / "cover.png"


def post(url, **kw):
    kw.setdefault("timeout", 120)
    r = requests.post(url, **kw)
    return json.loads(r.content.decode("utf-8", errors="replace"))


def token():
    r = post(f"{API}/stable_token", json={"grant_type": "client_credential",
                                          "appid": APPID, "secret": SECRET,
                                          "force_refresh": False})
    if "access_token" not in r:
        sys.exit("token failed: " + json.dumps(r, ensure_ascii=False))
    print(f"[1] stable_token ok, expires_in={r.get('expires_in')}")
    return r["access_token"]


def shrink_cover(path, cap=58000):
    im = Image.open(path).convert("RGB")
    q = 88
    while True:
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        data = buf.getvalue()
        if len(data) <= cap or q <= 45:
            break
        q -= 6
    return data, im.size


def upload_images(at):
    md = (HERE / "article.md").read_text(encoding="utf-8")
    paths = [m.group(1).strip() for m in MARKER.finditer(md)]
    urls = []
    for rel in paths:
        f = HERE / rel
        with open(f, "rb") as fh:
            r = post(f"{API}/media/uploadimg", params={"access_token": at},
                     files={"media": (f.name, fh, "image/png")})
        if "url" not in r:
            sys.exit(f"uploadimg failed for {rel}: " + json.dumps(r, ensure_ascii=False))
        urls.append(r["url"])
        print(f"    {rel} -> {r['url'][:60]}…  ({f.stat().st_size // 1024}KB)")
    print(f"[2] 正文图 {len(urls)}/{len(paths)} 上传成功")
    return urls


def main():
    at = token()

    r = post(f"{API}/draft/batchget", params={"access_token": at},
             data=json.dumps({"offset": 0, "count": 20, "no_content": 1},
                             ensure_ascii=False).encode("utf-8"),
             headers={"Content-Type": "application/json"})
    dup = [(i, it.get("media_id")) for i, it in enumerate(r.get("item", []))
           if it.get("content", {}).get("news_item", [{}])[0].get("title") == TITLE]
    print(f"[!] 同名旧稿: {dup if dup else '无'}")

    urls = upload_images(at)
    html = md_to_html((HERE / "article.md").read_text(encoding="utf-8"), urls)

    data, size = shrink_cover(COVER)
    r = post(f"{API}/material/add_material",
             params={"access_token": at, "type": "thumb"},
             files={"media": ("cover.jpg", data, "image/jpeg")})
    if "media_id" not in r:
        sys.exit("cover failed: " + json.dumps(r, ensure_ascii=False))
    thumb = r["media_id"]
    print(f"[3] 封面 ok {len(data)}B {size} -> {thumb[:20]}…")

    art = {"title": TITLE, "author": "", "content": html, "content_source_url": "",
           "thumb_media_id": thumb, "need_open_comment": 0, "only_fans_can_comment": 0}
    for i, d in enumerate(DIGESTS):
        art["digest"] = d
        r = post(f"{API}/draft/add", params={"access_token": at},
                 data=json.dumps({"articles": [art]}, ensure_ascii=False).encode("utf-8"),
                 headers={"Content-Type": "application/json"})
        if "media_id" in r:
            print(f"[4] draft/add ok (digest#{i}, {len(d)} 字)")
            break
        print(f"    digest#{i} 失败: {r.get('errcode')} {r.get('errmsg')}")
        if r.get("errcode") != 45004:
            sys.exit("draft/add failed: " + json.dumps(r, ensure_ascii=False))
    else:
        sys.exit("draft/add failed on all digests")

    mid = r["media_id"]
    (HERE / "wechat_draft_id.txt").write_text(mid, encoding="utf-8")
    (HERE / "wechat_content_uploaded.html").write_text(
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<title>trend_combo article (uploaded)</title></head><body style='max-width:677px;"
        "margin:0 auto;padding:24px 18px;'>" + html + "</body></html>", encoding="utf-8")
    print("MEDIA_ID:", mid)
    print("CONTENT_BYTES:", len(html.encode("utf-8")))
    print("IMGS_IN_CONTENT:", html.count("<img"))
    print("H2:", html.count("font-size:19px"))


if __name__ == "__main__":
    main()
