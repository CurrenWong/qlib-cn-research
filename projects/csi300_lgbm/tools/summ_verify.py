import json
from pathlib import Path

root = Path(r"C:\Users\curre\.copaw\workspaces\J6c4mu\dist\csi300_lgbm\logs")
for f in ["verify.json", "verify_frames.json", "verify_frames2.json", "verify_precise.json"]:
    p = root / f
    if not p.exists():
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    print("=====", f, "type", type(d).__name__,
          (list(d)[:10] if isinstance(d, dict) else len(d)))
    if isinstance(d, dict):
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            cen = v.get("census", {})
            print(f"  {k:12s} tables={cen.get('table')} img={cen.get('img')} "
                  f"tr={v.get('trCount')} literal**={v.get('literalAsteriskCount')} "
                  f"textLen={v.get('textLen')}")
