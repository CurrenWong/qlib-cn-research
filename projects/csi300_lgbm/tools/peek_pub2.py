import pathlib
import re

d = pathlib.Path(r"C:\Users\curre\.copaw\workspaces\J6c4mu\dist\csi300_lgbm\logs")


def read_any(p):
    raw = p.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


for f in sorted(d.glob("pub*.log")):
    s = read_any(f)
    ok = len(re.findall(r"✓ 上传", s))
    bad = re.findall(r"✗ 失败: (\S+)", s)
    links = re.findall(r"(https?://\S+)", s)
    print("==", f.name, "| 上传成功", ok, "| 失败", bad)
    for ln in links:
        print("   链接:", ln)
    for ln in s.splitlines():
        if "同步完成" in ln or "失败" in ln or "草稿" in ln:
            print("   ", ln.strip()[:120])
