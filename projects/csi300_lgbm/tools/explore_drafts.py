"""探查各平台的草稿列表页：截图 + 列出标题命中与删除按钮。

用法：python explore_drafts.py
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"D:\Project\qlib\projects\csi300_lgbm\docs\post\draft_shots")
OUT.mkdir(parents=True, exist_ok=True)

PAGES = {
    "zhihu": "https://zhuanlan.zhihu.com/drafts",
    "csdn": "https://editor.csdn.net/md",
    "juejin": "https://juejin.cn/editor/drafts/list",
    "baijiahao": "https://baijiahao.baidu.com/builder/rc/home",
    "bilibili": "https://member.bilibili.com/platform/upload/text/draft",
}

TITLE = "沪深300"

JS = """
() => {
  const out = {title: document.title, url: location.href, dels: [], rows: []};
  const dels = Array.from(document.querySelectorAll('a,button,span,i,div'))
    .filter(e => e.children.length === 0 && /删除|移除|废弃/.test(e.textContent || ''));
  out.dels = dels.slice(0, 40).map(e => ({
      tag: e.tagName, cls: (e.className || '').toString().slice(0, 60),
      txt: (e.textContent || '').trim().slice(0, 20)}));
  const hits = Array.from(document.querySelectorAll('*'))
      .filter(e => e.children.length === 0 && (e.textContent || '').includes('沪深300'));
  out.rows = hits.slice(0, 20).map(e => ({
      tag: e.tagName, cls: (e.className || '').toString().slice(0, 60),
      txt: (e.textContent || '').trim().slice(0, 80)}));
  out.bodyLen = (document.body.innerText || '').length;
  out.hasTitle = (document.body.innerText || '').includes('沪深300');
  return out;
}
"""


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        for name, url in PAGES.items():
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
                info = page.evaluate(JS)
                print("=" * 20, name, "=" * 20)
                print("  title:", info["title"], "| url:", info["url"])
                print("  bodyLen:", info["bodyLen"], "| 含标题:", info["hasTitle"])
                print("  删除类元素:", len(info["dels"]))
                for d in info["dels"][:12]:
                    print("    ", d)
                print("  标题命中:", len(info["rows"]))
                for r in info["rows"][:8]:
                    print("    ", r)
                page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            except Exception as e:                                   # noqa: BLE001
                print("=" * 20, name, "失败:", e)
            finally:
                page.close()


if __name__ == "__main__":
    main()
