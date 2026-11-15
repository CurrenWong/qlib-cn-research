"""新旧两份数据对账：同一只票、同一区间，收益率是否可比。

如果两个源只是复权基准不同（整体乘一个常数），收益率应完全一致；
若收益率不同，说明复权处理（分红送股）不一致，跨源结论不能直接对比。
"""

import subprocess
import sys

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

OLD = _ROOT + r"/qlib_data/cn_data"
NEW = _ROOT + r"/qlib_data/cn_data_2026"
PY = _ROOT + r"/.venv/Scripts/python.exe"

SNIPPET = r'''
import sys, json
import qlib
from qlib.constant import REG_CN
from qlib.data import D
provider = sys.argv[1]
qlib.init(provider_uri=provider, region=REG_CN)
out = {}
for code in ["SH600418", "SH000300"]:
    df = D.features([code], ["$close", "$factor"], start_time="2015-01-01", end_time="2026-12-31", freq="day")
    if not len(df):
        out[code] = {}
        continue
    d = df.xs(code, level="instrument")
    out[code] = {
        "close": {str(k.date()): float(v) for k, v in d["$close"].dropna().items()},
        "factor": {str(k.date()): float(v) for k, v in d["$factor"].dropna().items()},
    }
print("JSON_START" + json.dumps(out))
'''


def load(provider):
    r = subprocess.run([PY, "-c", SNIPPET, provider], capture_output=True, text=True, encoding="utf-8")
    for line in r.stdout.splitlines():
        if line.startswith("JSON_START"):
            import json

            return json.loads(line[len("JSON_START"):])
    print("失败:", r.stdout[-500:], r.stderr[-800:])
    return {}


def main():
    old = load(OLD)
    new = load(NEW)
    if not old or not new:
        sys.exit(1)

    for code in ["SH600418", "SH000300"]:
        oc = old[code]["close"]
        nc = new[code]["close"]
        of = old[code].get("factor", {})
        nf = new[code].get("factor", {})
        common = sorted(set(oc) & set(nc))
        print("=" * 74)
        print(f"{code}  共同交易日 {len(common)}  旧源区间 {min(oc)}~{max(oc)}  新源区间 {min(nc)}~{max(nc)}")
        print("=" * 74)

        if not common:
            print("  无重叠")
            continue

        # 关键区间收益率对比
        for label, s, e in [("2019-01-02~2020-09-24", "2019-01-02", "2020-09-24"),
                            ("2017-01-03~2018-12-28", "2017-01-03", "2018-12-28"),
                            ("2015-01-05~2016-12-30", "2015-01-05", "2016-12-30")]:
            oc0 = next((v for k, v in sorted(oc.items()) if k >= s), None)
            oc1 = next((v for k, v in sorted(oc.items(), reverse=True) if k <= e), None)
            nc0 = next((v for k, v in sorted(nc.items()) if k >= s), None)
            nc1 = next((v for k, v in sorted(nc.items(), reverse=True) if k <= e), None)
            if None in (oc0, oc1, nc0, nc1):
                print(f"  {label}: 数据缺失，跳过")
                continue
            ro = oc1 / oc0 - 1
            rn = nc1 / nc0 - 1
            print(f"  {label}:  旧 {ro:+8.2%}   新 {rn:+8.2%}   差 {rn - ro:+.2%}")

        # 价格比值稳定性（判断是否只差一个常数）
        ratios = [oc[d] / nc[d] for d in common if nc[d]]
        import statistics

        mean_r = statistics.mean(ratios)
        cv = statistics.pstdev(ratios) / mean_r if mean_r else 0
        print(f"  旧/新 收盘价比值：均值 {mean_r:.4f}  变异系数 {cv:.4%}  "
              f"（接近 0 = 仅基准不同；明显 >0 = 复权路径不一致）")
        if of and nf:
            common_f = sorted(set(of) & set(nf))
            if common_f:
                print(f"  复权因子示例 旧 {of[common_f[-1]]:.6f} / 新 {nf[common_f[-1]]:.6f} (末日)")
        print()


if __name__ == "__main__":
    main()
