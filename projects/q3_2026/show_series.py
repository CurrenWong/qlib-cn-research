import json

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

d = json.load(open(_ROOT + r"/projects/q3_2026/data.json", encoding="utf-8"))
for code in ("SH600418", "SZ002230"):
    print("==", code)
    for dt, v in d["series"][code]:
        print("  ", dt, v)
