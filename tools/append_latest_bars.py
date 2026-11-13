"""追加最新交易日（无除权日专用；历史零改动）。

## 为什么需要这个
`update_symbol_bins.py`（全历史重写）依赖腾讯 **前复权** 接口，该接口会被腾讯 WAF 拦截
（HTTP 501 → waf.tencent.com/501page.html）。而 **不复权** 的 `kline` 接口仍然可用。

在没有除权除息的日子里，本数据目录的 `close.bin = 不复权价 × factor`，且 factor 不变，
所以「不复权价 × 已有的 factor」就能正确追加新的一天，**完全不需要重写历史**。
（一旦发生分红送股，factor 会变，必须用全历史重写模式。）

## 用法
    .venv\\Scripts\\python.exe tools\\append_latest_bars.py --dir <qlib数据目录>
    .venv\\Scripts\\python.exe tools\\append_latest_bars.py --dir <...> --dry-run
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"   # 不复权
DEFAULT_DIR = r"D:\Project\qlib\qlib_data\cn_data_2026"
DEFAULT_SYMBOLS = ["SH600418", "SH000300"]


def tx_symbol(code: str) -> str:
    return ("sh" if code.upper().startswith("SH") else "sz") + "".join(ch for ch in code if ch.isdigit())


def fetch_raw(symbol: str, count: int = 640) -> pd.DataFrame:
    """腾讯 kline（不复权），单次最多 640 根。"""
    for attempt in range(6):
        try:
            r = requests.get(KLINE_URL, params={"param": f"{symbol},day,,,{count}"},
                             headers=UA, timeout=30)
            if r.status_code != 200 or not r.text.strip().startswith("{"):
                raise RuntimeError(f"HTTP {r.status_code} 非 JSON 响应")
            sub = (r.json().get("data") or {}).get(symbol) or {}
            rows = sub.get("day") or []
            if not rows:
                raise RuntimeError("空返回")
            df = pd.DataFrame(rows)
            df = df.iloc[:, :6]
            df.columns = ["date", "open", "close", "high", "low", "volume"]
            df["date"] = pd.to_datetime(df["date"])
            for c in ["open", "close", "high", "low", "volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            return df.set_index("date").sort_index()
        except Exception as e:  # noqa: BLE001
            print(f"    第 {attempt+1} 次失败: {type(e).__name__}: {str(e)[:90]}")
            time.sleep(3 + attempt * 2)
    return pd.DataFrame()


def read_bin(path: Path):
    arr = np.fromfile(path, dtype=np.float32)
    return int(arr[0]), arr[1:]


def write_bin(path: Path, values: np.ndarray, start_index: int) -> None:
    with open(path, "wb") as f:
        np.array([start_index], dtype=np.float32).tofile(f)
        np.asarray(values, dtype=np.float32).tofile(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--symbols-file", default=None,
                    help="从文件读标的清单（每行一个，或逗号分隔）")
    ap.add_argument("--until", default=None,
                    help="只追加到该日期（含）。用于盘中运行时排除当日未收盘的 bar")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    qlib_dir = Path(args.dir)
    if args.symbols_file:
        txt = Path(args.symbols_file).read_text(encoding="utf-8")
        symbols = [s.strip().upper() for s in txt.replace(",", "\n").split() if s.strip()]
    else:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    cal_path = qlib_dir / "calendars" / "day.txt"
    inst_path = qlib_dir / "instruments" / "all.txt"
    calendar = [x.strip() for x in cal_path.read_text().splitlines() if x.strip()]
    print(f"数据目录: {qlib_dir}")
    print(f"现有日历: {calendar[0]} ~ {calendar[-1]} ({len(calendar)} 天)")
    backup = qlib_dir / "_backup" / time.strftime("%Y%m%d_%H%M%S")

    for code in symbols:
        print(f"\n{'=' * 66}\n{code}\n{'=' * 66}")
        raw = fetch_raw(tx_symbol(code))
        if not len(raw):
            print("  ❌ 取数失败，跳过")
            continue
        print(f"  不复权 {len(raw)} 根 | {raw.index[0].date()} ~ {raw.index[-1].date()}")

        feat = qlib_dir / "features" / code.lower()
        close_p, vol_p, fac_p = (feat / "close.day.bin", feat / "volume.day.bin", feat / "factor.day.bin")
        if not close_p.exists():
            print("  ⚠ 该票还没有 .bin，本脚本只做追加，请先用 update_symbol_bins.py 全量建仓")
            continue

        si, closes = read_bin(close_p)
        old_last_idx = si + len(closes) - 1
        old_last_date = calendar[old_last_idx]
        if old_last_date not in raw.index:
            print(f"  ⚠ 现有末日 {old_last_date} 不在腾讯数据里，放弃（可能需要全量重写）")
            continue

        _, vols = read_bin(vol_p)
        _, facs = read_bin(fac_p)
        k_price = float(closes[-1]) / float(raw.loc[pd.Timestamp(old_last_date), "close"])
        k_vol = float(vols[-1]) / (float(raw.loc[pd.Timestamp(old_last_date), "volume"]) * 100.0)
        factor_last = float(facs[-1])
        print(f"  现有末日 {old_last_date}: close {closes[-1]:.4f} factor {factor_last:.6f}")
        print(f"  校准: 价格 ×{k_price:.6f}（应≈factor）  成交量 ×{k_vol:.6f}")

        new_dates = [d for d in raw.index if d.strftime("%Y-%m-%d") > old_last_date]
        if args.until:
            until = pd.Timestamp(args.until)
            dropped = [d for d in new_dates if d > until]
            new_dates = [d for d in new_dates if d <= until]
            if dropped:
                print(f"  ⏭ 按 --until {args.until} 跳过 {len(dropped)} 天（未收盘）: "
                      f"{[d.strftime('%Y-%m-%d') for d in dropped]}")
        if not new_dates:
            print("  ✅ 已是最新，无需追加")
            continue
        print(f"  待追加 {len(new_dates)} 天: {[d.strftime('%Y-%m-%d') for d in new_dates]}")

        if args.dry_run:
            print("  [dry-run] 不落盘")
            continue

        # 1) 日历补日期
        cal_set = set(calendar)
        add_dates = [d.strftime("%Y-%m-%d") for d in new_dates if d.strftime("%Y-%m-%d") not in cal_set]
        if add_dates:
            calendar = sorted(cal_set | set(add_dates))
            cal_path.write_text("\n".join(calendar) + "\n")
            print(f"  日历已更新 → {len(calendar)} 天，末日 {calendar[-1]}")

        # 2) 追加各字段（缺失日填 NaN）
        cal_idx = {d: i for i, d in enumerate(calendar)}
        new_start = old_last_idx + 1
        span = calendar[new_start:]
        span_idx = pd.to_datetime(span)

        def build(series_scaled, existing):
            s = pd.Series(np.nan, index=span_idx, dtype=float)
            s.loc[series_scaled.index] = series_scaled.values
            return np.concatenate([existing, s.values])

        adj = raw.loc[new_dates]
        fields = {
            "open": build(adj["open"] * k_price, read_bin(feat / "open.day.bin")[1]),
            "high": build(adj["high"] * k_price, read_bin(feat / "high.day.bin")[1]),
            "low": build(adj["low"] * k_price, read_bin(feat / "low.day.bin")[1]),
            "close": build(adj["close"] * k_price, closes),
            "volume": build(adj["volume"] * 100.0 * k_vol, vols),
            "factor": np.concatenate([facs, np.full(len(span), factor_last)]),
            "change": None,
        }
        cl = fields["close"]
        prev = np.concatenate([[cl[len(closes) - 1]], cl[len(closes):]])[: len(cl) - len(closes)]
        chg = np.concatenate([read_bin(feat / "change.day.bin")[1], np.zeros(len(span))])
        for i in range(len(closes), len(cl)):
            p = cl[i - 1]
            chg[i] = 0.0 if (np.isnan(p) or np.isnan(cl[i]) or p == 0) else cl[i] / p - 1
        fields["change"] = chg

        backup.mkdir(parents=True, exist_ok=True)
        shutil.copytree(feat, backup / code.lower(), dirs_exist_ok=True)
        for name, vals in fields.items():
            write_bin(feat / f"{name}.day.bin", vals, si)
        print(f"  ✅ 追加完成 → 现共 {len(fields['close'])} 天，末日 {calendar[si + len(fields['close']) - 1]}")

        # 3) instruments 结束日
        if inst_path.exists():
            lines = inst_path.read_text().splitlines()
            out, hit = [], False
            for ln in lines:
                p = ln.split("\t")
                if len(p) >= 3 and p[0].upper() == code:
                    p[2] = calendar[si + len(fields["close"]) - 1]
                    out.append("\t".join(p))
                    hit = True
                else:
                    out.append(ln)
            if not hit:
                out.append(f"{code}\t{calendar[si]}\t{calendar[si + len(fields['close']) - 1]}")
            inst_path.write_text("\n".join(out) + "\n")

    print(f"\n{'=' * 66}\n完成。日历末日: {calendar[-1]}")
    if backup.exists():
        print("备份:", backup)

    # 自动刷新数据状态文档，保证「数据更新到哪天」这个记录不过期
    try:
        import subprocess
        import sys as _sys

        subprocess.run([_sys.executable, str(Path(__file__).with_name("write_data_status.py")),
                        "--dir", str(qlib_dir)], check=False)
    except Exception as e:  # noqa: BLE001
        print(f"（状态文档刷新失败，不影响数据：{type(e).__name__}）")


if __name__ == "__main__":
    main()
