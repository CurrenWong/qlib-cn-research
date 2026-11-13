"""HTML → Markdown 转换（给公众号/一稿多发用）。

用 bs4 走结构化映射，不做正则硬啃：标题 / 段落 / 列表 / 表格 / 图片 / 引用块。
只处理 build_report.py 那套结构（h1-h3 / p / ul / table / img / div.lead|warn|bad|kv）。
"""

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup


def inline(node):
    """行内节点 → markdown 文本。"""
    out = []
    for child in node.children:
        if isinstance(child, str):
            out.append(child)
            continue
        name = child.name
        if name == "strong" or name == "b":
            out.append(f"**{inline(child).strip()}**")
        elif name == "em" or name == "i":
            out.append(f"*{inline(child).strip()}*")
        elif name == "code":
            out.append(f"`{child.get_text(strip=True)}`")
        elif name == "br":
            out.append("  \n")
        elif name in ("a", "span", "div", "small", "sup", "sub"):
            out.append(inline(child))
        else:
            out.append(inline(child))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def table_to_md(tbl):
    rows = []
    for tr in tbl.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        rows.append([inline(c) for c in cells])
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    head, body = rows[0], rows[1:]
    out = ["| " + " | ".join(head) + " |",
           "|" + "|".join(["---"] * ncol) + "|"]
    for r in body:
        out.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


def convert(html_path: Path) -> str:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    for bad in soup(["style", "script"]):
        bad.decompose()
    root = soup.select_one(".wrap") or soup.body or soup
    blocks = []
    for el in root.find_all(recursive=False):
        name = el.name
        cls = " ".join(el.get("class") or [])
        if name in ("h1", "h2", "h3", "h4"):
            blocks.append("#" * int(name[1]) + " " + inline(el))
        elif name == "p":
            t = inline(el)
            if t:
                blocks.append(t)
        elif name == "ul":
            items = [inline(li) for li in el.find_all("li", recursive=False)]
            blocks.append("\n".join(f"- {i}" for i in items if i))
        elif name == "ol":
            items = [inline(li) for li in el.find_all("li", recursive=False)]
            blocks.append("\n".join(f"{n}. {i}" for n, i in enumerate(items, 1) if i))
        elif name == "table":
            blocks.append(table_to_md(el))
        elif name == "img":
            src = el.get("src", "")
            alt = el.get("alt", "")
            blocks.append(f"![{alt}]({src})")
        elif name == "pre":
            code = el.get_text()
            blocks.append("```\n" + code.strip("\n") + "\n```")
        elif name == "blockquote":
            t = inline(el)
            if t:
                blocks.append("> " + t)
        elif name == "div":
            if "lead" in cls:
                items = [inline(li) for li in el.find_all("li")]
                if not items:
                    items = [inline(el)] if inline(el) else []
                blocks.append("> " + "\n> ".join(items))
            elif cls in ("warn", "bad"):
                mark = "⚠️" if cls == "warn" else "⛔"
                items = [inline(p) for p in el.find_all(["p", "li"])]
                items = [i for i in items if i]
                body = "\n".join(items) if items else inline(el)
                blocks.append(f"> {mark} " + body.replace("\n", "\n> "))
            elif "kpi" in cls:
                for d in el.find_all("div", recursive=False):
                    b = d.find("b")
                    s = d.find("span")
                    blocks.append(f"- **{inline(b) if b else ''}**"
                                  f"{' ' + inline(s) if s else ''}")
            elif "grid" in cls:
                for d in el.find_all("div", recursive=False):
                    t = inline(d)
                    if t:
                        blocks.append(t)
            else:
                t = inline(el)
                if t:
                    blocks.append(t)
        elif name in ("div", "section"):
            t = inline(el)
            if t:
                blocks.append(t)
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if out and out[-1] and out[-1][-1] != "\n" and not out[-1].endswith("|"):
            out.append("")
        out.append(b)
    return "\n\n".join(out)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"D:\Project\qlib\projects\csi300_lgbm\report\report.html")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".md")
    md = convert(src)
    dst.write_text(md, encoding="utf-8")
    print(f"已写出 {dst}  {len(md)} 字符 / {md.count(chr(10))+1} 行")


if __name__ == "__main__":
    main()
