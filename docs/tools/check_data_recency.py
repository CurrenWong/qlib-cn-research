"""查：现有数据边界 + 上游是否有更新版本的数据集。"""

import json
import sys

import requests

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

sys.path.insert(0, _ROOT)

HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "qlib-probe"}


def get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=60, **kw)
    return r


def show_releases(repo, limit=5):
    print(f"\n{'=' * 70}\n{repo}\n{'=' * 70}")
    r = get(f"https://api.github.com/repos/{repo}/releases?per_page={limit}")
    if r.status_code != 200:
        print("HTTP", r.status_code, r.text[:200])
        return
    for rel in r.json():
        print(f"[{rel['tag_name']}] published={rel['published_at']} name={rel.get('name')}")
        for a in rel.get("assets", [])[:6]:
            mb = a["size"] / 1024 / 1024
            print(f"     - {a['name']:55s} {mb:8.1f} MB  updated={a['updated_at']}")


# 1) 上游官方示例数据
show_releases("SunsetWolf/qlib_dataset", limit=6)

# 2) 社区每日更新版（qlib 官方 scripts/README 里推荐的 crowdsourced 数据）
show_releases("chenditc/investment_data", limit=3)


# 3) 现有本地数据边界
print(f"\n{'=' * 70}\n本地 cn_data 边界\n{'=' * 70}")
from pathlib import Path

import pandas as pd

root = Path(_ROOT + r"/qlib_data/cn_data")
cal = [x.strip() for x in (root / "calendars" / "day.txt").read_text().splitlines() if x.strip()]
print(f"日历: {cal[0]} ~ {cal[-1]}  共 {len(cal)} 天")

inst = [line.split("\t") for line in (root / "instruments" / "all.txt").read_text().splitlines() if line.strip()]
ends = pd.Series([i[2] for i in inst if len(i) >= 3])
print(f"all.txt 股票数: {len(inst)}，结束日分布（前 5）:")
print(ends.value_counts().head(5).to_string())
