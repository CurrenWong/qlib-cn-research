"""生成多平台分发的「真根源」：article.md（公众号版，带【插图】标记）
   → src/article.md（带 front matter，图改成标准 markdown 图片语法）

为什么要生成而不是手抄两份：
公众号版用【插图 N：img/x.png｜图注：…】标记（wechat_html.py 靠它做 CDN 上传 + 图注居中），
多平台版要标准 markdown 图片（adapt.py 会按相对路径自动拷图）。
一个脚本单向生成 → 正文只有一份真源，改完重跑即可，不会走样。

用法：..\\..\\.venv\\Scripts\\python.exe make_source.py
输出：src/article.md、src/img/*
"""

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
MARKER = re.compile(r"【插图\s*\d+：([^｜]+)｜图注：([^】]+)】")


def main():
    import yaml

    fm = yaml.safe_load((HERE / "front_matter.yaml").read_text(encoding="utf-8")) or {}
    body = (HERE / "article.md").read_text(encoding="utf-8")

    imgs = []

    def repl(m):
        path, cap = m.group(1).strip(), m.group(2).strip()
        imgs.append(path)
        return f"\n![{cap}]({path})\n"

    body = MARKER.sub(repl, body).strip()

    # 去掉开头的 H1：标题在 front matter 里（CLI 只认 front matter 的 title），
    # 正文再留一个 # 标题会在平台侧重复显示
    body = re.sub(r"\A#\s+.*?\n", "", body).lstrip()

    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for kk, vv in v.items():
                lines.append(f'  {kk}: "{vv}"')
        else:
            lines.append(f'{k}: "{v}"')
    lines += ["---", ""]

    SRC.mkdir(exist_ok=True)
    (SRC / "img").mkdir(exist_ok=True)
    (SRC / "article.md").write_text("\n".join(lines) + body + "\n", encoding="utf-8")

    # 图片按相对路径拷进 src/img/（adapt.py 按 article.md 所在目录找图）
    for rel in imgs:
        s = HERE / rel
        d = SRC / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)

    print(f"front matter 字段: {list(fm.keys())}")
    print(f"正文 {len(body)} 字，图 {len(imgs)} 张")
    print(f"已生成 {SRC / 'article.md'}")
    print(f"已拷图 {len(imgs)} 张 -> {SRC / 'img'}")
    for rel in imgs:
        print(f"   {rel}  {(SRC / rel).stat().st_size // 1024}KB")


if __name__ == "__main__":
    main()
