"""导出需要补 bar 的标的名单（面板 10-30 缺收盘价的那些），并切成分块。

用法：..\\..\\.venv\\Scripts\\python.exe tools\make_append_list.py
产出：data\\append_list_*.txt（每块一份）+ data\\append_list_all.txt
"""

from pathlib import Path

import pandas as pd

PROJ = Path(__file__).resolve().parent.parent
DATA = PROJ / "data"
DATA.mkdir(exist_ok=True)

sc = pd.read_parquet(PROJ / "data" / "scores.parquet", columns=["datetime", "symbol", "close"])
sc["datetime"] = pd.to_datetime(sc["datetime"])
last = sc["datetime"].max()
last_date = sc[sc["close"].notna()].groupby("symbol")["datetime"].max()
universe = sorted(set(sc["symbol"]))
miss = [s for s in universe if last_date.get(s, pd.NaT) != last]

(DATA / "append_list_all.txt").write_text("\n".join(miss) + "\n", encoding="utf-8")
print(f"需要补的标的 {len(miss)} 只 → {DATA / 'append_list_all.txt'}")
print("末日分布:")
print(last_date[miss].value_counts().head(4).to_string())

CHUNK = 85
chunks = [miss[i:i + CHUNK] for i in range(0, len(miss), CHUNK)]
for i, c in enumerate(chunks, 1):
    p = DATA / f"append_list_{i}.txt"
    p.write_text("\n".join(c) + "\n", encoding="utf-8")
    print(f"  块{i}: {len(c)} 只 → {p}")
print(f"共 {len(chunks)} 块")
