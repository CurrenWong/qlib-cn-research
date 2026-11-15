import pathlib
import re

d = pathlib.Path(r"<multi-platform-dist>\dist\csi300_lgbm\logs")


def read_any(p):
    raw = p.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


rows = []
for f in sorted(d.glob("pub*.log")):
    s = read_any(f)
    ok = len(re.findall(r"✓ 上传", s))
    bad = re.findall(r"✗ 失败: (\S+)", s)
    m = re.search(r"articleId=(\d+)", s)
    rows.append((f.name, ok, len(bad), m.group(1) if m else None, bad))

for r in rows:
    print(f"{r[0]:22s} 上传 {r[1]:2d}/失败 {r[2]}  articleId={r[3]}  {r[4]}")
