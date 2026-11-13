import pandas as pd

P = r"D:\Project\qlib\projects\trend_combo\results"
g = pd.read_csv(P + r"\weight_grid_icw.csv")
cols = ["wp", "wf", "we", "train_ic_f5", "valid_ic_f5", "valid_icir_f5",
        "test_ic_f5", "test_icir_f5", "test_ic_f20", "test_icir_f20"]
print("=== 权重网格（IC 加权域内）按 wf 排序，看同一 wf 下 wp 的影响 ===")
g2 = g[g["we"] == 0.0].sort_values(["wf", "wp"])
print(g2[cols].to_string(index=False, float_format=lambda v: f"{v:+.4f}"))

print("\n=== 验证期 Top10 ===")
print(g[cols].head(10).to_string(index=False, float_format=lambda v: f"{v:+.4f}"))

print("\n=== 测试期 Top10（只作事后观察，不用于选型）===")
print(g[cols].sort_values("test_icir_f20", ascending=False).head(10).to_string(
    index=False, float_format=lambda v: f"{v:+.4f}"))
