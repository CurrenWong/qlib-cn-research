"""调试：纯价量 top20 的取价情况。"""

from pathlib import Path

import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counterfactual_oct import fetch_raw, tx_symbol  # noqa: E402

for sym in ["SZ000046", "SH600068", "SH600074", "SH603986", "SZ300628"]:
    df = fetch_raw(tx_symbol(sym), count=12)
    print(f"\n{sym} → {len(df)} 行")
    if len(df):
        print(df.tail(6).to_string())
