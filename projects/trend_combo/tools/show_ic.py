import json

import pandas as pd

r = json.load(open(r"D:\Project\qlib\projects\trend_combo\results\ic_results.json", encoding="utf-8"))
for v in ["price_only", "fund_only", "event_only"]:
    for lab in ["fwd5", "fwd20"]:
        e = r["variants"][v][lab]
        print(v, lab,
              {k: round(e[k].get("ic_mean", 0), 4) for k in ["train", "valid", "test"]},
              "IR_test", round(e["test"].get("icir", 0), 3),
              "t_test", round(e["test"].get("t_stat", 0), 2))

g = pd.read_csv(r"D:\Project\qlib\projects\trend_combo\results\weight_grid.csv")
print(g.head(10)[["name", "valid_ic_f5", "valid_icir_f5", "test_ic_f5", "test_ic_f20"]].to_string(index=False))
print("grid rows", len(g), "valid_icir non-null", g["valid_icir_f5"].notna().sum())
print("dtypes", g.dtypes.to_dict())
