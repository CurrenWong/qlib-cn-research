"""检查 append_latest_bars 四块日志的结果统计。"""

from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
for i in range(1, 5):
    p = PROJ / "results" / f"append_{i}.log"
    if not p.exists():
        print(f"块{i}: 无日志")
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    print(f"块{i}: 追加完成 {t.count('追加完成')} | 已是最新 {t.count('已是最新')} | "
          f"取数失败 {t.count('取数失败')} | 放弃 {t.count('放弃')} | "
          f"无bin {t.count('还没有 .bin')} | 行数 {len(t.splitlines())}")
    # 列出没成功的标的
    import re
    blocks = re.split(r"={60,}\n", t)
    for b in blocks:
        first = b.splitlines()[0].strip() if b.splitlines() else ""
        if re.fullmatch(r"[A-Z]{2}\d{6}", first) and "追加完成" not in b:
            why = [ln.strip() for ln in b.splitlines()
                   if any(k in ln for k in ["取数失败", "放弃", "已是最新", "还没有 .bin"])]
            print(f"   {first}: {why[0] if why else '?'}")
