import json

r = json.load(open(r"D:\Project\qlib\projects\trend_combo\results\ic_results.json", encoding="utf-8"))
V = r["variants"]
print("变体 | 训练IC | 验证IC | 验证IR | 测试IC | 测试IR | 测试t | 测试IC20 | 测试IR20")
for v in ["price_only", "fund_only", "event_only", "mix_selected", "price_prior_dir"]:
    e5, e20 = V[v]["fwd5"], V[v]["fwd20"]
    print(f"{v} | {e5['train']['ic_mean']:+.4f} | {e5['valid']['ic_mean']:+.4f} | "
          f"{e5['valid']['icir']:+.3f} | {e5['test']['ic_mean']:+.4f} | "
          f"{e5['test']['icir']:+.3f} | {e5['test']['t_stat']:+.1f} | "
          f"{e20['test']['ic_mean']:+.4f} | {e20['test']['icir']:+.3f}")
