"""解压 qlib 数据集到目标目录。"""

import sys
import zipfile
from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

src = Path(_ROOT + r"/data/qlib_data_cn_1d_latest.zip")
dst = Path(_ROOT + r"/qlib_data/cn_data")
dst.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(src) as zp:
    names = zp.namelist()
    print(f"entries={len(names)} first={names[:3]}")
    zp.extractall(dst)

print("extracted ->", dst)
for p in sorted(dst.iterdir()):
    if p.is_dir():
        print(f"  [dir] {p.name:20s} {len(list(p.rglob('*')))} entries")
    else:
        print(f"  [file] {p.name} {p.stat().st_size} bytes")
sys.exit(0)
