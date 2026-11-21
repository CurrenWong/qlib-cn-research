"""CSDN 草稿最终核验：数字序列、正文一致性、8 张图是否真能加载、是否仍是草稿。"""
import json
import re
import urllib.request
from playwright.sync_api import sync_playwright

ART = "171141543"
NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")
DIST_ART = r"D:\Project\qlib\projects\style_post\dist\csdn\article.md"
SRC_ART = r"D:\Project\qlib\projects\style_post\src\article.md"


def strip_adapter(body):
    b = body
    if b.startswith("> CSDN 版"):
        b = b.split("\n\n", 1)[1]
    b = re.sub(r"^!\[\]\(cover\.png\)\n+", "", b)
    i = b.rfind("\n---\n\n")
    if i != -1:
        b = b[:i]
    return b.strip()


def strip_img(md):
    """把图片引用抹掉再比文本，URL 长度差异不算内容差异。"""
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "[IMG]", md)


with sync_playwright() as p:
    b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = b.contexts[0]
    pg = ctx.new_page()

    get = {}

    def on_get(r):
        if "getArticle" in r.url:
            try:
                get.update(json.loads(r.text()))
            except Exception:
                pass

    pg.on("response", on_get)
    pg.goto(f"https://editor.csdn.net/md?articleId={ART}",
            wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(20000)

    d = get.get("data") or {}
    md = d.get("markdowncontent") or ""
    html = d.get("content") or ""

    print("=== 草稿状态 ===")
    print("  status:", d.get("status"), "| type:", d.get("type"),
          "| article_id:", d.get("article_id"), "| title:", d.get("title"))
    print("  (status=2 且在草稿箱，未公开发布)")

    # 1) 数字序列
    src_body = strip_adapter(open(SRC_ART, encoding="utf-8").read().split("---", 2)[-1])
    want = NUM.findall(src_body)
    got = NUM.findall(md)
    print("\n=== 数字序列 ===")
    print(f"  真源 {len(want)} / 草稿 {len(got)} -> {'完全一致 ✓' if want == got else '不一致 ✗'}")
    if want != got:
        for i, (a, bb) in enumerate(zip(want, got)):
            if a != bb:
                print("   首个差异 #%d: src=%s csdn=%s" % (i + 1, a, bb)); break

    # 2) 文本（抹掉图片引用后）
    w_txt = strip_img(src_body).replace("\n", "").replace(" ", "")
    g_txt = strip_img(md).replace("\n", "").replace(" ", "")
    print("\n=== 正文文本（抹掉图片引用后）===")
    print(f"  真源 {len(w_txt)} 字 / 草稿 {len(g_txt)} 字 -> {'一致 ✓' if w_txt == g_txt else '不一致 ✗'}")
    if w_txt != g_txt:
        for i, (a, bb) in enumerate(zip(w_txt, g_txt)):
            if a != bb:
                print("   首个差异 @%d: src=...%s... csdn=...%s..." % (i, w_txt[max(0,i-40):i+40], g_txt[max(0,i-40):i+40]))
                break

    # 3) 图片
    refs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", md)
    print("\n=== 图片 ===")
    print("  markdown 引用:", len(refs), "| 占位图残留:",
          sum(1 for r in refs if "origin_url" in r or "20230724024159" in r))
    for r in refs:
        try:
            req = urllib.request.Request(r, method="GET", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            print(f"   HTTP {resp.status} {len(data):>7}B  {r[:95]}")
        except Exception as e:
            print(f"   ✗ 加载失败 {r[:95]}  ({e})")

    # 4) 编辑器里实际渲染
    pg.evaluate("() => { const b=[...document.querySelectorAll('.nav-tab-btn')].find(x=>x.innerText.trim()==='预览'); if(b) b.click(); }")
    pg.wait_for_timeout(9000)
    info = pg.evaluate("""() => {
        const imgs=[...document.querySelectorAll('.preview__inner-2 img')];
        return {n: imgs.length, loaded: imgs.filter(i=>i.naturalWidth>0).length,
                broken: imgs.filter(i=>i.complete && i.naturalWidth===0).map(i=>i.src.slice(0,110)),
                srcs: imgs.map(i=>i.src.slice(0,110))};
    }""")
    print("\n=== 预览面板渲染 ===")
    print("  img 总数:", info["n"], "| 已加载:", info["loaded"], "| 断链:", len(info["broken"]))
    for s in info["srcs"]:
        print("   ", s)

    pg.close()
    b.close()
