"""只读：细查 CSDN 草稿 171141543 里的图片状态（哪些是远端图、哪些断链）。"""
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
    pg.wait_for_timeout(10000)

    info = pg.evaluate("""() => {
        const imgs = [...document.querySelectorAll('img')];
        const remote = imgs.filter(i => !i.src.startsWith('data:'));
        const broken = remote.filter(i => i.complete && i.naturalWidth === 0);
        return {
            total: imgs.length,
            remoteCount: remote.length,
            brokenCount: broken.length,
            remote: remote.map(i => ({src: i.src, ok: i.complete && i.naturalWidth > 0,
                                      w: i.naturalWidth, alt: (i.alt||'').slice(0,60)})),
        };
    }""")
    print("DOM img 总数:", info["total"], "| 远端图:", info["remoteCount"], "| 断链:", info["brokenCount"])
    for r in info["remote"]:
        print(("  OK   " if r["ok"] else "  BROKEN ") + r["src"][:130] + "  | alt=" + r["alt"])

    # 找正文里的 markdown / 源码视图
    md = pg.evaluate("""() => {
        for (const k of ['__markdown_content__','markdownContent','articleMarkdown','window.mdContent']) {
            if (window[k]) return String(window[k]).slice(0, 200000);
        }
        const ta = [...document.querySelectorAll('textarea')];
        for (const t of ta) if (t.value && t.value.length > 500) return t.value.slice(0, 200000);
        return null;
    }""")
    if md:
        print("\n=== markdown 源码片段里的图片引用 ===")
        for line in md.split("\n"):
            if "![" in line:
                print("  ", line.strip()[:180])
    else:
        print("\n(未取到 markdown 源码)")

    pg.close()
    b.close()
