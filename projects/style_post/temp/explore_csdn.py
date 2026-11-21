"""探查 CSDN 编辑器结构（只读）：markdown 源码在哪、坏图的 DOM 上下文、上传入口。"""
import json
from playwright.sync_api import sync_playwright

ART = "171141543"

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.new_page()
    pg.goto(f"https://editor.csdn.net/md?articleId={ART}", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(10000)

    print("=== 顶层结构 ===")
    print(pg.evaluate("""() => {
        const out = [];
        document.querySelectorAll('div,section,textarea,input').forEach(el => {
            const c = (el.className||'').toString();
            const id = el.id||'';
            if (/editor|markdown|md-|source|code|monaco|cm-|bytemd|vditor/i.test(c+' '+id))
                out.push(el.tagName+'#'+id+'.'+c.slice(0,80)+' type='+(el.type||''));
        });
        return out.slice(0,40);
    }"""))

    print("\n=== file input ===")
    print(pg.evaluate("""() => [...document.querySelectorAll('input[type=file]')].map(i => ({
        accept: i.accept, name: i.name, cls: (i.className||'').toString().slice(0,60),
        visible: i.offsetParent !== null, outer: i.outerHTML.slice(0,160)}))"""))

    print("\n=== 坏图的 DOM 上下文 ===")
    print(pg.evaluate("""() => {
        const bad = [...document.querySelectorAll('img')].filter(i => i.src.includes('origin_url'));
        return bad.map(i => {
            let p = i, chain = [];
            for (let k=0;k<5 && p;k++){ chain.push(p.tagName+'.'+((p.className||'')+'').toString().slice(0,50)); p = p.parentElement; }
            return {src: i.src.slice(0,120), alt: i.alt, chain};
        });
    }"""))

    print("\n=== 全局变量探测 ===")
    print(pg.evaluate("""() => {
        const keys = Object.keys(window).filter(k => /markdown|md_|content|editor|article|draft/i.test(k));
        return keys.slice(0,60);
    }"""))

    print("\n=== 尝试取 markdown 源码 ===")
    md = pg.evaluate("""() => {
        // 1) Monaco
        try {
          const m = window.monaco;
          if (m && m.editor) {
            const models = m.editor.getModels();
            if (models.length) return {from:'monaco', text: models[0].getValue()};
          }
        } catch(e) {}
        // 2) CodeMirror
        try {
          const cms = document.querySelectorAll('.CodeMirror');
          for (const c of cms) { const cm = c.CodeMirror; if (cm && cm.getValue().length>500) return {from:'codemirror', text: cm.getValue()}; }
        } catch(e) {}
        // 3) textarea
        const ta = [...document.querySelectorAll('textarea')];
        for (const t of ta) if (t.value && t.value.length>500) return {from:'textarea', text: t.value};
        // 4) 常见全局
        for (const k of ['__markdown_content__','markdownContent','articleMarkdown','mdContent','INITIAL_DATA'])
            if (window[k] && typeof window[k]==='string' && window[k].length>500) return {from:'global:'+k, text: window[k]};
            else if (window[k] && typeof window[k]==='object') return {from:'globalobj:'+k, text: JSON.stringify(window[k]).slice(0,500)};
        return null;
    }""")
    if md:
        print("来源:", md["from"], "长度:", len(md["text"]))
        with open(r"D:\Project\qlib\projects\style_post\temp\csdn_draft_backup.md", "w", encoding="utf-8") as f:
            f.write(md["text"])
        print("已备份 -> temp/csdn_draft_backup.md")
        for line in md["text"].split("\n"):
            if "![" in line:
                print("   ", line.strip()[:170])
    else:
        print("!! 没取到")

    pg.close()
    b.close()
