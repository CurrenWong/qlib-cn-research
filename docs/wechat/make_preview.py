"""把 article.md 渲染成公众号风格的本地预览（图片用相对路径，双击即可看）。

用法：.venv\\Scripts\\python.exe docs\\wechat\\make_preview.py
输出：docs/wechat/preview.html
"""

import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
md_text = (HERE / "article.md").read_text(encoding="utf-8")

# 【插图 N：img/xxx.png｜图注：...】 → 真正的 HTML 图片块
md_text = re.sub(
    r"【插图\s*\d+：([^｜]+)｜图注：([^】]+)】",
    lambda m: f"\n![{m.group(2)}]({m.group(1).strip()})\n",
    md_text,
)

html_body = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "toc"],
)

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>公众号预览</title>
<style>
  body {{
    max-width: 677px; margin: 0 auto; padding: 32px 22px 80px;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                 "Microsoft YaHei", sans-serif;
    font-size: 16px; line-height: 1.85; color: #2c2c2c;
    background: #fff;
  }}
  h1 {{ font-size: 24px; line-height: 1.45; margin: 0 0 18px; letter-spacing: .3px; }}
  h2 {{
    font-size: 19px; margin: 40px 0 16px; padding-left: 11px;
    border-left: 4px solid #E67E22; line-height: 1.4;
  }}
  h3 {{ font-size: 17px; margin: 28px 0 12px; color: #1a1a1a; }}
  p {{ margin: 15px 0; }}
  strong {{ color: #000; }}
  blockquote {{
    margin: 20px 0; padding: 12px 16px; background: #F7F7F7;
    border-left: 3px solid #ddd; color: #555; font-size: 15px;
  }}
  blockquote p {{ margin: 4px 0; }}
  img {{
    max-width: 100%; display: block; margin: 22px auto 6px;
    border-radius: 2px;
  }}
  img + p em, p em {{
    display: block; text-align: center; font-size: 13px; color: #999;
    margin: -2px 0 22px; font-style: normal;
  }}
  table {{
    width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;
  }}
  th {{ background: #F5F5F5; font-weight: 600; }}
  th, td {{ border: 1px solid #E3E3E3; padding: 8px 10px; text-align: center; }}
  td:first-child, th:first-child {{ text-align: left; }}
  pre {{
    background: #FAFAFA; border: 1px solid #EEE; border-radius: 4px;
    padding: 14px; overflow-x: auto; font-size: 13px; line-height: 1.6;
  }}
  code {{ font-family: Consolas, Monaco, monospace; background: #F5F5F5;
          padding: 1px 4px; border-radius: 2px; font-size: 14px; }}
  pre code {{ background: none; padding: 0; }}
  hr {{ border: none; border-top: 1px solid #EAEAEA; margin: 36px 0; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""

out = HERE / "preview.html"
out.write_text(TPL.format(body=html_body), encoding="utf-8")

n_img = html_body.count("<img")
n_tab = html_body.count("<table")
n_h2 = html_body.count("<h2")
n_code = html_body.count("<pre")
print(f"已写入 {out}")
print(f"  图片 {n_img} 张 | 表格 {n_tab} 个 | h2 {n_h2} 个 | 代码块 {n_code} 个")
print(f"  正文字数（去标签）约 {len(re.sub(r'<[^>]+>', '', html_body))} 字")
