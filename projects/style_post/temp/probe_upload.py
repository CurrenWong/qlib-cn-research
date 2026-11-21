"""抓 CSDN 编辑器上传一张图的完整链路，并读出文档内容（看插入结果）。"""
import json
from playwright.sync_api import sync_playwright

ART = "171141543"
NET = []

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.new_page()

    def on_req(r):
        if r.method == "POST":
            try:
                body = r.post_data
            except Exception:
                body = None
            NET.append({"REQ": r.method, "url": r.url, "body": (body[:300] if body else None)})

    def on_resp(r):
        if r.request.method == "POST" and "csdn" in r.url:
            try:
                NET.append({"RESP": r.url, "text": r.text()[:1200]})
            except Exception:
                pass

    pg.on("request", on_req)
    pg.on("response", on_resp)

    pg.goto(f"https://editor.csdn.net/md?articleId={ART}", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(9000)

    def read_doc():
        return pg.evaluate("""() => {
            const pre = document.querySelector('PRE.editor__inner');
            if (!pre) return null;
            // 用 img-wrapper 里的 src 还原 markdown 图片引用
            let out = '';
            const walk = document.createTreeWalker(pre, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
            // 简单办法：取 textContent，再把 <img> 位置的信息补上
            const imgs = [...pre.querySelectorAll('img')].map(i => i.src);
            return {text: pre.textContent, imgs};
        }""")

    d0 = read_doc()
    print("=== 上传前 ===")
    print("文本长度:", len(d0["text"]) if d0 else None)
    print("img 数:", len(d0["imgs"]) if d0 else None)
    with open(r"D:\Project\qlib\projects\style_post\temp\doc_before.txt", "w", encoding="utf-8") as f:
        f.write(d0["text"])

    print("\n=== 上传 bias_percentile.png ===")
    NET.clear()
    pg.set_input_files("input.cfw-file-input",
                       r"D:\Project\qlib\projects\style_post\src\img\bias_percentile.png")
    pg.wait_for_timeout(12000)

    for n in NET:
        if "arms-retcode" in (n.get("REQ") or n.get("RESP") or ""):
            continue
        print("  ", json.dumps(n, ensure_ascii=False)[:700])

    d1 = read_doc()
    print("\n=== 上传后 ===")
    print("文本长度:", len(d1["text"]) if d1 else None)
    print("img 数:", len(d1["imgs"]) if d1 else None)
    if d1:
        new = [i for i in d1["imgs"] if i not in d0["imgs"]]
        print("新增 img:", new)
    with open(r"D:\Project\qlib\projects\style_post\temp\doc_after.txt", "w", encoding="utf-8") as f:
        f.write(d1["text"])

    pg.close()
    b.close()
