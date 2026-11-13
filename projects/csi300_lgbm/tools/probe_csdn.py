"""CSDN 草稿箱定位：创作中心内容管理 → 草稿 tab。"""

import asyncio


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto("https://mp.csdn.net/mp_blog/manage/article?type=0",
                      wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(8000)
        info = await pg.evaluate("""() => {
          const t = document.body.innerText || '';
          return {len:t.length, hasTitle:t.includes('沪深300'),
                  tabs:Array.from(document.querySelectorAll('a,span,li,div'))
                      .filter(e => e.children.length===0 && /草稿|全部|已发布|审核/.test((e.textContent||'').trim()))
                      .map(e => ({txt:(e.textContent||'').trim(), tag:e.tagName,
                                  cls:(e.className||'').toString().slice(0,50)}))
                      .slice(0,20)};
        }""")
        print("内容管理:", info)
        await pg.screenshot(path=r"D:\Project\qlib\projects\csi300_lgbm\docs\post\draft_shots\csdn_manage.png")

        clicked = await pg.evaluate("""() => {
          const els = Array.from(document.querySelectorAll('a,span,li,div'))
              .filter(e => e.children.length===0 && (e.textContent||'').trim()==='草稿');
          if (!els.length) return 'no-tab';
          els[0].click();
          return 'clicked';
        }""")
        print("点草稿:", clicked)
        await pg.wait_for_timeout(7000)
        after = await pg.evaluate("""() => {
          const t = document.body.innerText || '';
          return {url:location.href, len:t.length, hasTitle:t.includes('沪深300'),
                  rows:Array.from(document.querySelectorAll('tr,li,div'))
                      .filter(e => (e.textContent||'').includes('沪深300'))
                      .map(e => ({tag:e.tagName, txt:(e.textContent||'').trim().slice(0,70)}))
                      .slice(0,12)};
        }""")
        print("草稿页:", after)
        await pg.screenshot(path=r"D:\Project\qlib\projects\csi300_lgbm\docs\post\draft_shots\csdn_drafts.png")
        await pg.close()
        await b.close()


asyncio.run(main())
