"""把加粗里的句末标点挪到加粗外面（坑 16：某些平台的 Markdown 解析器会把整段吃成星号）。

只移动标点字符，不增删任何字；改完比对全文数字序列必须完全一致。
"""
import re
import sys
from pathlib import Path

p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"projects\style_post\article.md")
text = p.read_text(encoding="utf-8")

num_re = re.compile(r"[-+]?\d+(?:\.\d+)?")
before = num_re.findall(text)

pat = re.compile(r"\*\*(.+?)([。，；！？：])\*\*")
matches = pat.findall(text)
new = pat.sub(lambda m: f"**{m.group(1)}**{m.group(2)}", text)

after = num_re.findall(new)
print(f"加粗句末标点外移 {len(matches)} 处")
print(f"数字序列 {len(before)} 个，改前改后{'一致 ✅' if before == after else '不一致 ❌'}")
if before != after:
    sys.exit("数字变了，回滚")

# 检查是否还有跨行加粗（** 出现在行尾、下一行行首）
cross = [ln for i, ln in enumerate(new.splitlines())
         if ln.rstrip().endswith("**") and i + 1 < len(new.splitlines())
         and new.splitlines()[i + 1].lstrip().startswith("**")]
print(f"跨行加粗 {len(cross)} 处" + ("：" + str(cross[:3]) if cross else " ✅"))

p.write_text(new, encoding="utf-8")
print("已写入", p)
