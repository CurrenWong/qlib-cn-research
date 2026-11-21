"""核对五平台产物与真源的一致性：数字序列、可见文本、段落完整性。

规则（用户硬约束）：
  · 正文数字序列必须与 src/article.md 完全一致（正则 [-+]?\\d+(\\.\\d+)?）
  · 除加粗标点外，正文一个字符都不能改
  · 适配器允许改结构：开篇导语 / 文末版权块 / CSDN 首图插入 → 这些要在比对时剥掉
"""
import re
import sys
from pathlib import Path

SRC = Path(r"D:\Project\qlib\projects\style_post\src\article.md")
DIST = Path(r"D:\Project\qlib\projects\style_post\dist")
PLATS = ["zhihu", "csdn", "juejin", "baijiahao", "bilibili"]
NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def split_fm(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    return (m.group(2) if m else text).strip()


def strip_adapter(body, lead_text, cover_name):
    """剥掉适配器加的结构：开篇导语、CSDN 首图、文末版权块。"""
    b = body
    # 开篇导语（> 开头的一行）
    if lead_text:
        lead = "> " + lead_text.strip()
        if b.startswith(lead):
            b = b[len(lead):].lstrip("\n")
    # CSDN 自动插的封面首图
    b = re.sub(r"^!\[\]\(" + re.escape(cover_name) + r"\)\n+", "", b)
    # 文末版权块：最后一个 "\n---\n\n" 之后的内容
    idx = b.rfind("\n---\n\n")
    if idx != -1:
        b = b[:idx]
    return b.strip()


def visible(text):
    """去掉加粗/斜体标记后的可见文本（加粗标点外移不改变可见文本）。"""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.S)
    return re.sub(r"\s+", "", t)


def main():
    src_text = SRC.read_text(encoding="utf-8")
    src_body = split_fm(src_text)
    src_nums = NUM.findall(src_body)
    src_vis = visible(src_body)
    src_paras = [p.strip() for p in src_body.split("\n\n") if p.strip()]

    # 导语（各平台不同，从 front matter 取）
    lead = {}
    fm = src_text.split("---", 2)[1]
    for m in re.finditer(r"^\s{2}(\w+):\s*\"(.*)\"$", fm, re.M):
        if m.group(1) not in ("title", "summary", "category", "cover", "footer_note"):
            lead[m.group(1)] = m.group(2)

    print(f"真源正文：{len(src_nums)} 个数字，{len(src_paras)} 个实质段落")
    print()

    all_ok = True
    for p in PLATS:
        d = DIST / p
        art = (d / "article.md").read_text(encoding="utf-8")
        body = split_fm(art)
        stripped = strip_adapter(body, lead.get(p, ""), "cover.png")

        nums = NUM.findall(stripped)
        vis = visible(stripped)
        nums_ok = nums == src_nums
        vis_ok = vis == src_vis

        # 段落完整性：真源每个段落都要在平台正文里出现
        missing = [i for i, para in enumerate(src_paras) if visible(para) not in vis]

        # 数字位置差异明细
        diff = []
        if not nums_ok:
            for i, (a, b) in enumerate(zip(src_nums, nums)):
                if a != b:
                    diff.append(f"#{i+1} src={a} plat={b}")
                    if len(diff) >= 10:
                        break
            if len(src_nums) != len(nums):
                diff.append(f"数量不同 src={len(src_nums)} plat={len(nums)}")

        print(f"== {p} ==")
        print(f"   数字序列: {'✓ 完全一致' if nums_ok else '✗ 不一致 ' + str(diff)}"
              f"  (src {len(src_nums)} / plat {len(nums)})")
        print(f"   可见文本: {'✓ 完全一致' if vis_ok else '✗ 不一致'}")
        print(f"   缺段: {len(missing)} {missing if missing else ''}")
        if not (nums_ok and vis_ok and not missing):
            all_ok = False
        print()

    print("✓ 全部一致" if all_ok else "✗ 存在差异")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
