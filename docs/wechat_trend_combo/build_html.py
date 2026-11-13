"""把 article.md 渲染成两个 HTML：

  article.html      本地预览（414px 手机宽度、内联样式、图片相对路径）→ 用 headless Chrome 截 PNG
  wechat_body.html  公众号可用的「全内联样式」正文（data-src 形式，符合微信 API 约定）

复用 ../wechat/wechat_html.py 的样式逻辑。
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "wechat"))

from wechat_html import md_to_html  # noqa: E402

md_text = (HERE / "article.md").read_text(encoding="utf-8")

# 收集插图路径（按出现顺序）
imgs = re.findall(r"【插图\s*\d+：([^｜]+)｜图注：([^】]+)】", md_text)
print(f"插图 {len(imgs)} 张：")
for p, c in imgs:
    print(f"  {p.strip()}  |  {c.strip()[:40]}")

body_local = md_to_html(md_text, [p.strip() for p, _ in imgs], local=True)
body_wechat = md_to_html(md_text, [p.strip() for p, _ in imgs], local=False)

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>新闻归因实验｜公众号预览</title>
<style>
  html, body {{ margin:0; padding:0; background:#EDEDED; }}
  .wrap {{ width:720px; box-sizing:border-box; margin:0 auto; background:#fff;
           padding:26px 30px 44px; overflow:hidden; }}
  .wrap * {{ box-sizing:border-box; }}
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
{body}
</div>
</body>
</html>
"""

out = HERE / "article.html"
out.write_text(TPL.format(body=body_local), encoding="utf-8")
(HERE / "wechat_body.html").write_text(body_wechat, encoding="utf-8")
print(f"\n已写入 {out}")
print(f"已写入 {HERE / 'wechat_body.html'}")
