"""查候选数据源的覆盖范围：chenditc manifest + SunsetWolf 仓库说明。"""

import json

import requests

H = {"User-Agent": "qlib-probe", "Accept": "application/vnd.github+json"}

# 1) chenditc/investment_data 的 manifest（小文件，会列出数据覆盖信息）
url = "https://github.com/chenditc/investment_data/releases/download/2026-10-27/qlib_bin.manifest.json"
r = requests.get(url, headers=H, timeout=60)
print("manifest HTTP", r.status_code, "len", len(r.content))
if r.status_code == 200:
    try:
        j = r.json()
        print("顶层 key:", list(j.keys())[:10])
        print(json.dumps(j, ensure_ascii=False, indent=2)[:1500])
    except Exception as e:
        print("非 JSON:", e, r.text[:300])

# 2) SunsetWolf 仓库 README（看是否有覆盖区间说明）
r2 = requests.get("https://raw.githubusercontent.com/SunsetWolf/qlib_dataset/main/README.md", headers=H, timeout=60)
print("\n=== SunsetWolf/qlib_dataset README ===")
print(r2.status_code, r2.text[:1200] if r2.status_code == 200 else r2.text[:200])

# 3) chenditc 仓库 README（了解数据口径与用法）
r3 = requests.get("https://raw.githubusercontent.com/chenditc/investment_data/main/README.md", headers=H, timeout=60)
print("\n=== chenditc/investment_data README（前 2000 字） ===")
print(r3.status_code)
print(r3.text[:2000] if r3.status_code == 200 else r3.text[:200])
