"""修 CSDN 草稿：拦截编辑器自己的 saveArticle 请求，在飞的那一下改 body。

要点：
  · 编辑器自己签名（x-ca-key/nonce/signature），我们不改头，只改 body
  · 只有确认原请求是「存草稿」才改（status/pubStatus 必须是 draft），
    万一抓到的不是草稿保存，直接放行不碰
  · 改两处：markdowncontent 里的 img/xxx.png 相对路径；content HTML 里的占位图 URL
"""
import json
import re
import sys
from playwright.sync_api import sync_playwright

ART = "171141543"
REAL = {
    "img/bias_percentile.png": "https://i-blog.csdnimg.cn/direct/08fad431f4ef49059f59769cfd87f358.png",
    "img/rotate.png": "https://i-blog.csdnimg.cn/direct/938747715b7e4b3a81642a980bf2517f.png",
}
PLACEHOLDER = "https://img-home.csdnimg.cn/images/20230724024159.png"


def patch(text: str) -> tuple[str, int]:
    """把 CSDN 的「外链图片转存失败」占位图换成真实 CDN URL。

    占位图形态（编辑器存进 markdown/HTML 的就是这个 URL，不是相对路径）：
      https://img-home.csdnimg.cn/images/20230724024159.png?origin_url=img%2Fxxx.png&pos_id=...
    其中 origin_url 里的 '/' 是 %2F 编码，pos_id 每次加载都会变。
    """
    n = 0
    for key, real in REAL.items():
        base = key.split("/")[-1]
        # ① 占位图 URL（两种编码都覆盖）
        enc = re.escape("img%2F" + base)
        raw = re.escape("img/" + base)
        pat = re.compile(re.escape(PLACEHOLDER) + r"\?origin_url=(?:" + enc + "|" + raw + r")[^\s\"']*")
        text, k = pat.subn(real, text)
        n += k
        # ② 裸相对路径（万一还在）
        text, k = re.subn(r"(?<![\w/])" + re.escape(key) + r"(?![\w])", real, text)
        n += k
    return text, n


def main():
    seen = {}
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = ctx.new_page()

        def handler(route):
            req = route.request
            try:
                data = json.loads(req.post_data or "{}")
            except Exception:
                seen["parse_error"] = True
                route.continue_()
                return

            seen["keys"] = sorted(data.keys())
            seen["status"] = data.get("status")
            seen["pubStatus"] = data.get("pubStatus")
            seen["article_id"] = data.get("article_id") or data.get("id")
            seen["title"] = data.get("title")
            md = data.get("markdowncontent") or ""
            html = data.get("content") or ""
            seen["md_len"] = len(md)
            seen["html_len"] = len(html)
            seen["md_imgs"] = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", md)
            seen["html_bad"] = len(re.findall(re.escape(PLACEHOLDER), html))
            seen["md_bad"] = sum(1 for k in REAL if k in md)

            # 只在确认是「存草稿」时才改
            draft_ok = (data.get("pubStatus") == "draft") or (data.get("status") in (2, "2"))
            if not draft_ok:
                seen["skipped"] = "不是草稿保存，未修改"
                route.continue_()
                return

            new_md, n1 = patch(md)
            new_html, n2 = patch(html)
            seen["patched_md"] = n1
            seen["patched_html"] = n2
            data["markdowncontent"] = new_md
            data["content"] = new_html
            body = json.dumps(data, ensure_ascii=False)
            seen["new_md_imgs"] = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", new_md)
            seen["new_html_bad"] = len(re.findall(re.escape(PLACEHOLDER), new_html))
            route.continue_(post_data=body, headers={**req.headers, "content-type": "application/json"})

        pg.route("**/blog-console-api/v3/mdeditor/saveArticle", handler)

        pg.goto(f"https://editor.csdn.net/md?articleId={ART}",
                wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(9000)

        # 先让编辑器认为内容有改动（否则保存可能是空转）
        pg.evaluate("""() => {
            const b = document.querySelector('.button-save');
            if (b) b.classList.add('hasChg');
        }""")
        pg.click(".button-save")
        pg.wait_for_timeout(12000)

        print("=== 拦截到的 saveArticle 请求 ===")
        for k, v in seen.items():
            if isinstance(v, list):
                print(f"  {k}:")
                for x in v:
                    print("      ", str(x)[:120])
            else:
                print(f"  {k}: {v}")

        # 读回核对
        getart = {}
        def on_get(r):
            if "getArticle" in r.url:
                try:
                    getart.update(json.loads(r.text()))
                except Exception:
                    pass
        pg.on("response", on_get)
        pg.reload(wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(12000)

        imgs = pg.evaluate("""() => [...document.querySelectorAll('PRE.editor__inner img')].map(i => i.src)""")
        print(f"\n=== 读回：源码面板 {len(imgs)} 张图，占位图残留 {sum(1 for i in imgs if 'origin_url' in i)} ===")
        for i in imgs:
            print("   ", i[:115])

        if getart:
            print("\ngetArticle 顶层 keys:", list(getart.keys()))
            data = getart.get("data")
            print("data 类型:", type(data).__name__)
            if isinstance(data, dict):
                print("data keys:", list(data.keys())[:40])
                md = data.get("markdown_content") or data.get("markdowncontent") or ""
                if md:
                    with open(r"D:\Project\qlib\projects\style_post\temp\csdn_readback.md", "w",
                              encoding="utf-8") as f:
                        f.write(md)
                    print("markdown 长度:", len(md))
                    print("图片引用:")
                    for r in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", md):
                        print("   ", r[:115])

        pg.close()
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
