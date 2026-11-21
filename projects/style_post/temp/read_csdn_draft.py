"""只读：读 CSDN 草稿 171141543 的正文，确认 2 张失败图在草稿里的实际状态。

不写、不点发布、不调 saveArticle。
"""
import json
import sys

ART = "171141543"

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("no playwright")

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.new_page()
    pg.goto(f"https://editor.csdn.net/md?articleId={ART}", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(8000)

    print("URL:", pg.url)
    print("TITLE:", pg.title())

    # 从页面里把 markdown 源码抠出来（编辑器一般挂在某个全局变量或 textarea）
    md = pg.evaluate("""() => {
        const cands = ['window.__markdown_content__','window.markdownContent','window.articleMarkdown'];
        for (const k of cands) { if (window[k]) return window[k]; }
        const ta = document.querySelector('textarea');
        if (ta && ta.value && ta.value.length > 500) return ta.value;
        return null;
    }""")
    if md:
        print("markdown len:", len(md))
        imgs = [l.strip() for l in md.split("\\n") if "![" in l]
        print("图片引用数:", len(imgs))
        for i in imgs:
            print("   ", i[:160])
    else:
        print("未取到 markdown 源码，改为数 DOM 里的 img")
        info = pg.evaluate("""() => {
            const imgs = [...document.querySelectorAll('img')].map(i => ({src: i.src, w: i.naturalWidth, h: i.naturalHeight}));
            return {count: imgs.length, imgs};
        }""")
        print(json.dumps(info, ensure_ascii=False, indent=2)[:4000])

    pg.close()
    b.close()
