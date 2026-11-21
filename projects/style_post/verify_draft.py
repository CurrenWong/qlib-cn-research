"""核验公众号草稿：把草稿从后台拉回来，和本地生成的 HTML / article.md 对。

三层校验：
  1. 回传正文 与 本地上传的 `wechat_content_uploaded.html` 纯文本逐字一致（round-trip）
  2. article.md 里 4 条图注、若干sentinel 句子都出现在回传正文里（内容没被截断）
  3. 结构：<img> 数 = 本地【插图】数且全是 mmbiz；表格数、h2 数、标题

用法：..\\..\\.venv\\Scripts\\python.exe verify_draft.py
"""

import difflib
import html as html_mod
import json
import os
import re
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
APPID = os.environ["WECHAT_APP_ID"]
SECRET = os.environ["WECHAT_APP_SECRET"]
API = "https://api.weixin.qq.com/cgi-bin"
MARKER = re.compile(r"【插图\s*\d+：([^｜]+)｜图注：([^】]+)】")

SENTINELS = [
    "乖离率（BIAS）就是收盘价对均线的偏离",
    "58.6% 的仓位，压在了当周跌得最狠、离均线最远的两三个行业上",
    "所以这不是「模型失效」，是「风险模型缺位」",
    "数字必须来自实际输出，不能凭印象写",
    "不构成投资建议。数据截至 2026-11-20 收盘。",
]


def post(url, **kw):
    kw.setdefault("timeout", 120)
    return json.loads(requests.post(url, **kw).content.decode("utf-8", errors="replace"))


def plain(html: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html))


def main() -> int:
    mid = open(os.path.join(HERE, "wechat_draft_id.txt"), encoding="utf-8").read().strip()
    at = post(f"{API}/stable_token", json={"grant_type": "client_credential",
                                           "appid": APPID, "secret": SECRET,
                                           "force_refresh": False})["access_token"]
    r = post(f"{API}/draft/get", params={"access_token": at},
             data=json.dumps({"media_id": mid}).encode("utf-8"),
             headers={"Content-Type": "application/json"})
    if "news_item" not in r:
        sys.exit("draft/get 失败: " + json.dumps(r, ensure_ascii=False))
    item = r["news_item"][0]
    html = item["content"]

    md = open(os.path.join(HERE, "article.md"), encoding="utf-8").read()
    uploaded = open(os.path.join(HERE, "wechat_content_uploaded.html"), encoding="utf-8").read()
    # 去掉 <head><title>：微信只保存 body，标题另存 item['title']，否则 round-trip 会差 21 字
    uploaded = re.search(r"<body[^>]*>(.*)</body>", uploaded, flags=re.S).group(1)

    n_expect = len(MARKER.findall(md))
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
    h2 = html.count("font-size:19px")
    tables = html.count("<table")
    ratio = difflib.SequenceMatcher(None, plain(uploaded), plain(html)).ratio()

    # 图注/关键句在正文里可能被转义成 &lt; &gt;，比对前先还原
    html_text = html_mod.unescape(html)
    caps_ok = [(c, c in html_text) for _, c in MARKER.findall(md)]
    sent_ok = [(s, s in html_text) for s in SENTINELS]

    print(f"标题        : {item['title']}")
    print(f"摘要        : {item.get('digest', '')[:64]}")
    print(f"图片        : {len(imgs)} (期望 {n_expect})")
    print(f"mmbiz 图    : {sum('mmbiz.qpic.cn' in u for u in imgs)}")
    print(f"表格 / h2   : {tables} / {h2}")
    print(f"round-trip  : {ratio:.4f}  (回传 {len(plain(html))} 字 vs 上传 {len(plain(uploaded))} 字)")
    miss_cap = [c[:20] for c, ok in caps_ok if not ok]
    miss_sent = [s for s, ok in sent_ok if not ok]
    print(f"图注齐全    : {len(caps_ok) - len(miss_cap)}/{len(caps_ok)}" + (f"  缺 {miss_cap}" if miss_cap else ""))
    print(f"关键句齐全  : {len(sent_ok) - len(miss_sent)}/{len(sent_ok)}" + (f"  缺 {miss_sent}" if miss_sent else ""))

    ok = (len(imgs) == n_expect and all("mmbiz.qpic.cn" in u for u in imgs)
          and ratio > 0.999 and not miss_cap and not miss_sent and tables >= 4)
    print("结论        :", "通过" if ok else "需要复查")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
