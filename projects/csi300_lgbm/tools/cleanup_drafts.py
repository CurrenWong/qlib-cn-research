"""清理本轮在各平台建出来的重复草稿。

只删**本次这篇文章**的草稿（按标题前缀匹配），保留每平台最新的一条。
B站走 API（有 csrf），知乎走草稿页按钮；其他平台先只读探查。

用法：python cleanup_drafts.py <平台> [<平台> ...]
     平台名：bili zhihu juejin csdn baijiahao
"""

import asyncio
import sys

TITLE = "沪深300"
KEEP_LATEST = True

# 本轮留下的草稿标识（标题 + 平台自己给的 id）
BILI = {"aids": [373535, 373555]}       # 旧的 373535、新的 373555
ZHIHU = {"ids": ["2100728637385454845", "2100868424528353196"]}


async def clean_bili(pw):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        cookies = await ctx.cookies()
        csrf = next((c["value"] for c in cookies if c["name"] == "bili_jct"), "")
        pg = await ctx.new_page()
        await pg.goto("https://member.bilibili.com/platform/upload/text/edit?aid=373555",
                      wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(6000)
        keep = max(BILI["aids"])
        for aid in BILI["aids"]:
            if aid == keep:
                print(f"  B站 aid={aid} 保留（最新）")
                continue
            res = await pg.evaluate("""async ({aid, csrf}) => {
              const fd = new URLSearchParams();
              fd.append('aid', String(aid)); fd.append('csrf', csrf);
              const r = await fetch('https://api.bilibili.com/x/article/creative/draft/delete', {
                method:'POST', credentials:'include',
                headers:{'Content-Type':'application/x-www-form-urlencoded'},
                body: fd.toString()});
              return {status:r.status, body:(await r.text()).slice(0,200)};
            }""", {"aid": aid, "csrf": csrf})
            print(f"  B站 删除 aid={aid}: {res['status']} {res['body']}")
        await pg.close()
        await b.close()


async def clean_zhihu(pw):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto("https://zhuanlan.zhihu.com/drafts",
                      wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(6000)
        # 收集标题命中项，保留最后一条（列表按时间倒序，最新在前）
        items = await pg.evaluate("""() => {
          const titles = Array.from(document.querySelectorAll('a.ColumnDraftItem-title'))
              .filter(a => (a.textContent||'').includes('沪深300'));
          return titles.map(a => {
            const card = a.closest('div[class*=ColumnDraftItem]') || a.parentElement.parentElement;
            const btn = card ? card.querySelector('button[class*=deleteButton]') : null;
            return {title:(a.textContent||'').trim(), href:a.getAttribute('href'), hasBtn: !!btn};
          });
        }""")
        print("  知乎命中草稿:", [(i["title"][:30], i["href"]) for i in items])
        for idx, it in enumerate(items):
            # 列表通常按更新时间倒序：保留第一条（最新），删后面的
            if idx == 0:
                print(f"  知乎 保留：{it['title'][:40]}")
                continue
            ok = await pg.evaluate("""(idx) => {
              const titles = Array.from(document.querySelectorAll('a.ColumnDraftItem-title'))
                  .filter(a => (a.textContent||'').includes('沪深300'));
              const a = titles[idx];
              if (!a) return 'no-title';
              const card = a.closest('div[class*=ColumnDraftItem]') || a.parentElement.parentElement;
              const btn = card ? card.querySelector('button[class*=deleteButton]') : null;
              if (!btn) return 'no-btn';
              btn.click();
              return 'clicked';
            }""", idx)
            print(f"  知乎 删除 {it['title'][:30]}: {ok}")
            await pg.wait_for_timeout(1500)
            # 弹窗确认
            conf = await pg.evaluate("""() => {
              const btns = Array.from(document.querySelectorAll('button'));
              const hit = btns.find(b => /确定|确认|删除/.test(b.textContent||''));
              if (hit) { hit.click(); return 'confirmed:' + (hit.textContent||'').trim(); }
              return 'no-confirm';
            }""")
            print("     确认:", conf)
            await pg.wait_for_timeout(2000)
        await pg.close()
        await b.close()


async def explore(name, url):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        try:
            await pg.goto(url, wait_until="domcontentloaded", timeout=90000)
            await pg.wait_for_timeout(9000)
            info = await pg.evaluate("""() => {
              const t = document.body.innerText || '';
              const dels = Array.from(document.querySelectorAll('button,a,span'))
                  .filter(e => e.children.length===0 && /删除|废弃|移除/.test(e.textContent||''));
              return {url: location.href, title: document.title, len: t.length,
                      hasTitle: t.includes('沪深300'), dels: dels.length,
                      sample: t.slice(0, 300).replace(/\\n/g,' | '),
                      delTags: dels.slice(0,8).map(e => e.tagName + '.' + (e.className||'').toString().slice(0,40))};
            }""")
            print("=" * 12, name, "=" * 12)
            print("  ", info)
        except Exception as e:                                       # noqa: BLE001
            print("=" * 12, name, "失败:", e)
        finally:
            await pg.close()
            await b.close()


async def main():
    targets = sys.argv[1:] or ["bili", "zhihu"]
    for t in targets:
        if t == "bili":
            print("== B站 ==")
            await clean_bili(None)
        elif t == "zhihu":
            print("== 知乎 ==")
            await clean_zhihu(None)
        elif t == "juejin":
            await explore("掘金", "https://juejin.cn/editor/drafts/list")
        elif t == "csdn":
            await explore("CSDN", "https://mp.csdn.net/mp_blog/home")
        elif t == "baijiahao":
            await explore("百家号", "https://baijiahao.baidu.com/builder/rc/home")


if __name__ == "__main__":
    asyncio.run(main())
