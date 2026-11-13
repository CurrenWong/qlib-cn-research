import json
from pathlib import Path

p = Path(r"C:\Users\curre\.copaw\workspaces\J6c4mu\dist\csi300_lgbm\logs\verify.json")
d = json.loads(p.read_text(encoding="utf-8"))
for k, v in d.items():
    print("=====", k, type(v).__name__, (list(v)[:12] if isinstance(v, dict) else ""))
    if isinstance(v, dict):
        for kk, vv in list(v.items())[:4]:
            if isinstance(vv, str):
                print(f"   {kk}: {vv[:300]!r}")
            elif isinstance(vv, dict):
                print(f"   {kk}: dict keys={list(vv)[:8]}")
            else:
                print(f"   {kk}: {type(vv).__name__} {str(vv)[:120]}")
