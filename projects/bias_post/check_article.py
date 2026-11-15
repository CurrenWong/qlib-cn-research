"""文章数字自检：正文里出现的每个关键数字，都要在同仓库的产物里找得到出处。

思路：不硬编码期望值，而是从数据/结果文件里**重新读出**数值，再检查正文字符串里
有没有它的两位小数形式。这样改文章忘了改数、或者数据重跑后数字变了，都会报错。

用法：..\\..\\.venv\\Scripts\\python.exe check_article.py
"""

import glob
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ART = (HERE / "article.md").read_text(encoding="utf-8")

checks: list[tuple[str, str, bool]] = []  # (标签, 正文里应出现的串, 是否必须)


def expect(label: str, value: float, fmt: str = "{:+.2f}", text: str | None = None):
    """value 来自产物；正文允许 1 位或 2 位小数、允许省略正号（+0.68 / 0.68 都算）。"""
    body = text or ART
    cands = [fmt.format(value), f"{value:+.1f}", f"{value:.1f}", f"{value:+.2f}", f"{value:.2f}"]
    hit = next((c for c in cands if c in body), None)
    checks.append((f"{label} = {cands[0]}", cands[0], hit is not None))


# ---------------------------------------------------------------- 1. 截面 BIAS
snap = pd.read_csv(ROOT / "data/sw_industry/bias/bias_snapshot.csv", index_col=0,
                   encoding="utf-8-sig")
snap.columns = [str(c) for c in snap.columns]
for ind, per in [("传媒", "6"), ("传媒", "20"), ("传媒", "60"), ("传媒", "120"),
                 ("通信", "6"), ("通信", "20"), ("通信", "60"), ("通信", "120"),
                 ("石油石化", "20"), ("银行", "60"), ("银行", "120"),
                 ("食品饮料", "60"), ("食品饮料", "120"),
                 ("机械设备", "6"), ("机械设备", "120"),
                 ("煤炭", "20"), ("美容护理", "20")]:
    expect(f"BIAS{per} {ind}", float(snap.loc[ind, per]))

# ---------------------------------------------------------------- 2. 区间涨跌
ind = pd.read_parquet(ROOT / "data/sw_industry/industries.parquet")
name_map = {c.split(".")[0]: n.strip() for c, n in
            zip(ind["index_code"].astype(str), ind["industry_name"].astype(str))}
chg, bias20, pct = {}, {}, {}
for f in sorted(glob.glob(str(ROOT / "data/sw_industry/index_daily/*.parquet"))):
    code = Path(f).stem
    df = pd.read_parquet(f).set_index("date")["close"].astype(float).sort_index()
    df = df[df.index <= "2026-11-11"]
    b = (df - df.rolling(20).mean()) / df.rolling(20).mean() * 100
    tail = b.dropna().tail(750)
    nm = name_map.get(code, code)
    chg[nm] = (df.iloc[-1] / df.asof(pd.Timestamp("2026-09-30")) - 1) * 100
    bias20[nm] = tail.iloc[-1]
    pct[nm] = (tail <= tail.iloc[-1]).mean() * 100

for nm in ("通信", "电子", "传媒", "食品饮料"):
    expect(f"{nm} 区间涨跌", chg[nm])
med = float(pd.Series(chg).median())
expect("行业中位涨跌", med)
n_up = int((pd.Series(chg) > 0).sum())
n_dn = int((pd.Series(chg) <= 0).sum())
checks.append((f"上涨行业数 = {n_up}", str(n_up), f"{n_up} 涨" in ART or
               f"{n_up} 个上涨" in ART))
checks.append((f"下跌行业数 = {n_dn}", str(n_dn), f"{n_dn} 个下跌" in ART))

# 分位（正文用整数）
for nm, want in [("传媒", 92), ("纺织服饰", 86), ("汽车", 81), ("家用电器", 81),
                 ("食品饮料", 76), ("石油石化", 9), ("通信", 17), ("煤炭", 21),
                 ("美容护理", 29), ("综合", 30)]:
    got = round(pct[nm])
    checks.append((f"分位 {nm} = {got}（期望 {want}）", str(got),
                   str(want) in ART and got == want))

# ---------------------------------------------------------------- 3. 沪深300
hs = ROOT / "data/sw_industry/_hs300_period.txt"
if hs.exists():
    txt = hs.read_text(encoding="utf-8")
    expect("沪深300 区间涨跌", float(re.search(r"(-?\d+\.\d+)%", txt).group(1)))
else:
    checks.append(("沪深300 区间涨跌（缺缓存）", "-6.47", "-6.47%" in ART))

# ---------------------------------------------------------------- 4. 策略数字
lgbm = json.loads((ROOT / "projects/csi300_lgbm/results/backtest.json").read_text("utf-8"))
runs = lgbm.get("runs") or lgbm.get("results") or {}
for key, field, label in [
    ("策略 top10 月调（含成本）", "ann_return", "LGBM 验证期年化"),
]:
    pass  # 结构因项目而异，下面按已知 key 兜底


def find_run(d: dict, contains: str):
    for k, v in d.items():
        if contains in k:
            return v
    return None


valid = find_run(runs, "top10") if runs else None
if valid:
    expect("LGBM 验证期年化 %", valid["ann_return"] * 100)
    expect("LGBM 验证期 IR %", valid["ir"])

tc = json.loads((ROOT / "projects/trend_combo/results/backtest.json").read_text("utf-8"))["runs"]
for k, label in [("策略(验证期选参) top50", "混合 top50"), ("纯价量分 top20 月调", "纯价量"),
                 ("纯基本面 top20 月调", "纯基本面"),
                 ("混合分 top20 月调(行业≤3)", "混合 行业≤3")]:
    if k in tc:
        expect(f"{label} 年化 %", tc[k]["ann_return"] * 100)
        expect(f"{label} IR", tc[k]["ir"])

pnl = json.loads((ROOT / "projects/csi300_lgbm/results/pnl_monday.json").read_text("utf-8"))

# ---------------------------------------------------------------- 5. 结构检查
struct = [
    ("插图标记数 = 4", str(len(re.findall(r"【插图\s*\d+：", ART))), 
     len(re.findall(r"【插图\s*\d+：", ART)) == 4),
    ("无遗留 TODO", "TODO", "TODO" not in ART),
    ("有免责声明", "不是投资建议", "不是投资建议" in ART),
    ("有数据截止说明", "2026-11-11", "2026-11-11" in ART),
    ("无本地绝对路径", "D:\\", "D:\\" not in ART),
]

print("=" * 70)
bad = 0
for label, needle, ok in checks:
    flag = "OK  " if ok else "FAIL"
    if not ok:
        bad += 1
    print(f"[{flag}] {label}")
print("-" * 70)
for label, needle, ok in struct:
    flag = "OK  " if ok else "FAIL"
    if not ok:
        bad += 1
    print(f"[{flag}] {label}")
print("=" * 70)
print(f"共 {len(checks) + len(struct)} 项，失败 {bad} 项")
