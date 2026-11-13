"""CSDN 内容管理：轮询 type 参数，找到含我们草稿的 tab。"""

import asyncio


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        for t in range(0, 8):
            pg = await ctx.new_page()
            try:
                await pg.goto(f"https://mp.csdn.net/mp_blog/manage/article?type={t}",
                              wait_until="domcontentloaded", timeout=60000)
                await pg.wait_for_timeout(6000)
                info = await pg.evaluate("""() => {
                  const body = document.body.innerText || '';
                  const ids = Array.from(document.querySelectorAll('a[href*="articleId"]'))
                      .map(a => a.getAttribute('href').split('articleId=')[1]);
                  return {len: body.length, has: body.includes('沪深300'),
                          ids: Array.from(new Set(ids)).slice(0, 15),
                          active: (document.querySelector('span.nav-link.active')||{}).innerText};
                }""")
                print(f"type={t} 命中={info['has']} active={info['active']} ids={info['ids']}")
            except Exception as e:                                   # noqa: BLE001
                print(f"type={t} 失败 {e}")
            finally:
                await pg.close()
        await b.close()


asyncio.run(main())
