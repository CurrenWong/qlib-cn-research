"""找掘金草稿行尾的「⋯」控件：列出标题附近的所有元素。"""

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
        info = await pg.evaluate("""(t) => {
          const el = Array.from(document.querySelectorAll('*'))
              .filter(e => e.children.length === 0 && (e.textContent||'').includes(t))[0];
          if (!el) return {err:'no-title'};
          const r = el.getBoundingClientRect();
          const near = [];
          document.querySelectorAll('*').forEach(e => {
            const b = e.getBoundingClientRect();
            if (b.width === 0 || b.height === 0) return;
            if (b.x > r.x - 40 && b.x < r.x + 600 &&
                b.y > r.y - 60 && b.y < r.y + 120) {
              near.push({tag:e.tagName, cls:(e.className||'').toString().slice(0,50),
                         txt:(e.textContent||'').trim().slice(0,20),
                         x:Math.round(b.x), y:Math.round(b.y),
                         w:Math.round(b.width), h:Math.round(b.height)});
            }
          });
          return {title:{x:Math.round(r.x), y:Math.round(r.y)}, near:near.slice(0,40)};
        }""", TARGET)
        print("标题:", info.get("title"), "| 候选:", len(info.get("near", [])))
        for n in info.get("near", []):
            print("   ", n)
        await pg.screenshot(path=r"D:\Project\qlib\projects\csi300_lgbm\docs\post\draft_shots\juejin_probe.png")
        await pg.close()
        await b.close()


asyncio.run(main())
