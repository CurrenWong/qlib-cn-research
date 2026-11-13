"""探测三个平台的"草稿列表 / 删除"接口（只读探测，先不删）。"""

import asyncio

PAGES = {
    "csdn": "https://editor.csdn.net/md?articleId=169915486",
    "juejin": "https://juejin.cn/editor/drafts/list",
    "baijiahao": "https://baijiahao.baidu.com/builder/rc/home",
}

PROBES = {
    "csdn": [
        ("GET", "https://blog.csdn.net/phoenix/web/v1/article/list?page=1&size=20&status=2"),
        ("GET", "https://blog.csdn.net/phoenix/web/v1/article/list?page=1&size=20&status=0"),
    ],
    "juejin": [
        ("POST", "https://api.juejin.cn/content_api/v1/draft/query?aid=2608&uuid=&spider=0"),
    ],
    "baijiahao": [
        ("GET", "https://baijiahao.baidu.com/builder/rc/api/content/list?page=1&size=20&status=0"),
        ("GET", "https://baijiahao.baidu.com/builder/rc/api/draft/list?page=1&size=20"),
    ],
}

JS = """
async ({method, url}) => {
  try {
    const opt = {method, credentials:'include', headers:{'Accept':'application/json'}};
    if (method === 'POST') {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify({cursor:'0', size:20, sort_type:0});
    }
    const r = await fetch(url, opt);
    const t = await r.text();
    return {status:r.status, body:t.slice(0,700)};
  } catch (e) { return {err:String(e)}; }
}
"""


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        for name, page_url in PAGES.items():
            pg = await ctx.new_page()
            try:
                await pg.goto(page_url, wait_until="domcontentloaded", timeout=90000)
                await pg.wait_for_timeout(6000)
                print("=" * 18, name, "=" * 18)
                for method, url in PROBES[name]:
                    res = await pg.evaluate(JS, {"method": method, "url": url})
                    print(f"  {method} {url[:90]}")
                    print("    ", str(res.get("body", res.get("err")))[:400])
            except Exception as e:                                   # noqa: BLE001
                print("=" * 18, name, "失败:", e)
            finally:
                await pg.close()
        await b.close()


asyncio.run(main())
