import re, sys
p = sys.argv[1] if len(sys.argv) > 1 else r"D:\Project\qlib\projects\style_post\src\article.md"
t = open(p, encoding="utf-8").read()
for m in re.finditer(r"\*\*(.+?)\*\*", t, re.S):
    inner = m.group(1)
    hits = [c for c in "。？！" if c in inner]
    if hits:
        line = t[: m.start()].count("\n") + 1
        print("LINE", line, "HITS", hits, "CROSSLINE", "\n" in inner)
        print(repr(t[max(0, m.start() - 80): m.end() + 80]))
        print("---")
