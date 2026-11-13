import pathlib

p = pathlib.Path(r"C:\Users\curre\.copaw\workspaces\J6c4mu\dist\csi300_lgbm\csdn\article.md")
s = p.read_text(encoding="utf-8")
n = s.count("cover.png")
s = s.replace("![](cover.png)\n\n", "").replace("![](cover.png)\n", "").replace("![](cover.png)", "")
p.write_text(s, encoding="utf-8")
c = p.parent / "cover.png"
print("去掉 cover 引用", n, "处；剩余", s.count("cover.png"))
print("cover.png 是否还在目录:", c.exists())
