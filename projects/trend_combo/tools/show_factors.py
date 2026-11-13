import json

import pandas as pd

P = r"D:\Project\qlib\projects\trend_combo\results"
r = json.load(open(P + r"\ic_results.json", encoding="utf-8"))
f = pd.read_csv(P + r"\factor_ic.csv")

print("=== 因子表（训练期排序，看哪些留下、哪些方向被推翻）===")
f["abs_train"] = f["fwd5_train_ic"].abs()
f = f.sort_values("abs_train", ascending=False)
for _, r_ in f.iterrows():
    flag = "✓保留" if r_["keep"] else "✗剔除"
    flip = "方向被推翻" if (r_["keep"] and not r_["prior_agrees"]) else ""
    print(f"{r_['factor']:<20} {r_['domain']:<16} 先验{r_['prior_dir']:>2} "
          f"train {r_['fwd5_train_ic']:+.4f}(t{r_['fwd5_train_t']:+.1f}) "
          f"valid {r_['fwd5_valid_ic']:+.4f} test {r_['fwd5_test_ic']:+.4f} {flag} {flip}")

print("\n=== fwd20 ===")
for v in ["price_only", "fund_only", "event_only", "mix_selected"]:
    e = r["variants"][v]["fwd20"]
    print(f"{v:<16} train {e['train']['ic_mean']:+.4f}(IR {e['train']['icir']:+.2f}) "
          f"valid {e['valid']['ic_mean']:+.4f}(IR {e['valid']['icir']:+.2f}) "
          f"test {e['test']['ic_mean']:+.4f}(IR {e['test']['icir']:+.2f}, t {e['test']['t_stat']:+.2f})")

print("\n=== 分年 fwd5 ===")
y = pd.DataFrame(r["yearly"])
for v in ["price_only", "fund_only", "mix_selected"]:
    s = y[(y["variant"] == v) & (y["label"] == "fwd5")].sort_values("year")
    print(v, {int(a): round(b, 4) for a, b in zip(s["year"], s["ic_mean"])})

print("\n=== 分档（测试期 fwd20）===")
print(r["buckets_test_fwd20"])
print("\n=== 选中 ===", r["selected"])
print("保留因子数", r["n_kept"], "/", r["n_factors"])
