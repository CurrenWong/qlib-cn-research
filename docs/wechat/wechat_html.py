"""把 article.md 转成微信公众号可用的「全内联样式」正文 HTML。

- 插图标记 【插图 N：img/xxx.png｜图注：…】 → 居中图片 + 居中灰色图注
- 表格保留真 <table>，外层包 overflow-x:auto 的 section，列宽自适应
- h2 用左侧橙色竖线；bash 代码块保留等宽 + pre-wrap
- 不改写任何正文文字
"""
import re

import markdown
from bs4 import BeautifulSoup

BODY_FONT = ("-apple-system,BlinkMacSystemFont,'PingFang SC',"
             "'Microsoft YaHei',sans-serif")
C_ORANGE = "#E67E22"

MARKER = re.compile(r"【插图\s*\d+：([^｜]+)｜图注：([^】]+)】")


def md_to_html(md_text, img_srcs, local=False):
    """img_srcs: 按出现顺序的图片地址列表（长度须与标记数一致）。

    local=True 时写 src（本地预览可显示）；否则写 data-src（微信 API 约定）。
    """
    caps = []

    def repl(m):
        i = len(caps)
        caps.append((m.group(1).strip(), m.group(2).strip()))
        return f"\n\n@@IMG_{i}@@\n\n"

    md_text = MARKER.sub(repl, md_text)
    raw = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    soup = BeautifulSoup(raw, "lxml")
    return _style(soup, caps, img_srcs, local)


def _style(soup, caps, img_srcs, local=False):
    # ---- 段落 ----
    for p in soup.find_all("p"):
        p["style"] = "margin:15px 0;font-size:16px;line-height:1.85;color:#2c2c2c;"

    # ---- 标题 ----
    for h1 in soup.find_all("h1"):
        h1["style"] = ("margin:0 0 18px;font-size:22px;line-height:1.45;"
                       "font-weight:700;color:#111;letter-spacing:.3px;")
    for h2 in soup.find_all("h2"):
        txt = h2.get_text()
        wrap = soup.new_tag("section")
        wrap["style"] = (f"border-left:4px solid {C_ORANGE};padding-left:11px;"
                         "margin:40px 0 18px;")
        head = soup.new_tag("span")
        head["style"] = ("font-size:19px;font-weight:700;color:#1a1a1a;"
                         "line-height:1.45;")
        head.string = txt
        wrap.append(head)
        h2.replace_with(wrap)
    for h3 in soup.find_all("h3"):
        h3["style"] = ("margin:28px 0 12px;font-size:17px;font-weight:700;"
                       "color:#1a1a1a;line-height:1.5;")

    # ---- 引用 ----
    for bq in soup.find_all("blockquote"):
        bq["style"] = ("margin:20px 0;padding:12px 16px;background:#F7F7F7;"
                       "border-left:3px solid #ddd;color:#555;font-size:15px;"
                       "line-height:1.8;")
        for p in bq.find_all("p"):
            p["style"] = "margin:4px 0;font-size:15px;line-height:1.8;color:#555;"

    # ---- 列表 ----
    for ul in soup.find_all(["ul", "ol"]):
        ul["style"] = "margin:15px 0;padding-left:24px;font-size:16px;line-height:1.85;color:#2c2c2c;"
    for li in soup.find_all("li"):
        li["style"] = "margin:8px 0;font-size:16px;line-height:1.85;color:#2c2c2c;"
        for p in li.find_all("p"):
            p["style"] = "margin:4px 0;font-size:16px;line-height:1.85;color:#2c2c2c;"

    # ---- 分隔线 → • • • ----
    for hr in soup.find_all("hr"):
        p = soup.new_tag("p")
        p["style"] = ("margin:32px 0;text-align:center;color:#D8D8D8;"
                      "letter-spacing:8px;font-size:14px;")
        p.string = "• • •"
        hr.replace_with(p)

    # ---- 强调 ----
    for s in soup.find_all("strong"):
        s["style"] = "font-weight:700;color:#000;"
    for em in soup.find_all("em"):
        em["style"] = "font-style:italic;color:#555;"

    # ---- 行内 code（先处理，后面 pre code 覆盖） ----
    for c in soup.find_all("code"):
        c["style"] = ("font-family:Consolas,Monaco,'Courier New',monospace;"
                      "background:#F5F5F5;padding:1px 4px;border-radius:2px;"
                      "font-size:14px;color:#333;")

    # ---- 代码块 ----
    for pre in soup.find_all("pre"):
        pre["style"] = ("margin:0;padding:0;background:transparent;"
                        "font-family:Consolas,Monaco,'Courier New',monospace;"
                        "font-size:13px;line-height:1.8;white-space:pre-wrap;"
                        "word-break:break-all;color:#333;")
        box = soup.new_tag("section")
        box["style"] = ("margin:20px 0;padding:14px 16px;background:#FAFAFA;"
                        "border:1px solid #EEE;border-radius:4px;"
                        "overflow-x:auto;")
        pre.replace_with(box)
        box.append(pre)
        for c in box.find_all("code"):
            c["style"] = ("font-family:Consolas,Monaco,'Courier New',monospace;"
                          "background:transparent;padding:0;font-size:13px;"
                          "line-height:1.8;color:#333;white-space:pre-wrap;")

    # ---- 表格 ----
    for tb in soup.find_all("table"):
        tb["style"] = ("width:100%;border-collapse:collapse;font-size:14px;"
                       "table-layout:auto;margin:0;")
        for th in tb.find_all("th"):
            th["style"] = ("border:1px solid #E3E3E3;padding:8px 10px;"
                           "background:#F5F5F5;font-weight:600;font-size:14px;"
                           "text-align:center;line-height:1.6;color:#222;")
        for td in tb.find_all("td"):
            td["style"] = ("border:1px solid #E3E3E3;padding:8px 10px;"
                           "font-size:14px;text-align:center;line-height:1.6;"
                           "color:#2c2c2c;")
        # 第一列左对齐
        for tr in tb.find_all("tr"):
            cells = tr.find_all(["th", "td"], recursive=False)
            if cells:
                cells[0]["style"] = cells[0]["style"].replace(
                    "text-align:center;", "text-align:left;")
        wrap = soup.new_tag("section")
        wrap["style"] = "margin:20px 0;overflow-x:auto;"
        tb.replace_with(wrap)
        wrap.append(tb)

    # ---- 插图占位 ----
    for i, (path, cap) in enumerate(caps):
        for p in soup.find_all("p"):
            if p.get_text().strip() == f"@@IMG_{i}@@":
                frag = BeautifulSoup(
                    '<p style="margin:22px 0 6px;text-align:center;">'
                    f'<img {"src" if local else "data-src"}="{img_srcs[i]}" '
                    'style="max-width:100%;display:block;margin:0 auto;'
                    'border-radius:2px;" /></p>'
                    f'<p style="margin:6px 0 24px;text-align:center;font-size:13px;'
                    f'color:#999;line-height:1.6;">{cap}</p>',
                    "lxml")
                nodes = list(frag.body.children)
                for n in nodes:
                    p.insert_before(n)
                p.decompose()
                break

    body = soup.body or soup
    inner = "".join(str(c) for c in body.children)
    return (f'<section style="font-size:16px;line-height:1.85;color:#2c2c2c;'
            f'font-family:{BODY_FONT};">{inner}</section>')
