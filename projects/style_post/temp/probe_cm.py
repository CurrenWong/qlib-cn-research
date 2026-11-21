"""探测 CSDN 编辑器里 CodeMirror 6 的 view 实例（拿全文 + 改全文的最稳路径）。"""
from playwright.sync_api import sync_playwright

ART = "171141543"

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.new_page()
    pg.goto(f"https://editor.csdn.net/md?articleId={ART}", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(10000)

    probe = pg.evaluate("""() => {
        const res = {};
        const cm = document.querySelector('.cm-content');
        const cmEditor = document.querySelector('.cm-editor');
        res.hasContent = !!cm;
        res.contentKeys = cm ? Object.keys(cm).filter(k=>/cm|view/i.test(k)) : [];
        res.editorKeys = cmEditor ? Object.keys(cmEditor).filter(k=>/cm|view/i.test(k)) : [];
        // CM6 把 view 挂在 contentDOM.cmView
        if (cm && cm.cmView) res.cmViewType = typeof cm.cmView;
        if (cm && cm.cmView && cm.cmView.view) {
            const v = cm.cmView.view;
            res.hasView = true;
            res.viewState = v.state ? v.state.doc.length : null;
        }
        // 全局
        res.globals = ['CodeMirror','EditorView','EditorState'].filter(k => window[k]);
        return res;
    }""")
    print("探测:", probe)

    # 退路：直接从 .cm-line 读全文
    lines = pg.evaluate("""() => [...document.querySelectorAll('.editor__inner .cm-line')].map(l => l.textContent)""")
    print(".cm-line 条数:", len(lines))
    text = "\n".join(lines)
    with open(r"D:\Project\qlib\projects\style_post\temp\csdn_draft_backup.md", "w", encoding="utf-8") as f:
        f.write(text)
    print("全文长度:", len(text))
    print("--- 图片引用 ---")
    for line in text.split("\n"):
        if "![" in line:
            print("   ", line.strip()[:170])

    pg.close()
    b.close()
