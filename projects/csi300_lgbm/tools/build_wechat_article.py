"""把 article.md 转成微信公众号能用的 HTML（行内样式 + 图片占位符）。

微信正文只认行内样式：<style> 会被清掉，所以每个元素都要自带 style。
图片先写成 __IMG:文件名__ 占位，发布脚本上传后替换成 mmbiz URL。

输出：docs/post/wechat_article.html
"""

import re
from pathlib import Path

import markdown
from bs4 import BeautifulSoup

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

POST = Path(_ROOT + r"/projects/csi300_lgbm/docs/post")

P = ("margin:1.05em 0;font-size:16px;line-height:1.9;color:#2E2E33;"
     "letter-spacing:.3px;text-align:justify;")
H2 = ("margin:2.2em 0 .9em;padding-left:11px;border-left:4px solid #1F3BE0;"
      "font-size:19px;line-height:1.5;font-weight:700;color:#1A1A1E;")
H3 = ("margin:1.6em 0 .6em;font-size:16px;line-height:1.6;font-weight:700;color:#1F3BE0;")
LI = "margin:.55em 0;font-size:16px;line-height:1.85;color:#2E2E33;letter-spacing:.3px;"


def main():
    md_text = (POST / "article.md").read_text(encoding="utf-8")
    body = re.sub(r"(?s)^---\n.*?\n---\n", "", md_text).strip()

    # 导语那段（引用块）改成公众号喜欢的样式：保留引用块外观
    html = markdown.markdown(body, extensions=["tables", "fenced_code", "sane_lists"])
    soup = BeautifulSoup(html, "html.parser")

    for h1 in soup.find_all("h1"):
        h1["style"] = ("margin:0 0 14px;font-size:22px;line-height:1.5;"
                       "font-weight:700;color:#1A1A1E;")
    for h2 in soup.find_all("h2"):
        h2["style"] = H2
    for h3 in soup.find_all("h3"):
        h3["style"] = H3
    for p in soup.find_all("p"):
        p["style"] = P
    for ul in soup.find_all("ul"):
        ul["style"] = "margin:1.1em 0;padding-left:1.3em;list-style-type:disc;"
    for ol in soup.find_all("ol"):
        ol["style"] = "margin:1.1em 0;padding-left:1.4em;"
    for li in soup.find_all("li"):
        li["style"] = LI
        for p2 in li.find_all("p"):
            p2["style"] = LI
    for st in soup.find_all("strong"):
        st["style"] = "font-weight:700;color:#1A1A1E;"
    for bq in soup.find_all("blockquote"):
        bq["style"] = ("margin:1.2em 0;padding:2px 0 2px 14px;"
                        "border-left:3px solid #1F3BE0;color:#55575E;font-size:15px;"
                        "line-height:1.85;")
        for p3 in bq.find_all("p"):
            p3["style"] = ("margin:.6em 0;font-size:15px;line-height:1.85;color:#55575E;")
    for tbl in soup.find_all("table"):
        tbl["style"] = ("width:100%;border-collapse:collapse;margin:1.1em 0;"
                        "font-size:12.5px;line-height:1.6;")
    for th in soup.find_all("th"):
        th["style"] = ("background:#F3F1EA;border-bottom:2px solid #1F3BE0;"
                       "padding:8px 7px;text-align:left;color:#1A1A1E;font-weight:700;")
    for td in soup.find_all("td"):
        td["style"] = ("border-bottom:1px solid #E7E2D6;padding:7px;"
                        "text-align:left;color:#2E2E33;")
    for pre in soup.find_all("pre"):
        pre["style"] = ("background:#F5F3EE;border-radius:6px;padding:12px 14px;"
                        "overflow-x:auto;font-size:12px;line-height:1.6;color:#3A3A40;")
        for c in pre.find_all("code"):
            c["style"] = "font-family:Menlo,Consolas,monospace;font-size:12px;"
    for c in soup.find_all("code"):
        if c.parent and c.parent.name == "pre":
            continue
        c["style"] = ("background:#F3F1EA;padding:1px 5px;border-radius:3px;"
                      "font-family:Menlo,Consolas,monospace;font-size:13px;color:#1F3BE0;")
    for img in soup.find_all("img"):
        name = img.get("src", "").split("/")[-1]
        img["src"] = f"__IMG:{name}__"
        img["data-src"] = f"__IMG:{name}__"
        img["style"] = ("display:block;max-width:100%;margin:12px auto;"
                        "border-radius:4px;")

    out = "<section style=\"margin:0 0 26px;\">" + str(soup) + "</section>"
    (POST / "wechat_article.html").write_text(out, encoding="utf-8")
    n_img = out.count("__IMG:")
    print(f"已写出 {POST / 'wechat_article.html'}  {len(out)} 字节 / 图片占位 {n_img} 处")


if __name__ == "__main__":
    main()
