"""每日更新 qlib 数据（单票/小股票池，全历史重写）。

## 为什么"全历史重写"而不是追加
qlib 的 close.bin 存**前复权**价，前复权基准是"最新一天"——一旦分红送股，整个历史的前复权价都变。
所以正确做法是每天重算该票全历史并整体重写；`dump_bin.py dump_update` 那种只追加新行
会在除权日造成价格跳变。单票 6000 根 K 线重写耗时毫秒级，没有性能问题。

## 数据源
优先腾讯（web.ifzq.gtimg.cn，实测稳定，单次 640 根需分页）；东财作备份（近期不稳定）。
两者都是 前复权(qfq) / 不复权 两套序列，factor = 前复权/不复权。

## 口径自校准
本数据目录（chenditc/qlib 官方 cn_data）里 close.bin = 不复权价 × factor，factor 有自己的基准；
而腾讯/东财的前复权在最新一天恒等于不复权价。两者差一个常数 k，用重叠日反解，
保证写入后价格连续、不跳变。

用法：
    .venv\\Scripts\\python.exe tools\\update_symbol_bins.py --dir <qlib数据目录> [--dry-run]
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TX_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
EM_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

DEFAULT_DIR = _ROOT + r"/qlib_data/cn_data_2026"
DEFAULT_SYMBOLS = ["SH600418", "SH000300"]
START = "2001-01-01"


# ------------------------------------------------------------------ 抓数
def _tx_page(symbol: str, fq: str, end: str = ""):
    param = f"{symbol},day,,{end},640,{fq}"
    r = requests.get(TX_URL, params={"param": param}, headers=UA, timeout=30)
    j = r.json()
    data = j.get("data")
    if not isinstance(data, dict):
        return []
    sub = data.get(symbol) or {}
    if not isinstance(sub, dict):
        return []
    for k in (f"{fq}day" if fq else "day", "qfqday", "day"):
        if isinstance(sub.get(k), list) and sub[k]:
            return sub[k]
    return []


def fetch_tx_symbol(symbol: str, fq: str) -> pd.DataFrame:
    """腾讯分页抓全历史。腾讯单次最多 640 根，按 end 往前翻。"""
    rows: dict = {}
    end = ""
    prev_earliest = None
    for _ in range(60):
        page = _tx_page(symbol, fq, end)
        if not page:
            break
        for r in page:
            rows[r[0]] = r
        earliest = min(rows)
        if earliest <= START:
            break
        if prev_earliest is not None and earliest >= prev_earliest:
            break  # 不再往前推进，说明到底了
        prev_earliest = earliest
        end = (pd.Timestamp(earliest) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        time.sleep(0.3)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([rows[d] for d in sorted(rows)])
    cols = ["date", "open", "close", "high", "low", "volume"] + [f"x{i}" for i in range(len(df.columns) - 6)]
    df.columns = cols[: len(df.columns)]
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "close", "high", "low", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.set_index("date").sort_index()


def fetch_em_symbol(secid: str, fqt: int) -> pd.DataFrame:
    p = {"secid": secid, "fields1": "f1,f2,f3,f4,f5,f6",
         "fields2": "f51,f52,f53,f54,f55,f56", "klt": 101, "fqt": fqt,
         "beg": "19900101", "end": "20500101", "lmt": 100000}
    r = requests.get(EM_URL, params=p, headers={**UA, "Referer": "https://quote.eastmoney.com/"}, timeout=30)
    k = (r.json().get("data") or {}).get("klines") or []
    if not k:
        return pd.DataFrame()
    rows = [x.split(",") for x in k]
    df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "close", "high", "low", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.set_index("date").sort_index()


def em_secid(code: str) -> str:
    num = "".join(ch for ch in code if ch.isdigit())
    return ("1." if code.upper().startswith("SH") else "0.") + num


def fetch_pair(code: str):
    """返回 (前复权df, 不复权df, 数据源名)"""
    tx = "sh" + "".join(ch for ch in code if ch.isdigit())
    try:
        adj, raw = fetch_tx_symbol(tx, "qfq"), fetch_tx_symbol(tx, "")
        if len(adj) and len(raw):
            return adj, raw, "腾讯"
    except Exception as e:  # noqa: BLE001
        print(f"    腾讯失败: {type(e).__name__}: {str(e)[:80]}")
    try:
        adj, raw = fetch_em_symbol(em_secid(code), 1), fetch_em_symbol(em_secid(code), 0)
        if len(adj) and len(raw):
            return adj, raw, "东财"
    except Exception as e:  # noqa: BLE001
        print(f"    东财失败: {type(e).__name__}: {str(e)[:80]}")
    return pd.DataFrame(), pd.DataFrame(), "无"


# ------------------------------------------------------------------ 写 bin
def write_bin(path: Path, values: np.ndarray, start_index: int) -> None:
    arr = np.asarray(values, dtype=np.float32)
    with open(path, "wb") as f:
        np.array([start_index], dtype=np.float32).tofile(f)
        arr.tofile(f)


def read_bin(path: Path):
    arr = np.fromfile(path, dtype=np.float32)
    return int(arr[0]), arr[1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    qlib_dir = Path(args.dir)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    cal_path = qlib_dir / "calendars" / "day.txt"
    inst_path = qlib_dir / "instruments" / "all.txt"
    if not cal_path.exists():
        sys.exit(f"找不到日历: {cal_path}")

    calendar = [x.strip() for x in cal_path.read_text().splitlines() if x.strip()]
    print(f"数据目录: {qlib_dir}")
    print(f"现有日历: {calendar[0]} ~ {calendar[-1]} ({len(calendar)} 天)")
    backup_dir = qlib_dir / "_backup" / time.strftime("%Y%m%d_%H%M%S")

    for code in symbols:
        print(f"\n{'=' * 68}\n{code}\n{'=' * 68}")
        adj, raw, src = fetch_pair(code)
        if not len(adj):
            print("  ❌ 两个数据源都失败，跳过")
            continue
        print(f"  [{src}] 前复权 {len(adj)} 根 / 不复权 {len(raw)} 根 | "
              f"{adj.index[0].date()} ~ {adj.index[-1].date()}")

        common = adj.index.intersection(raw.index)
        factor = (adj.loc[common, "close"] / raw.loc[common, "close"]).replace([np.inf, -np.inf], np.nan)

        # 日历补新日子
        cal_set = set(calendar)
        new_dates = [d.strftime("%Y-%m-%d") for d in adj.index if d.strftime("%Y-%m-%d") not in cal_set]
        if new_dates:
            print(f"  日历需追加 {len(new_dates)} 天: {new_dates[0]} ... {new_dates[-1]}")
            if not args.dry_run:
                calendar = sorted(cal_set | set(new_dates))
                cal_path.write_text("\n".join(calendar) + "\n")
                print(f"  日历已更新 → {len(calendar)} 天，末日 {calendar[-1]}")

        dates = [d.strftime("%Y-%m-%d") for d in adj.index]
        cal_idx = {d: i for i, d in enumerate(calendar)}
        if dates[0] not in cal_idx:
            print(f"  ⚠ 首日 {dates[0]} 不在日历，跳过")
            continue
        start_index = cal_idx[dates[0]]

        feat_dir = qlib_dir / "features" / code.lower()
        old_close = feat_dir / "close.day.bin"

        # 自校准（价格 / 成交量单位）
        k_price = k_vol = 1.0
        old_vals = None
        old_last_date = None
        if old_close.exists():
            si, old_vals = read_bin(old_close)
            old_last_date = calendar[si + len(old_vals) - 1]
            if old_last_date in dates:
                k_price = float(old_vals[-1]) / float(adj.loc[pd.Timestamp(old_last_date), "close"])
            vol_p = feat_dir / "volume.day.bin"
            if vol_p.exists() and old_last_date in dates:
                _, vv = read_bin(vol_p)
                em_vol = float(adj.loc[pd.Timestamp(old_last_date), "volume"]) * 100.0
                if em_vol:
                    k_vol = float(vv[-1]) / em_vol
            print(f"  现有末日 {old_last_date} | 校准: 价格 ×{k_price:.6f}, 成交量 ×{k_vol:.6f}")

        fields = {
            "open": adj["open"].values * k_price,
            "high": adj["high"].values * k_price,
            "low": adj["low"].values * k_price,
            "close": adj["close"].values * k_price,
            "volume": adj["volume"].values * 100.0 * k_vol,
            "factor": factor.reindex(adj.index).ffill().bfill().values * k_price,
            "change": adj["close"].pct_change().fillna(0).values,
        }

        # ★ 关键：qlib 的 .bin 是按【日历】对齐的，一天一个值，停牌日必须是 NaN。
        # 数据源返回的是稀疏序列（缺停牌日），必须 reindex 到日历，否则整体错位。
        span = calendar[start_index:]                      # 从首日到日历末日
        span_idx = pd.to_datetime(span)
        aligned = {}
        for name, vals in fields.items():
            s = pd.Series(np.nan, index=span_idx, dtype=float)
            s.loc[adj.index] = vals
            aligned[name] = s.values

        # 连续性对账（按日历下标取，不用偏移量）
        if old_vals is not None and old_last_date in cal_idx:
            k = cal_idx[old_last_date] - start_index
            if 0 <= k < len(aligned["close"]) and not np.isnan(aligned["close"][k]):
                gap = abs(aligned["close"][k] / old_vals[-1] - 1) * 100
                print(f"  {'✅' if gap < 0.5 else '⚠️'} 连续性 {old_last_date}: "
                      f"旧 {old_vals[-1]:.4f} vs 新 {aligned['close'][k]:.4f}（差 {gap:.3f}%）")

        if args.dry_run:
            print(f"  [dry-run] 将写 {len(span)} 天（{span[0]} ~ {span[-1]}），起始下标 {start_index}")
            continue

        if not args.no_backup:
            backup_dir.mkdir(parents=True, exist_ok=True)
            if feat_dir.exists():
                shutil.copytree(feat_dir, backup_dir / code.lower(), dirs_exist_ok=True)

        feat_dir.mkdir(parents=True, exist_ok=True)
        for name, vals in aligned.items():
            write_bin(feat_dir / f"{name}.day.bin", vals, start_index)
        n_nan = int(np.isnan(aligned["close"]).sum())
        print(f"  ✅ 写入 {len(span)} 天（{span[0]} ~ {span[-1]}），含 {n_nan} 个停牌/缺失 NaN，起始下标 {start_index}")

        if inst_path.exists():
            lines = inst_path.read_text().splitlines()
            out, hit = [], False
            for ln in lines:
                p = ln.split("\t")
                if len(p) >= 3 and p[0].upper() == code:
                    p[2] = dates[-1]
                    out.append("\t".join(p))
                    hit = True
                else:
                    out.append(ln)
            if not hit:
                out.append(f"{code}\t{dates[0]}\t{dates[-1]}")
            inst_path.write_text("\n".join(out) + "\n")

    print(f"\n{'=' * 68}\n完成。日历末日: {calendar[-1]}")
    if backup_dir.exists():
        print("备份:", backup_dir)

    # 自动刷新数据状态文档
    try:
        import subprocess
        import sys as _sys

        subprocess.run([_sys.executable, str(Path(__file__).with_name("write_data_status.py")),
                        "--dir", str(qlib_dir)], check=False)
    except Exception as e:  # noqa: BLE001
        print(f"（状态文档刷新失败，不影响数据：{type(e).__name__}）")


if __name__ == "__main__":
    main()
