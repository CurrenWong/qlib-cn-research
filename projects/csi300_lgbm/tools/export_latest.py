"""导出"最新成分股"（csi300.txt 里 end >= 2026-10-27 的 300 只），供数据更新脚本使用。"""

from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

DATA = Path(_ROOT + r"/qlib_data/cn_data_2026")
OUT = Path(_ROOT + r"/projects/csi300_lgbm/data/csi300_latest.txt")

mem = {}
for line in (DATA / "instruments" / "csi300.txt").read_text(encoding="utf-8").splitlines():
    p = line.split("\t")
    if len(p) == 3:
        mem.setdefault(p[0], []).append((p[1], p[2]))

latest = sorted({s for s, v in mem.items() if any(b >= "2026-10-27" for a, b in v)})
OUT.write_text("\n".join(latest) + "\n", encoding="utf-8")
print(f"{len(latest)} 只 -> {OUT}")
print(",".join(latest[:5]), "…", ",".join(latest[-3:]))
