"""确认「为什么没有收盘价」：更新范围 300 vs 面板宇宙 637。"""

import re
from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parent.parent
LGBM = Path(r"D:\Project\qlib\projects\csi300_lgbm")
QLIB = Path(r"D:\Project\qlib\qlib_data\cn_data_2026")
LOG = LGBM / "results" / "update_data.log"

# 1. 更新日志里处理了哪些标的
txt = LOG.read_text(encoding="utf-8", errors="replace")
log_syms = set(re.findall(r"^([A-Z]{2}\d{6})$", txt, flags=re.M))
print("更新日志里处理的标的数:", len(log_syms))

# 2. 面板宇宙 + 末日
sc = pd.read_parquet(PROJ / "data" / "scores.parquet", columns=["datetime", "symbol", "close"])
sc["datetime"] = pd.to_datetime(sc["datetime"])
last = sc["datetime"].max()
last_date = sc[sc["close"].notna()].groupby("symbol")["datetime"].max()
universe = set(sc["symbol"])
have = set(last_date[last_date == last].index)
print("面板宇宙:", len(universe), "| 有 10-30 价:", len(have))

print("\n更新日志标的 == 有 10-30 价的集合 ?", log_syms == have)
print("  交集", len(log_syms & have), "| 仅日志", len(log_syms - have), "| 仅面板", len(have - log_syms))

# 3. qlib instruments 里的指数成分
inst = QLIB / "instruments"
print("\ninstruments 目录:", [p.name for p in inst.glob("*.txt")][:10])
for name in ["csi300.txt", "all.txt"]:
    f = inst / name
    if not f.exists():
        continue
    lines = [l.split("\t")[0].strip().upper() for l in
             f.read_text(encoding="utf-8", errors="replace").splitlines()
             if l.strip() and not l.startswith("#")]
    print(f"  {name}: {len(lines)} 行, 前 3 {lines[:3]}")
    if name == "csi300.txt":
        s = set(lines)
        print("    与面板宇宙交集:", len(s & universe),
              "| 与更新日志交集:", len(s & log_syms),
              "| 与有 10-30 价交集:", len(s & have))

# 4. 没有 10-30 价的票，它们的末日分布（再确认一遍）
miss = sorted(universe - have)
d = last_date[miss]
print("\n没有 10-30 价的 338 只：末日分布 top5")
print(d.value_counts().head(5).to_string())
print("\n其中末日 = 2026-10-27 的:", int((d == pd.Timestamp('2026-10-27')).sum()))
print("末日早于 2026-10-01 的（真停牌/退市）:", int((d < pd.Timestamp('2026-10-01')).sum()))
