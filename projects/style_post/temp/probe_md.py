"""探 CSDN 编辑器：Markdown 源码页 + 图片上传链路（拿到真实 URL 的办法）。"""
import json
from playwright.sync_api import sync_playwright

ART = "171141543"
UP = []

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.new_page()

    def on_req(r):
        u = r.url
        if "upload" in u.lower() or "oss" in u.lower() or "resource-api" in u.lower():
            try:
                body = r.post_data
            except Exception:
                body = None
            UP.append({"m": r.method, "url": u, "body": (body[:500] if body else None)})

    def on_resp(r):
        if "upload" in r.url.lower() or "resource-api" in r.url.lower():
            try:
                txt = r.text()[:600]
            except Exception:
                txt = "<no body>"
            UP.append({"resp": r.url, "text": txt})

    pg.on("request", on_req)
    pg.on("response", on_resp)

    pg.goto(f"https://editor.csdn.net/md?articleId={ART}", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(9000)

    # --- 切到 Markdown 页 ---
    print("=== 点击 Markdown 页签 ===")
    pg.evaluate("""() => {
        const b = [...document.querySelectorAll('.nav-tab-btn')].find(x => x.innerText.trim() === 'Markdown');
        if (b) b.click();
        return !!b;
    }""")
    pg.wait_for_timeout(4000)

    print("=== textarea ===")
    print(pg.evaluate("""() => [...document.querySelectorAll('textarea')].map(t => ({
        id: t.id, cls: (t.className||'').toString().slice(0,60), len: (t.value||'').length,
        visible: t.offsetParent !== null, parent: t.parentElement ? t.parentElement.className.slice(0,60) : null
    }))"""))

    md = pg.evaluate("""() => {
        const ts = [...document.querySelectorAll('textarea')].filter(t => t.value && t.value.length > 500);
        return ts.length ? ts[0].value : null;
    }""")
    if md:
        with open(r"D:\Project\qlib\projects\style_post\temp\csdn_md_source.md", "w", encoding="utf-8") as f:
            f.write(md)
        print("\nMarkdown 源码长度:", len(md))
        print("--- 图片引用 ---")
        for line in md.split("\n"):
            if "![" in line:
                print("   ", line.strip()[:160])
        print("--- 开头 200 字 ---")
        print(md[:200])
    else:
        print("\n!! Markdown 页没拿到 textarea")

    # --- 试上传一张图，走编辑器自己的上传链路 ---
    print("\n=== 触发图片上传（编辑器自带 file input） ===")
    try:
        pg.set_input_files("input.cfw-file-input",
                           r"D:\Project\qlib\projects\style_post\src\img\bias_percentile.png")
        pg.wait_for_timeout(9000)
    except Exception as e:
        print("set_input_files 失败:", e)

    for u in UP:
        print("  ", json.dumps(u, ensure_ascii=False)[:500])

    # 上传后源码变成什么样
    md2 = pg.evaluate("""() => {
        const ts = [...document.querySelectorAll('textarea')].filter(t => t.value && t.value.length > 500);
        return ts.length ? ts[0].value : null;
    }""")
    if md2:
        print("\n=== 上传后源码里的图片引用 ===")
        for line in md2.split("\n"):
            if "![" in line:
                print("   ", line.strip()[:170])

    pg.close()
    b.close()
