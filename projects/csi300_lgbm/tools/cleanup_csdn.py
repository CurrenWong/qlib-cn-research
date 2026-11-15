"""CSDN 草稿箱清理：创作中心 → 草稿箱 → 删掉本次留下的多余草稿，只保留最好的一条。"""

import asyncio

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

KEEP = "169919034"          # pub6：10 张图里成功 9 张（只差 fig1_nav）
TITLE = "沪深300"


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = await ctx.new_page()
        await pg.goto("https://mp.csdn.net/mp_blog/manage/article?type=0",
                      wait_until="domcontentloaded", timeout=90000)
        await pg.wait_for_timeout(7000)
        clicked = await pg.evaluate("""() => {
          const els = Array.from(document.querySelectorAll('span.nav-link,a,span,li'))
              .filter(e => (e.textContent||'').trim().startsWith('草稿箱'));
          if (!els.length) return 'no-tab';
          els[0].click();
          return 'clicked:' + (els[0].textContent||'').trim();
        }""")
        print("点草稿箱:", clicked)
        await pg.wait_for_timeout(7000)

        rows = await pg.evaluate("""(title) => {
          const out = [];
          document.querySelectorAll('div.article-list-item, tr, li').forEach(r => {
            const t = (r.textContent||'');
            if (!t.includes(title)) return;
            const link = r.querySelector('a[href*="articleId"], a[href*="editor.csdn"]');
            const btns = Array.from(r.querySelectorAll('a,button,span,i'))
                .filter(e => e.children.length===0 && e.textContent.trim())
                .map(e => (e.textContent||'').trim());
            out.push({txt:t.trim().slice(0,50),
                      href: link ? link.getAttribute('href') : null,
                      btns: btns.slice(0,12)});
          });
          return out;
        }""", TITLE)
        print("命中草稿行:", len(rows))
        for r in rows:
            print("   ", r["href"], "|", r["txt"], "|", r["btns"])

        # 逐条删除（保留 KEEP）
        for r in rows:
            if not r["href"] or KEEP in r["href"]:
                print("   保留:", r["href"], r["txt"][:30])
                continue
            aid = r["href"].split("articleId=")[-1].split("&")[0]
            res = await pg.evaluate("""async (aid) => {
              // 优先用创作中心的删除接口
              const candidates = [
                {u:'https://blog.csdn.net/phoenix/web/v1/article/delete?articleId=' + aid, m:'POST', body: {articleId: aid}},
                {u:'https://mp.csdn.net/mp_blog/api/article/delete?articleId=' + aid, m:'POST', body: {articleId: aid}},
              ];
              const out = [];
              for (const c of candidates) {
                try {
                  const opt = {method:c.m, credentials:'include',
                               headers:{'Content-Type':'application/json'},
                               body: JSON.stringify(c.body)};
                  const r = await fetch(c.u, opt);
                  out.push(c.u.slice(0,60) + ' -> ' + r.status + ' ' + (await r.text()).slice(0,120));
                } catch (e) { out.push(c.u.slice(0,60) + ' -> ERR ' + String(e).slice(0,80)); }
              }
              return out;
            }""", aid)
            print("   删除尝试", aid, res)
        await pg.screenshot(path=_ROOT + r"/projects/csi300_lgbm/docs/post/draft_shots/csdn_drafts2.png")
        await pg.close()
        await b.close()


asyncio.run(main())
