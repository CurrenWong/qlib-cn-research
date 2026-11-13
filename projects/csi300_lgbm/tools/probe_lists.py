"""找草稿列表页（候选 URL 轮询）。"""

import asyncio

CANDS = {
    "juejin": [
        "https://juejin.cn/editor/drafts",
        "https://juejin.cn/editor/drafts/list",
        "https://juejin.cn/draft",
    ],
    "csdn": [
        "https://mp.csdn.net/mp_blog/manage/article?type=0",
        "https://mp.csdn.net/mp_blog/manage/article",
        "https://editor.csdn.net/md/manage",
        "https://editor.csdn.net/md/draft",
    ],
    "baijiahao": [
        "https://baijiahao.baidu.com/builder/rc/home#/articleManage?type=0",
        "https://baijiahao.baidu.com/builder/rc/articleManage?type=0",
        "https://baijiahao.baidu.com/builder/rc/home",
    ],
}

JS = """
() => {
  const t = document.body.innerText || '';
  const dels = Array.from(document.querySelectorAll('button,a,span,div'))
      .filter(e => e.children.length===0 && /^(删除|废弃|移除)$/.test((e.textContent||'').trim()));
  const menu = Array.from(document.querySelectorAll('button,a,span'))
      .filter(e => e.children.length===0 && /更多|操作|⋯|\\.\\.\\./.test((e.textContent||'').trim()));
  return {url: location.href, title: document.title, len: t.length,
          hasTitle: t.includes('沪深300'), delCount: dels.length,
          delSample: dels.slice(0,6).map(e => e.tagName+'|'+(e.className||'').toString().slice(0,40)),
          menuCount: menu.length,
          sample: t.slice(0,200).replace(/\\n/g,' / ')};
}
"""


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        for name, urls in CANDS.items():
            for url in urls:
                pg = await ctx.new_page()
                try:
                    await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await pg.wait_for_timeout(7000)
                    info = await pg.evaluate(JS)
                    print("=" * 10, name, url)
                    print("   ", info)
                    if info["hasTitle"] or info["delCount"]:
                        await pg.screenshot(path=fr"D:\Project\qlib\projects\csi300_lgbm\docs\post\draft_shots\{name}_list.png")
                        print("    → 截图已存")
                        await pg.close()
                        break
                except Exception as e:                               # noqa: BLE001
                    print("=" * 10, name, url, "失败:", str(e)[:120])
                finally:
                    try:
                        await pg.close()
                    except Exception:                               # noqa: BLE001
                        pass
        await b.close()


asyncio.run(main())
