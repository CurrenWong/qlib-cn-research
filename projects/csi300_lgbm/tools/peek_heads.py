import json
from pathlib import Path

p = Path(r"C:\Users\curre\.copaw\workspaces\J6c4mu\dist\csi300_lgbm\logs\verify.json")
d = json.loads(p.read_text(encoding="utf-8"))
for k, v in d.items():
    th = v.get("textHead") or ""
    print("=====", k, "| bodyLen", v.get("bodyLen"), "| textHead len", len(th),
          "| '**' in head:", th.count("**"))
    print("   ", th[:600].replace("\n", " ⏎ "))
