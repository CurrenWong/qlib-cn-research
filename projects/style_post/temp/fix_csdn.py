"""修复 CSDN 草稿 171141543 的 2 张断链图。

背景：publish 时这 2 张图上传失败（Unexpected end of JSON input），
      CSDN 编辑器拿到相对路径 img/xxx.png，调 external/storage 报「非正常图片地址」，
      渲染成占位图 https://img-home.csdnimg.cn/images/20230724024159.png?origin_url=...

做法（不重跑 publish、不新建草稿）：
  1. 用编辑器自带的 file input 把 2 张本地 PNG 传上 CSDN 图床 -> 拿真实 URL
  2. 下载回传，和本地文件逐字节比对，确认没传错图
  3. 在编辑器源码 DOM 里把 2 个占位 <img> 的 src 换成真实 URL
  4. 点编辑器的保存按钮（存草稿，不发布）
  5. 重新加载页面 + 抓 getArticle 响应，读回核对：8 张图全是 csdnimg URL、数字序列不变

每步都有回读校验；第 4 步之前不碰任何草稿状态。
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ART = "171141543"
SRC = Path(r"D:\Project\qlib\projects\style_post\src")
DIST = Path(r"D:\Project\qlib\projects\style_post\dist")
NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")

TARGETS = {
    "img/bias_percentile.png": SRC / "img" / "bias_percentile.png",
    "img/rotate.png": SRC / "img" / "rotate.png",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    urls = {}
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0]
        pg = ctx.new_page()

        uploads = []

        def on_resp(r):
            if "obs" in r.url and r.request.method == "POST":
                try:
                    uploads.append(json.loads(r.text()))
                except Exception:
                    pass

        pg.on("response", on_resp)
        pg.goto(f"https://editor.csdn.net/md?articleId={ART}",
                wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(9000)

        # ---------- 1. 传 2 张图 ----------
        for key, local in TARGETS.items():
            uploads.clear()
            pg.set_input_files("input.cfw-file-input", str(local))
            pg.wait_for_timeout(11000)
            got = None
            for u in uploads:
                if u.get("code") == 200 and u.get("data", {}).get("imageUrl"):
                    got = u["data"]["imageUrl"]
            if not got:
                print(f"!! {key} 上传失败")
                pg.close(); b.close(); return 1
            urls[key] = got
            print(f"[1] {key} -> {got}")
            # 确认没有往文档里插东西
            n_img = pg.evaluate("""() => document.querySelectorAll('PRE.editor__inner img').length""")
            print(f"    文档内 img 数（应仍为 8）: {n_img}")

        # ---------- 2. 回传校验 ----------
        import urllib.request
        for key, local in TARGETS.items():
            tmp = Path(r"D:\Project\qlib\projects\style_post\temp") / ("dl_" + local.name)
            urllib.request.urlretrieve(urls[key], tmp)
            same = sha(tmp) == sha(local)
            print(f"[2] {local.name}: 本地 {local.stat().st_size}B / 回传 {tmp.stat().st_size}B "
                  f"sha256 {'一致 ✓' if same else '不一致 ✗'}")
            if not same:
                pg.close(); b.close(); return 1
            tmp.unlink()

        # ---------- 3. 换 src ----------
        swapped = pg.evaluate("""(urls) => {
            const out = [];
            for (const [key, real] of Object.entries(urls)) {
                const bad = [...document.querySelectorAll('PRE.editor__inner img')]
                    .filter(i => i.src.includes('origin_url=' + encodeURIComponent(key))
                              || i.src.includes('origin_url=' + key));
                for (const img of bad) {
                    out.push({key, from: img.src, to: real});
                    img.src = real;
                    img.alt = '';
                    img.removeAttribute('data-pos_id');
                }
            }
            return out;
        }""", urls)
        print(f"[3] 替换 {len(swapped)} 个 <img>：")
        for s in swapped:
            print(f"    {s['key']}: {s['from'][:70]}... -> {s['to']}")

        # ---------- 4. 保存 ----------
        pg.wait_for_timeout(1500)
        btn_info = pg.evaluate("""() => {
            const b = document.querySelector('.button-save');
            return b ? {text: b.innerText.trim(), cls: b.className} : null;
        }""")
        print("[4] 保存按钮:", btn_info)
        save_resp = []
        pg.on("response", lambda r: save_resp.append((r.url, r.request.method))
              if "saveArticle" in r.url else None)
        pg.click(".button-save")
        pg.wait_for_timeout(12000)
        print("    保存相关请求:", save_resp)

        # ---------- 5. 读回核对 ----------
        getart = {}
        def on_get(r):
            if "getArticle" in r.url:
                try:
                    getart.update(json.loads(r.text()))
                except Exception:
                    pass
        pg.on("response", on_get)
        pg.reload(wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(12000)

        imgs = pg.evaluate("""() => [...document.querySelectorAll('PRE.editor__inner img')].map(i => i.src)""")
        print(f"\n[5] 读回：源码面板 {len(imgs)} 张图")
        bad = [i for i in imgs if "origin_url" in i]
        print("    占位图残留:", len(bad), bad)
        for i in imgs:
            print("    ", i[:110])

        if getart:
            data = getart.get("data") or {}
            md = data.get("markdown_content") or ""
            with open(DIST / "csdn" / "article.md", encoding="utf-8") as f:
                want = f.read()
            body = want.split("---", 2)[-1]
            want_nums = NUM.findall(body)
            got_nums = NUM.findall(md)
            print(f"\n    getArticle markdown 长度 {len(md)}")
            print(f"    数字序列 src {len(want_nums)} / csdn {len(got_nums)} -> "
                  f"{'一致 ✓' if want_nums == got_nums else '不一致 ✗'}")
            refs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", md)
            print(f"    图片引用 {len(refs)}:")
            for r in refs:
                print("      ", r[:110])
            with open(r"D:\Project\qlib\projects\style_post\temp\csdn_readback.md", "w",
                      encoding="utf-8") as f:
                f.write(md)
        else:
            print("!! 没抓到 getArticle 响应")

        pg.close()
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
