import io

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

p = _ROOT + r"/projects/csi300_lgbm/tools/rank_latest.py"
s = io.open(p, encoding="utf-8").read()

pairs = [
    ("import json\nimport time\nimport urllib.request",
     "import json\nimport sys\nimport time\nimport urllib.request"),
    ('    names = fetch_names(df["symbol"].head(10).tolist())',
     '    names = fetch_names(df["symbol"].head(K).tolist())'),
    ("    top10 = df.head(10)\n    raw = {f: ctxm[f] for f in mc.FEATURES}",
     "    topk_df = df.head(K)\n    raw = {f: ctxm[f] for f in mc.FEATURES}"),
    ("    for _, r in top10.iterrows():", "    for _, r in topk_df.iterrows():"),
    ('    (mc.RESULTS / "picks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),\n'
     '                                           encoding="utf-8")\n'
     '    log(f"\\n已写出 results/picks.json（{len(picks)} 只）")',
     '    fname = "picks.json" if K == 10 else f"picks_K{K}.json"\n'
     '    (mc.RESULTS / fname).write_text(json.dumps(out, ensure_ascii=False, indent=2),\n'
     '                                    encoding="utf-8")\n'
     '    log(f"\\n已写出 results/{fname}（{len(picks)} 只）")'),
    ("def main():\n    t0 = time.time()", "def main():\n    K = int(sys.argv[1]) if len(sys.argv) > 1 else 10\n    t0 = time.time()"),
    ('"top10 是模型观察名单，不是买入指令"', 'f"top{K} 是模型观察名单，不是买入指令"'),
]

for old, new in pairs:
    if old not in s:
        raise SystemExit("NOT FOUND: " + old[:60])
    s = s.replace(old, new, 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched ok")
