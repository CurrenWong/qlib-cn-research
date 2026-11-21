"""抓 CSDN 编辑器的真实网络调用：加载草稿 + 保存草稿的 endpoint / body / 签名头。

只读为主；最后点一次「保存草稿」是为了抓到 saveArticle 的真实请求体
（保存的是当前已有的草稿状态，不会发布，也不会改内容）。
"""
import json
from playwright.sync_api import sync_playwright

ART = "171141543"
CAP = []

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.new_page()

    def on_req(r):
        if "bizapi.csdn.net" in r.url or "csdnimg" in r.url or "upload" in r.url.lower():
            try:
                body = r.post_data
            except Exception:
                body = None
            CAP.append({
                "method": r.method, "url": r.url,
                "headers": {k: v for k, v in r.headers.items()
                            if k.lower() in ("x-ca-key", "x-ca-nonce", "x-ca-signature",
                                             "x-ca-signature-headers", "content-type")},
                "post": (body[:4000] if body else None),
            })

    pg.on("request", on_req)
    pg.goto(f"https://editor.csdn.net/md?articleId={ART}", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(10000)

    print("=== 可编辑性 ===")
    print(pg.evaluate("""() => {
        const pre = document.querySelector('PRE.editor__inner');
        const ed = document.querySelector('.editor');
        return {
            preContentEditable: pre ? pre.getAttribute('contenteditable') : null,
            preIsContentEditable: pre ? pre.isContentEditable : null,
            edContentEditable: ed ? ed.getAttribute('contenteditable') : null,
            edIsContentEditable: ed ? ed.isContentEditable : null,
            activeEditable: document.activeElement ? document.activeElement.className : null,
        };
    }"""))

    print("\n=== 按钮清单 ===")
    print(pg.evaluate("""() => [...document.querySelectorAll('button,a[class*=btn],[class*=button]')]
        .map(b => (b.innerText||'').trim() + '  [' + (b.className||'').toString().slice(0,45) + ']')
        .filter(t => t && t.length>1 && t.length<70).slice(0,40)"""))

    print("\n=== 加载阶段的网络调用 ===")
    for c in CAP:
        print(f"{c['method']} {c['url'][:150]}")
        if c["headers"]:
            print("     headers:", json.dumps(c["headers"], ensure_ascii=False))
        if c["post"]:
            print("     body:", c["post"][:600])

    pg.close()
    b.close()
