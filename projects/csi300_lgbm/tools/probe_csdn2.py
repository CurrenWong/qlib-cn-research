"""CSDN 草稿箱：把命中标题的元素及其祖先结构全部倒出来。"""

import asyncio


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto("https://mp.csdn.net/mp_blog/manage/article?type=0",
                      wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(7000)
        await pg.evaluate("""() => {
          const els = Array.from(document.querySelectorAll('span.nav-link,a,span,li'))
              .filter(e => (e.textContent||'').trim().startsWith('草稿箱'));
          if (els.length) els[0].click();
        }""")
        await pg.wait_for_timeout(8000)
        dump = await pg.evaluate("""() => {
          const hits = Array.from(document.querySelectorAll('*'))
              .filter(e => (e.textContent||'').includes('沪深300'));
          const small = hits.filter(e => e.children.length < 6).slice(0, 12);
          const out = small.map(e => {
            let p = e, chain = [];
            for (let i = 0; i < 4 && p; i++) {
              chain.push(p.tagName + '.' + (p.className||'').toString().split(' ').slice(0,3).join('.'));
              p = p.parentElement;
            }
            const links = Array.from(e.closest('div,li,tr').querySelectorAll('a'))
                .map(a => (a.textContent||'').trim().slice(0,12) + '|' + (a.getAttribute('href')||''));
            return {tag:e.tagName, cls:(e.className||'').toString().slice(0,60),
                    txt:(e.textContent||'').trim().slice(0,50), chain, links:links.slice(0,8)};
          });
          const body = document.body.innerText || '';
          return {out, bodyLen: body.length,
                  head: body.slice(0, 400).replace(/\\n/g,' / '),
                  allLinks: Array.from(document.querySelectorAll('a'))
                      .filter(a => (a.getAttribute('href')||'').includes('articleId'))
                      .map(a => (a.textContent||'').trim().slice(0,20) + '|' + a.getAttribute('href')).slice(0,20)};
        }""")
        print("命中:", len(dump["out"]))
        for o in dump["out"]:
            print("  ", o)
        print("正文头:", dump["head"])
        print("带 articleId 的链接:")
        for l in dump["allLinks"]:
            print("   ", l)
        await pg.close()
        await b.close()


asyncio.run(main())
