"""本地预览：article.md → preview.html（沿用报告版式）→ 交给 render_png.py 截图。"""

import re
from pathlib import Path

import markdown

POST = Path(r"D:\Project\qlib\projects\csi300_lgbm\docs\post")
md_text = (POST / "article.md").read_text(encoding="utf-8")

body = re.sub(r"(?s)^---\n.*?\n---\n", "", md_text).strip()
body = re.sub(r"(?m)^# (.+)$", r"\1\n\n<div class='sub'>数据截至 2026-10-30 · 沪深300 时点成分股 · 训练 2016-2019 / 验证 2020-2022 / 测试 2023-2026 · qlib + LightGBM</div>\n\n", body, count=1)

html_body = markdown.markdown(
    body, extensions=["tables", "fenced_code", "sane_lists", "md_in_html"])

CSS = """
* { box-sizing: border-box; }
body { margin:0; background:#fff; color:#1F2933;
  font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;
  font-size:14px; line-height:1.8; }
.wrap { max-width:1180px; margin:0 auto; padding:38px 34px 56px; }
h1 { font-size:26px; margin:0 0 6px; letter-spacing:-.3px; }
.sub { color:#8A9099; font-size:12.5px; margin-bottom:24px; }
h2 { font-size:18.5px; margin:34px 0 10px; padding-left:11px;
  border-left:4px solid #E8833A; line-height:1.35; }
h3 { font-size:14.5px; margin:22px 0 8px; color:#2F7E8C; }
p { margin:9px 0; }
blockquote { background:#F7F8FA; border-left:4px solid #E8833A; margin:16px 0;
  padding:13px 18px; border-radius:6px; color:#39424E; }
blockquote p { margin:5px 0; }
table { border-collapse:collapse; width:100%; margin:14px 0 6px; font-size:12.4px; }
th { background:#F2F4F6; color:#5B6470; font-weight:600; text-align:right;
  padding:8px 9px; border-bottom:1px solid #E4E7EB; }
td { padding:7px 9px; border-bottom:1px solid #F0F2F4; text-align:right; }
td:first-child, th:first-child { text-align:left; }
img { max-width:100%; margin:12px 0 4px; display:block; }
code { background:#F2F4F6; padding:1.5px 6px; border-radius:4px; font-size:12px;
  font-family:Consolas,monospace; }
pre { background:#1F2933; color:#E8ECEF; padding:14px 16px; border-radius:8px;
  overflow-x:auto; font-size:12px; line-height:1.6; }
pre code { background:none; color:inherit; padding:0; }
ul { padding-left:22px; } li { margin:6px 0; }
"""

out = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>预览 · 沪深300 × LightGBM 选股复盘</title><style>{CSS}</style></head>
<body><div class="wrap">
{html_body}
</div></body></html>
"""
(POST / "preview.html").write_text(out, encoding="utf-8")
print("已写出", POST / "preview.html", len(out), "字节")
