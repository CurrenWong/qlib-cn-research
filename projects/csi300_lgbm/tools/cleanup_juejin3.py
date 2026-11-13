"""掘金草稿清理（按 .draft 容器 → .menu → 删除）。"""

import asyncio

URL = "https://juejin.cn/editor/drafts"
TARGET = "沪深300 × LightGBM 选股复盘"


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(8000)
        res = await pg.evaluate("""(t) => {
          const card = Array.from(document.querySelectorAll('div.draft'))
              .find(d => (d.textContent||'').includes(t));
          if (!card) return 'no-card';
          const menu = card.querySelector('div.menu') || card;
          const del = Array.from(menu.querySelectorAll('*'))
              .find(e => e.children.length === 0 && (e.textContent||'').trim() === '删除');
          if (!del) return 'no-del';
          del.click();
          return 'clicked';
        }""", TARGET)
        print("点删除:", res)
        await pg.wait_for_timeout(1800)
        conf = await pg.evaluate("""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          const hit = btns.find(b => /确定|确认/.test(b.textContent||''));
          if (hit) { hit.click(); return 'confirmed:' + (hit.textContent||'').trim(); }
          return 'no-confirm';
        }""")
        print("确认:", conf)
        await pg.wait_for_timeout(2500)
        left = await pg.evaluate("""() => {
          const t = document.body.innerText || '';
          return {hasShort: t.includes('沪深300×LightGBM选股复盘'),
                  hasLong: t.includes('沪深300 × LightGBM 选股复盘'),
                  count: (t.match(/文章草稿（(\\d+)）/ ) || [])[1]};
        }""")
        print("复核:", left)
        await pg.close()
        await b.close()


asyncio.run(main())
