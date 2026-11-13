"""本地构建 + 结构体检（不上传、不建草稿）。"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wechat_html import md_to_html, MARKER

HERE = Path(__file__).resolve().parent
md = (HERE / "article.md").read_text(encoding="utf-8")

imgs = [m.group(1).strip() for m in MARKER.finditer(md)]
print("插图标记顺序:", imgs)
html = md_to_html(md, [(HERE / p).resolve().as_uri() for p in imgs], local=True)

out = HERE / "wechat_content_local.html"
out.write_text(
    "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
    "<title>wechat body preview</title></head>"
    "<body style='max-width:677px;margin:0 auto;padding:24px 18px;"
    "background:#fff;'>" + html + "</body></html>", encoding="utf-8")

text = re.sub(r"<[^>]+>", "", html)
print(f"写出 {out}")
print(f"  <img> {html.count('<img')} | <table> {html.count('<table')} | "
      f"h2-section {html.count('border-left:4px solid #E67E22')} | "
      f"<pre> {html.count('<pre')} | 正文 {len(text)} 字")
print("  残留标记:", "@@IMG" in html, "| data-src 数:", html.count("data-src"))
unstyled = html.count('style="') 
print("  style 属性数:", unstyled)
for tag in ["<p>", "<table>", "<td>", "<pre>", "<h2>", "<ul>", "<li>"]:
    n = html.count(tag)
    if n:
        print(f"  ⚠ 无内联样式 {tag} x{n}")
