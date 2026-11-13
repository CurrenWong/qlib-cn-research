import json

d = json.load(open(r"D:\Project\qlib\projects\q3_2026\data.json", encoding="utf-8"))
for code in ("SH600418", "SZ002230"):
    print("==", code)
    for dt, v in d["series"][code]:
        print("  ", dt, v)
