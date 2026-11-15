"""侦察：数据最新日期、沪深300成分股规模、字段可用性。"""

from pathlib import Path

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

ROOT = Path(_ROOT)
DATA = ROOT / "qlib_data" / "cn_data_2026"


def main():
    cal = (DATA / "calendars" / "day.txt").read_text().split()
    print("日历最后 5 天:", cal[-5:], "总交易日", len(cal))

    rows = [l.split("\t") for l in
            (DATA / "instruments" / "csi300.txt").read_text().splitlines() if l.strip()]
    print("csi300 区间行数:", len(rows))
    for d in ("2026-10-30", "2026-10-27", "2025-12-31", "2023-12-29", "2020-12-31", "2015-12-31"):
        act = sorted({r[0] for r in rows if r[1] <= d <= r[2]})
        print(f"{d}  成分股 {len(act):3d}  例: {act[:3]}")

    latest = sorted({r[0] for r in rows if r[1] <= cal[-1] <= r[2]})
    (ROOT / "projects" / "csi300_lgbm").mkdir(parents=True, exist_ok=True)
    out = ROOT / "projects" / "csi300_lgbm" / "universe_latest.txt"
    out.write_text("\n".join(latest) + "\n", encoding="utf-8")
    print(f"已写出最新成分 {len(latest)} 只 -> {out}")

    # 字段可用性抽查
    import qlib
    from qlib.data import D
    qlib.init(provider_uri=str(DATA), region="cn", expression_cache=None, dataset_cache=None)
    df = D.features(["SH600000", "SH000300"], ["$close", "$volume", "$factor", "$open", "$high", "$low", "$vwap"],
                    start_time="2026-10-26", end_time="2026-10-30", freq="day")
    print(df.tail(8).to_string())


if __name__ == "__main__":
    main()
