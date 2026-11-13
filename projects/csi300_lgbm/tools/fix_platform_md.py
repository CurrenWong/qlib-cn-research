"""发布前的平台定向修补（作用于 adapt 产出的 dist/<平台>/article.md）。

依据是上一轮实发的回读结果：

- CSDN / B站：markdown 编辑器里 `**` 被转义成 \\*\\*，正文会出现字面星号 → 去掉加粗标记，保留文字
- 百家号：富文本转换器不认引用块，`> ` 会原样出现在正文里 → 引用块降级成普通段落
- 知乎（HTML）/ 掘金：渲染正常，不动

用法：python fix_platform_md.py <dist 目录>
"""

import re
import sys
from pathlib import Path

dist = Path(sys.argv[1] if len(sys.argv) > 1 else
            r"C:\Users\curre\.copaw\workspaces\J6c4mu\dist\csi300_lgbm")

STRIP_BOLD = ["csdn", "bilibili"]
DROP_QUOTE = ["baijiahao"]


def strip_bold(text: str) -> str:
    return text.replace("**", "")


def dequote(text: str) -> str:
    out = []
    for line in text.splitlines():
        if line.startswith("> "):
            out.append(line[2:])
        elif line.strip() == ">":
            out.append("")
        else:
            out.append(line)
    # 引用块拆开后可能留下连续空行，压掉两行以上的
    txt = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", txt)


def main():
    for plat in dist.iterdir():
        if not plat.is_dir():
            continue
        f = plat / "article.md"
        if not f.exists():
            continue
        src = f.read_text(encoding="utf-8")
        txt = src
        changed = []
        if plat.name in STRIP_BOLD:
            txt = strip_bold(txt)
            changed.append("去粗体标记")
        if plat.name in DROP_QUOTE:
            txt = dequote(txt)
            changed.append("引用块降级")
        if txt != src:
            f.write_text(txt, encoding="utf-8")
            print(f"  {plat.name}: {'、'.join(changed)}  ({len(src)} → {len(txt)})")
        else:
            print(f"  {plat.name}: 无需处理")


if __name__ == "__main__":
    main()
