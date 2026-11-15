"""CSDN：翻页找到我们建的草稿，列出每行的操作按钮。"""

import asyncio

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto("https://mp.csdn.net/mp_blog/manage/article?type=0",
                      wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(7000)
        found = False
        for i in range(20):
            hit = await pg.evaluate("""() => (document.body.innerText||'').includes('沪深300')""")
            if hit:
                found = True
                print(f"第 {i+1} 页命中")
                break
            ok = await pg.evaluate("""() => {
              const cands = Array.from(document.querySelectorAll('a,button,li,span'))
                  .filter(e => e.children.length===0 && /^(下一页|下页|>)$/.test((e.textContent||'').trim()));
              const next = cands.find(e => (e.textContent||'').includes('下')) || cands[cands.length-1];
              if (!next) return 'no-next';
              next.click();
              return 'clicked:' + (next.textContent||'').trim();
            }""")
            print(f"  第 {i+1} 页 未命中 → {ok}")
            if not ok.startswith("clicked"):
                break
            await pg.wait_for_timeout(3500)
        if found:
            rows = await pg.evaluate("""() => {
              const out = [];
              document.querySelectorAll('tr').forEach(tr => {
                const t = tr.textContent || '';
                if (!t.includes('沪深300')) return;
                const link = tr.querySelector('a[href*="articleId"]');
                const acts = Array.from(tr.querySelectorAll('a,button'))
                    .map(a => ((a.textContent||'').trim() + '|' + (a.getAttribute('href')||'')).slice(0,60));
                out.push({txt:t.trim().slice(0,60), href: link?link.getAttribute('href'):null, acts});
              });
              return out;
            }""")
            for r in rows:
                print("  行:", r["href"], "|", r["txt"], "|", r["acts"][:8])
            await pg.screenshot(path=_ROOT + r"/projects/csi300_lgbm/docs/post/draft_shots/csdn_ours.png")
        else:
            print("翻完也没命中")
        await pg.close()
        await b.close()


asyncio.run(main())
