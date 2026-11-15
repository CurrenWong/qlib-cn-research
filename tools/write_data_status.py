"""生成 / 刷新数据状态文档 DATA_STATUS.md。

被 append_latest_bars.py 和 update_symbol_bins.py 在成功后自动调用，
保证"当前数据更新到哪一天"这个记录永远不会过期；也可以单独手动跑。

用法：
    .venv\\Scripts\\python.exe tools\\write_data_status.py
    .venv\\Scripts\\python.exe tools\\write_data_status.py --dir <数据目录>
"""

import argparse
import re
import time
from pathlib import Path

import numpy as np

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

DEFAULT_DIR = _ROOT + r"/qlib_data/cn_data_2026"
DEFAULT_OUT = _ROOT + r"/DATA_STATUS.md"
WATCH = ["SH600418", "SH000300"]


def read_bin_last(path: Path):
    if not path.exists():
        return None
    arr = np.fromfile(path, dtype=np.float32)
    if len(arr) < 2:
        return None
    return int(arr[0]), arr[1:]


def collect(qlib_dir: Path):
    cal_path = qlib_dir / "calendars" / "day.txt"
    cal = [x.strip() for x in cal_path.read_text().splitlines() if x.strip()]

    inst_path = qlib_dir / "instruments" / "all.txt"
    instruments = []
    if inst_path.exists():
        for ln in inst_path.read_text().splitlines():
            p = ln.split("\t")
            if len(p) >= 3:
                instruments.append(p)

    symbols = []
    for code in WATCH:
        feat = qlib_dir / "features" / code.lower()
        cp = read_bin_last(feat / "close.day.bin")
        fp = read_bin_last(feat / "factor.day.bin")
        if cp is None:
            symbols.append({"code": code, "missing": True})
            continue
        si, closes = cp
        last_idx = si + len(closes) - 1
        symbols.append({
            "code": code,
            "first": cal[si] if si < len(cal) else "?",
            "last": cal[last_idx] if last_idx < len(cal) else "?",
            "close": float(closes[-1]),
            "factor": float(fp[1][-1]) if fp else np.nan,
            "rows": len(closes),
        })

    return {
        "dir": str(qlib_dir),
        "cal_first": cal[0],
        "cal_last": cal[-1],
        "cal_days": len(cal),
        "n_instruments": len(instruments),
        "symbols": symbols,
    }


def previous_log(out_path: Path):
    """从已有文档里取出「更新日志」表的历史行。"""
    if not out_path.exists():
        return []
    txt = out_path.read_text(encoding="utf-8")
    m = re.search(r"## 更新日志\s*\n\n(\|.*?)\n\n", txt, re.S)
    if not m:
        return []
    rows = [ln for ln in m.group(1).splitlines() if ln.startswith("|") and "---" not in ln]
    return rows[1:] if rows else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    qlib_dir = Path(args.dir)
    # 输出位置自动决定：正式数据目录 → 项目根 DATA_STATUS.md
    # 其他目录（测试副本等）→ 该目录下的 _DATA_STATUS.md，避免覆盖正式记录
    if args.out:
        out = Path(args.out)
    elif str(qlib_dir).rstrip("\\") == DEFAULT_DIR:
        out = Path(DEFAULT_OUT)
    else:
        out = qlib_dir / "_DATA_STATUS.md"
    info = collect(qlib_dir)

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    rows = previous_log(out)
    new_row = (f"| {now} | {info['cal_last']} | {info['cal_days']} | "
               + " / ".join(f"{s['code']} {s.get('close', float('nan')):.4f}" if not s.get("missing")
                            else f"{s['code']} —" for s in info["symbols"]) + " |")

    # 同一天只保留最新一条记录
    rows = [r for r in rows if f"| {info['cal_last']} |" not in r]
    rows.append(new_row)

    sym_lines = []
    for s in info["symbols"]:
        if s.get("missing"):
            sym_lines.append(f"| {s['code']} | — | — | — | — | 缺数据 |")
        else:
            sym_lines.append(
                f"| {s['code']} | {s['first']} | **{s['last']}** | {s['close']:.4f} | {s['factor']:.6f} | {s['rows']} 天 |"
            )

    doc = f"""# 数据状态（自动生成，勿手改）

> 本文件由 `tools/write_data_status.py` 自动生成；`append_latest_bars.py` /
> `update_symbol_bins.py` 每次更新成功后会自动刷新它。
> 手动刷新：`.venv\\Scripts\\python.exe tools\\write_data_status.py`

## 当前状态

| 项 | 值 |
|---|---|
| **数据最新到** | **{info['cal_last']}** |
| 状态文件生成时间 | {now} |
| 数据目录 | `{info['dir']}` |
| 交易日历 | {info['cal_first']} ~ {info['cal_last']}（{info['cal_days']} 个交易日） |
| 股票数 | instruments/all.txt 共 {info['n_instruments']} 条（含已退市；按日期区间过滤后 2026 年在市约 5600 只） |
| 数据来源 | `chenditc/investment_data` release **2026-10-27**（qlib_bin.tar.gz，569,575,728 bytes）+ 后续按日追加 |

### 关键标的

| 代码 | 起始 | **最新交易日** | 收盘（复权） | factor | 行数 |
|---|---|---|---|---|---|
{chr(10).join(sym_lines)}

## 更新日志

| 更新时间 | 数据最新到 | 日历天数 | 标的末价 |
|---|---|---|---|
{chr(10).join(rows)}

## 怎么更新（不注册定时任务，手动跑）

```cmd
:: 普通交易日（只追加当天，历史零改动；用不复权接口，前复权接口被 WAF 封时也能用）
cd /d <repo>
.venv\\Scripts\\python.exe tools\\append_latest_bars.py --dir qlib_data\\cn_data_2026

:: 分红送股之后（factor 变了，必须全历史重写）
.venv\\Scripts\\python.exe tools\\update_symbol_bins.py --dir qlib_data\\cn_data_2026

:: 只想刷新本文件
.venv\\Scripts\\python.exe tools\\write_data_status.py
```

每次更新会自动备份到 `{info['dir']}\\_backup\\<时间戳>\\`。

## 相关文档

- [`docs/DATA_UPDATE.md`](docs/DATA_UPDATE.md) —— 三种更新方案对比、复权与日历对齐的坑
- [`docs/QLIB_USAGE.md`](docs/QLIB_USAGE.md) —— qlib 使用手册
- [`projects/jac_600418/README.md`](projects/jac_600418/README.md) —— 江淮汽车策略（第 12 节的 7.8 年样本外检验基于本数据）
"""

    out.write_text(doc, encoding="utf-8")
    print(f"已写入 {out}")
    print(f"  数据最新到: {info['cal_last']}  日历 {info['cal_days']} 天  股票 {info['n_instruments']} 只")
    for s in info["symbols"]:
        if s.get("missing"):
            print(f"  {s['code']}: 缺数据")
        else:
            print(f"  {s['code']}: {s['first']} ~ {s['last']}  收盘 {s['close']:.4f}  factor {s['factor']:.6f}")


if __name__ == "__main__":
    main()
