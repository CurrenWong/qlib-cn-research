"""掘金草稿清理（按坐标定位行尾的「⋯」）。删完后需要重新 publish 一次。"""

import asyncio

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

URL = "https://juejin.cn/editor/drafts"
TARGET_TITLE = "沪深300 × LightGBM 选股复盘"   # 第一轮的长标题稿（要删）


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(8000)

        # 目标标题的坐标 + 页面里所有「⋯」的坐标
        info = await pg.evaluate("""(t) => {
          const el = Array.from(document.querySelectorAll('*'))
              .filter(e => e.children.length === 0 && (e.textContent||'').includes(t))[0];
          if (!el) return {err:'no-title'};
          const r = el.getBoundingClientRect();
          const dots = Array.from(document.querySelectorAll('button,span,div,i,a'))
              .filter(e => {
                const s = (e.textContent||'').trim();
                return s === '...' || s === '⋯' || s === '···';
              })
              .map(e => {const b = e.getBoundingClientRect();
                         return {x:b.x, y:b.y, w:b.width, h:b.height};});
          return {title:{x:r.x, y:r.y, w:r.width, h:r.height}, dots};
        }""", TARGET_TITLE)
        print("定位:", info)
        if info.get("err"):
            await pg.close()
            await b.close()
            return
        t = info["title"]
        cands = [d for d in info["dots"]
                 if abs(d["y"] - t["y"]) < 60 and d["x"] > t["x"]]
        cands.sort(key=lambda d: abs(d["y"] - t["y"]))
        if not cands:
            print("找不到同行的 ⋯")
            await pg.close()
            await b.close()
            return
        target = cands[0]
        print("点击 ⋯ 于", target)
        await pg.mouse.click(target["x"] + target["w"] / 2, target["y"] + target["h"] / 2)
        await pg.wait_for_timeout(1500)

        clicked = await pg.evaluate("""() => {
          const items = Array.from(document.querySelectorAll('li,span,div,button,a'))
              .filter(e => e.children.length === 0 && /^(删除|废弃)$/.test((e.textContent||'').trim()));
          if (!items.length) return 'no-item';
          items[0].click();
          return 'clicked';
        }""")
        print("点删除:", clicked)
        await pg.wait_for_timeout(1500)
        conf = await pg.evaluate("""() => {
          const btns = Array.from(document.querySelectorAll('button'));
          const hit = btns.find(b => /确定|确认/.test(b.textContent||''));
          if (hit) { hit.click(); return 'confirmed'; }
          return 'no-confirm';
        }""")
        print("确认:", conf)
        await pg.wait_for_timeout(2500)
        left = await pg.evaluate("""() => {
          const t = document.body.innerText || '';
          return {hasShort: t.includes('沪深300×LightGBM选股复盘'),
                  hasLong: t.includes('沪深300 × LightGBM 选股复盘'),
                  count: (t.match(/文章草稿（(\\d+)）/ ) || [])[1],
                  titles: Array.from(document.querySelectorAll('div,p'))
                      .filter(e => e.children.length===0 && /沪深300/.test(e.textContent||''))
                      .map(e => e.textContent.trim().slice(0,40))};
        }""")
        print("复核:", left)
        await pg.screenshot(path=_ROOT + r"/projects/csi300_lgbm/docs/post/draft_shots/juejin_after2.png")
        await pg.close()
        await b.close()


asyncio.run(main())
