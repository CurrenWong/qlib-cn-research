"""把 projects/q3_2026/article.md 渲染成 article.html（720px，本地图片相对路径）。"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "docs" / "wechat"))

from wechat_html import md_to_html  # noqa: E402

md_text = (HERE / "article.md").read_text(encoding="utf-8")
imgs = re.findall(r"【插图\s*\d+：([^｜]+)｜图注：([^】]+)】", md_text)
print(f"插图 {len(imgs)} 张：")
for p, c in imgs:
    f = HERE / p.strip()
    print(f"  {p.strip():32s} {'✓' if f.exists() else '✗ 缺失'}  |  {c.strip()[:44]}")

body = md_to_html(md_text, [p.strip() for p, _ in imgs], local=True)

TITLE = "一份赚 2190 万，一份亏 11.41 亿——两份三季报翻到同一页"

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>两份三季报｜公众号预览</title>
<style>
  html, body {{ margin:0; padding:0; background:#EDEDED; }}
  .wrap {{ width:720px; box-sizing:border-box; margin:0 auto; background:#fff;
           padding:26px 30px 44px; overflow:hidden; }}
  .wrap * {{ box-sizing:border-box; }}
  .wrap h1.title {{ font-size:23px; line-height:1.5; font-weight:700; color:#1a1a1a;
                    margin:6px 0 20px; letter-spacing:.2px; }}
  .wrap img {{ max-width:100%; display:block; margin:22px auto 6px; border-radius:2px; }}
  .wrap p em {{ display:block; text-align:center; font-size:13px; color:#999; margin:-2px 0 22px; }}
  .wrap table {{ width:100%; border-collapse:collapse; font-size:13px; table-layout:fixed; }}
  .wrap th {{ background:#F5F5F5; font-weight:600; }}
  .wrap th, .wrap td {{ border:1px solid #E3E3E3; padding:7px 8px; text-align:center;
                         line-height:1.55; word-break:break-word; }}
  .wrap th:first-child, .wrap td:first-child {{ text-align:left; }}
  .wrap blockquote {{ margin:18px 0; padding:12px 14px; background:#F7F7F7;
                      border-left:3px solid #ddd; color:#555; font-size:14px; }}
  .wrap section {{ max-width:100%; }}
</style>
</head>
<body>
<div class="wrap">
<h1 class="title">{title}</h1>
{body}
</div>
</body>
</html>
"""

out = HERE / "article.html"
out.write_text(TPL.format(title=TITLE, body=body), encoding="utf-8")
print(f"\n已写入 {out}  ({out.stat().st_size / 1024:.0f} KB)")
