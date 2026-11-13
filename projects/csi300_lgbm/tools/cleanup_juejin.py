"""掘金草稿清理：点行尾的「⋯」菜单 → 删除。保留最新一条。"""

import asyncio

URL = "https://juejin.cn/editor/drafts"
KEEP_TITLE = "沪深300×LightGBM选股复盘"      # 保留（无空格的短标题）
OLD_TITLE = "沪深300 × LightGBM 选股复盘"     # 删除（第一轮的长标题）


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(8000)

        # 找到旧标题所在的行，再在该行里点「⋯」
        info = await pg.evaluate("""(oldTitle) => {
          const nodes = Array.from(document.querySelectorAll('div,p,li,section'))
              .filter(e => (e.textContent||'').includes(oldTitle) && e.children.length < 8);
          const row = nodes[nodes.length - 1];
          if (!row) return 'no-row';
          const more = Array.from(row.querySelectorAll('button,span,div,i'))
              .filter(e => (e.textContent||'').trim() === '...' || (e.textContent||'').trim() === '⋯');
          if (!more.length) return 'no-more';
          more[more.length-1].click();
          return 'clicked-more';
        }""", OLD_TITLE)
        print("点菜单:", info)
        await pg.wait_for_timeout(1500)

        menu = await pg.evaluate("""() => {
          const items = Array.from(document.querySelectorAll('li,span,div,button,a'))
              .filter(e => e.children.length === 0 && /^(删除|废弃)$/.test((e.textContent||'').trim()));
          return items.map(e => e.textContent.trim());
        }""")
        print("菜单项:", menu)
        clicked = await pg.evaluate("""() => {
          const items = Array.from(document.querySelectorAll('li,span,div,button,a'))
              .filter(e => e.children.length === 0 && /^(删除|废弃)$/.test((e.textContent||'').trim()));
          if (!items.length) return 'no-item';
          items[0].click();
          return 'clicked:' + items[0].textContent.trim();
        }""")
        print("点删除:", clicked)
        await pg.wait_for_timeout(2000)

        # 确认弹窗
        conf = await pg.evaluate("""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          const hit = btns.find(b => /确定|确认|删除/.test(b.textContent||''));
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
        await pg.screenshot(path=r"D:\Project\qlib\projects\csi300_lgbm\docs\post\draft_shots\juejin_after.png")
        await pg.close()
        await b.close()


asyncio.run(main())
