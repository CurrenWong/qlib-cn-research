"""查 316 只停在 2026-10-27 的原因：翻数据更新日志，看这些票当时发生了什么。"""

import re
from collections import Counter
from pathlib import Path

LGBM = Path(r"D:\Project\qlib\projects\csi300_lgbm")
QLIB = Path(r"D:\Project\qlib\qlib_data\cn_data_2026")
LOG = LGBM / "results" / "update_data.log"

txt = LOG.read_text(encoding="utf-8", errors="replace")
print("日志行数", len(txt.splitlines()), "| 大小", LOG.stat().st_size // 1024, "KB")

blocks = re.split(r"={60,}\n", txt)
print("按分隔线切出的段数:", len(blocks))

# 每段第一行通常是 symbol
per = {}
for b in blocks:
    m = re.match(r"\s*([A-Z]{2}\d{6})\s*$", b.splitlines()[0].strip()) if b.strip() else None
    if m:
        per[m.group(1)] = b
print("识别到的 symbol 段数:", len(per))

kinds = Counter()
for sym, b in per.items():
    if "末日 2026-10-30" in b:
        kinds["已追加到 10-30"] += 1
    elif "跳过" in b and "无" in b:
        kinds["跳过/无数据"] += 1
    elif "失败" in b or "❌" in b:
        kinds["失败"] += 1
    elif "现有末日 2026-10-27" in b:
        kinds["停在 10-27（其它原因）"] += 1
    else:
        kinds["其它"] += 1
print("\n按结果统计：", dict(kinds))

print("\n=== 抽样：停在 10-27 的票，日志里写了什么 ===")
for sym in ["SH600008", "SH600021", "SH600037", "SH600060"]:
    b = per.get(sym)
    print(f"\n----- {sym} -----")
    print((b or "（日志里没有这一段）")[:900])

print("\n=== 日志里出现过的关键词计数 ===")
for kw in ["跳过", "失败", "❌", "无数据", "已停牌", "退市", "新股", "直到", "until"]:
    print(f"  {kw}: {txt.count(kw)}")

print("\n=== 本地 bin 真实末日（正确路径） ===")
import numpy as np

for sym in ["SH600008", "SH601919", "SH600648", "SH600079", "SH600005"]:
    f = QLIB / "features" / sym / "day.bin"
    if not f.exists():
        print(f"  {sym}: 无 bin")
        continue
    arr = np.fromfile(f, dtype=np.float32)
    n = (len(arr) - 1) // 5
    print(f"  {sym}: bars={n} 起始下标={int(arr[0])}")
