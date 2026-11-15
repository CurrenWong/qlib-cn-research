"""百家号草稿清理探查：进入内容管理 → 草稿箱 → 定位标题行。"""

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
        await pg.goto("https://baijiahao.baidu.com/builder/rc/home",
                      wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(7000)

        # 点左侧「内容管理」
        nav = await pg.evaluate("""() => {
          const els = Array.from(document.querySelectorAll('a,span,div'))
              .filter(e => e.children.length === 0 && (e.textContent||'').trim() === '内容管理');
          return els.map(e => ({tag:e.tagName, href:e.getAttribute('href'), cls:(e.className||'').toString().slice(0,60)}));
        }""")
        print("内容管理入口:", nav)
        await pg.evaluate("""() => {
          const els = Array.from(document.querySelectorAll('a,span,div'))
              .filter(e => e.children.length === 0 && (e.textContent||'').trim() === '内容管理');
          if (els.length) els[0].click();
        }""")
        await pg.wait_for_timeout(6000)
        print("当前 url:", pg.url)
        await pg.screenshot(path=_ROOT + r"/projects/csi300_lgbm/docs/post/draft_shots/bjh_manage.png")

        tabs = await pg.evaluate("""() => {
          const t = document.body.innerText || '';
          return {len:t.length, hasTitle:t.includes('沪深300'),
                  tabs:Array.from(document.querySelectorAll('a,span,div'))
                      .filter(e => e.children.length===0 && /草稿|作品|全部|已发布/.test((e.textContent||'').trim()))
                      .map(e => ({txt:(e.textContent||'').trim(), tag:e.tagName, cls:(e.className||'').toString().slice(0,40)}))
                      .slice(0,15)};
        }""")
        print("页面:", tabs)
        await pg.close()
        await b.close()


asyncio.run(main())
