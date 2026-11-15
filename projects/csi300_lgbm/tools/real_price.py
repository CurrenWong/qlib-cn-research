"""真实价格核算：qlib 的 $close 是"原始价 × 复权因子"之后的连续序列，
不能直接当成交价用。这里取 $factor，还原真实市场价，再算一手金额与最小资金。"""

import json
from pathlib import Path

import qlib
from qlib.data import D

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

ROOT = Path(_ROOT)
DATA = ROOT / "qlib_data" / "cn_data_2026"
RES = ROOT / "projects" / "csi300_lgbm" / "results"


def main():
    d = json.loads((RES / "picks_K20.json").read_text(encoding="utf-8"))
    syms = [p["symbol"] for p in d["picks"]]
    qlib.init(provider_uri=str(DATA), region="cn")
    df = D.features(syms, ["$close", "$factor"], start_time="2026-10-30",
                    end_time="2026-10-30", freq="day")
    close = df["$close"].unstack(level=0).iloc[0]
    factor = df["$factor"].unstack(level=0).iloc[0]
    rows = []
    for p in d["picks"]:
        s = p["symbol"]
        c, f = float(close[s]), float(factor[s])
        real = c / f
        rows.append((p["rank"], s, p["name"], c, f, real, real * 100, p["board"]))
    total = sum(r[6] for r in rows)
    print(f"{'#':>2} {'代码':9s} {'名称':6s} {'qlib close':>11s} {'factor':>9s} "
          f"{'真实价':>8s} {'一手':>9s}")
    for r in rows:
        print(f"{r[0]:>2} {r[1]:9s} {r[2]:6s} {r[3]:11.3f} {r[4]:9.5f} {r[5]:8.2f} {r[6]:9,.0f}")
    print(f"\n20 只各买一手合计 {total:,.0f} 元（等权最小可执行资金）")
    for cap in (100_000, 300_000, 1_000_000, 3_000_000):
        per = cap / len(rows)
        lots = sum(max(1, int(per // (r[5] * 100))) for r in rows)
        print(f"  本金 {cap/1e4:6.0f} 万 → 每只 {per:8,.0f} 元，合计约 {lots} 手，"
              f"实际投资 {sum(max(1,int(per//(r[5]*100)))*r[5]*100 for r in rows)/1e4:7.1f} 万")
    out = {"as_of": "2026-10-30", "total_one_lot": total,
           "rows": [{"rank": r[0], "symbol": r[1], "name": r[2], "qlib_close": r[3],
                     "factor": r[4], "real_price": r[5], "one_lot": r[6], "board": r[7]}
                    for r in rows]}
    (RES / "picks_K20_price.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    print("已写出 results/picks_K20_price.json")


if __name__ == "__main__":
    main()
