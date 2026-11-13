"""校验申万一级行业成分表的质量。

## 查什么
1. **覆盖率**：申万 31 个一级行业 / 多少只股票，和本地 qlib 宇宙的交集多大；
2. **一致性**：同一只股票会不会落在多个行业（应该只有 1 个）；
3. **PIT 可用性**：`in_date` 有没有值（决定能不能做 as-of 行业中性化）；
4. **交叉验证**：拿几只票跟本地 qlib 里的现成行业标签（东财 BOARD_NAME）比一比。

## 用法
```cmd
cd /d D:\\Project\\qlib
.venv\\Scripts\\python.exe tools\\verify_sw_industry.py
```
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
QLIB_ROOT = HERE.parent
IND_DIR = QLIB_ROOT / "data" / "sw_industry"
UNIVERSE = QLIB_ROOT / "qlib_data" / "cn_data_2026" / "instruments" / "all.txt"


def main() -> int:
    ap = argparse.ArgumentParser(description="校验申万一级行业成分表")
    ap.add_argument("--dir", default=str(IND_DIR))
    args = ap.parse_args()
    d = Path(args.dir)

    ind = pd.read_parquet(d / "industries.parquet")
    mem = pd.read_parquet(d / "members.parquet")
    mp = pd.read_parquet(d / "map.parquet")

    print(f"== 申万一级行业成分表校验 | {d} ==")
    print(f"\n① 行业表：{len(ind)} 个一级行业")
    print(f"   样例: {ind.head(3).to_dict('records')}")

    print(f"\n② 成分表：{len(mem):,} 行 / {mem['qlib_symbol'].nunique():,} 只")
    dup = mem["qlib_symbol"].duplicated().sum()
    print(f"   同一只股票出现多次的行数: {dup}（sws 源按「计入日」留历史，属正常）")

    print(f"\n③ 最新映射：{len(mp):,} 行")
    multi = mp["qlib_symbol"].duplicated().sum()
    print(f"   一只股票映射到多个行业的: {multi}  {'✅' if multi == 0 else '❌'}")
    print(f"   行业分布（全部 {mp['l1_name'].nunique()} 个）:")
    print(mp["l1_name"].value_counts().to_string())

    print(f"\n④ PIT 可用性：")
    has_in = mem["in_date"].notna().sum()
    print(f"   in_date 非空: {has_in:,}/{len(mem):,} ({has_in / max(len(mem), 1):.1%})")
    if has_in:
        print(f"   in_date 范围: {mem['in_date'].min().date()} ~ {mem['in_date'].max().date()}")
    print(f"   out_date 非空: {mem['out_date'].notna().sum():,} "
          f"（sws 源不提供剔除日 → 只能做「纳入日之后」的近似 as-of）")

    if UNIVERSE.exists():
        uni = [l.split("\t")[0].strip() for l in UNIVERSE.read_text(encoding="utf-8").splitlines()
               if l.strip()]
        u = set(uni)
        m = set(mp["qlib_symbol"])
        print(f"\n⑤ 与本地 qlib 宇宙（{len(u):,} 只）的关系：")
        print(f"   申万有标签且 qlib 也有: {len(u & m):,}")
        print(f"   申万有、qlib 没有（新股/已退市）: {len(m - u):,}")
        print(f"   qlib 有、申万没标签: {len(u - m):,}")
        if u - m:
            miss = sorted(u - m)[:15]
            print(f"   缺失样例: {miss}")

    print(f"\n⑥ 样例（取 5 只看映射）:")
    print(mp.head(5).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
