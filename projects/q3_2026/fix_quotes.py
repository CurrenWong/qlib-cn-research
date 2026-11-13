# -*- coding: utf-8 -*-
"""把正文里的直引号成对替换成中文引号（只处理成对的短引号段）。"""
import re

P = r"D:\Project\qlib\projects\q3_2026\article.md"
t = open(P, encoding="utf-8").read()

before = t.count('"')
# 成对替换：不跨越换行、长度受限，避免误伤
for _ in range(60):
    t2 = re.sub(r'"([^"\n]{1,60})"', r"“\1”", t)
    if t2 == t:
        break
    t = t2

open(P, "w", encoding="utf-8").write(t)
print("直引号:", before, "->", t.count('"'))
print("中文引号对:", t.count("“"), t.count("”"))
left = [l for l in t.splitlines() if l.count('"') % 2]
print("仍有奇数个直引号的行:", len(left))
for l in left[:5]:
    print("   ", l[:90])
