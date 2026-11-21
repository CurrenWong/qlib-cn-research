"""扫描加粗标记是否被 fix_bold 弄坏：
- 破坏特征：`**` 紧跟在数字/字母后面（本该是「加粗结束」）却出现在句子中间，
  典型坏例：`分位 95**，最热的一个**。`
- 另查：每行 `**` 个数必须是偶数
"""
import re
import sys
from pathlib import Path

files = sys.argv[1:] or [r"projects\style_post\article.md",
                          r"projects\style_post\src\article.md",
                          r"projects\style_post\dist\zhihu\article.md",
                          r"projects\style_post\dist\csdn\article.md",
                          r"projects\style_post\dist\juejin\article.md",
                          r"projects\style_post\dist\baijiahao\article.md",
                          r"projects\style_post\dist\bilibili\article.md"]

for f in files:
    p = Path(f)
    if not p.exists():
        continue
    txt = p.read_text(encoding="utf-8")
    print(f"== {f} ==")
    bad = 0
    for i, line in enumerate(txt.splitlines(), 1):
        n = line.count("**")
        if n % 2:
            print(f"   行{i} ** 个数为奇数({n}): {line[:110]}")
            bad += 1
        # 加粗结束符紧跟数字 → 数字被误吞进加粗
        for m in re.finditer(r"[0-9%）\)]\*\*[，、；：。！？]", line):
            print(f"   行{i} 疑似误吞: ...{line[max(0,m.start()-40):m.end()+30]}...")
            bad += 1
    print("   合计问题:", bad)
