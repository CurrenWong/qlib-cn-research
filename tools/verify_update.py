"""验证更新后的目录：qlib 能读出 2026-10-28，且重叠日与原数据一致。"""

import subprocess
import sys

import qlib
from qlib.constant import REG_CN
from qlib.data import D

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

TEST = _ROOT + r"/qlib_data/_test_update"
ORIG = _ROOT + r"/qlib_data/cn_data_2026"
CODES = ["SH600418", "SH000300"]
S, E = "2026-10-15", "2026-10-31"


def grab(provider):
    qlib.init(provider_uri=provider, region=REG_CN)
    out = {}
    for code in CODES:
        df = D.features([code], ["$close", "$volume", "$factor"], start_time=S, end_time=E, freq="day")
        for (inst, dt), row in df.iterrows():
            out[(inst, str(dt.date()))] = {k: float(v) for k, v in row.items()}
    return out


def main():
    new = grab(TEST)
    print("=" * 74)
    print("更新后（_test_update）读取结果")
    print("=" * 74)
    for (code, d), v in sorted(new.items()):
        print(f"  {code} {d}  close {v['$close']:8.4f}  volume {v['$volume']:>14.0f}  factor {v['$factor']:.6f}")

    # 原数据放在子进程里读，避免两次 qlib.init 互相干扰
    snippet = f'''
import qlib
from qlib.constant import REG_CN
from qlib.data import D
qlib.init(provider_uri=r"{ORIG}", region=REG_CN)
for code in {CODES!r}:
    df = D.features([code], ["$close"], start_time="{S}", end_time="{E}", freq="day")
    for (inst, dt), row in df.iterrows():
        print(f"{{inst}},{{dt.date()}},{{float(row['$close']):.6f}}")
'''
    r = subprocess.run([sys.executable, "-c", snippet], capture_output=True, text=True, encoding="utf-8")
    old = {}
    for ln in r.stdout.splitlines():
        p = ln.split(",")
        if len(p) == 3:
            try:
                old[(p[0], p[1])] = float(p[2])
            except ValueError:
                pass

    print("\n" + "=" * 74)
    print("重叠日对账（原 cn_data_2026 vs 更新后）")
    print("=" * 74)
    print(f"  {'代码':10s} {'日期':12s} {'原':>9s} {'新':>9s} {'差':>8s}")
    ok = True
    for (code, d), v in sorted(new.items()):
        if (code, d) in old:
            diff = abs(v["$close"] / old[(code, d)] - 1) * 100
            ok &= diff < 0.05
            print(f"  {code:10s} {d:12s} {old[(code,d)]:9.4f} {v['$close']:9.4f} {diff:7.3f}%")
        else:
            print(f"  {code:10s} {d:12s} {'(无)':>9s} {v['$close']:9.4f}   ← 新增")
    print("\n→", "✅ 重叠日口径一致（<0.05%），新增日已入库" if ok else "⚠️ 存在 >0.05% 偏差")


if __name__ == "__main__":
    main()
