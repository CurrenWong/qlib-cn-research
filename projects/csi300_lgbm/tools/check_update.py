"""核对追加结果（v2）：校准系数 vs 既有 factor；找出末日落后的成分股。"""

import re
from collections import Counter
from pathlib import Path

import numpy as np

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

LOG = Path(_ROOT + r"/projects/csi300_lgbm/results/update_data.log")
DATA = Path(_ROOT + r"/qlib_data/cn_data_2026")
cal = (DATA / "calendars" / "day.txt").read_text().split()

txt = LOG.read_text(encoding="utf-8", errors="replace").replace("\r", "")
blocks = re.split(r"=+\s*\n", txt)
bad, ok, failed, skipped = [], 0, [], []
for b in blocks:
    m_sym = re.search(r"\b(SH|SZ)\d{6}\b", b)
    m_fac = re.search(r"factor ([\d.]+)", b)
    m_k = re.search(r"价格 ×([\d.]+)", b)
    if not (m_sym and m_fac and m_k):
        continue
    fac, k = float(m_fac.group(1)), float(m_k.group(1))
    sym = m_sym.group(0)
    if "追加完成" in b:
        ok += 1
        if abs(k - fac) / max(fac, 1e-9) > 0.005:
            bad.append((sym, fac, round(k, 6)))
    elif "取数失败" in b:
        failed.append(sym)
    elif "跳过" in b or "⚠" in b:
        skipped.append((sym, [l.strip() for l in b.splitlines() if "⚠" in l or "跳过" in l]))
print(f"追加成功 {ok}；校准异常(>0.5%) {len(bad)}；取数失败 {len(failed)}；跳过 {len(skipped)}")
for x in bad[:8]:
    print("   校准异常:", x)
for x in failed[:8]:
    print("   取数失败:", x)
for x in skipped[:8]:
    print("   跳过:", x)


def end_date(sym):
    p = DATA / "features" / sym.lower() / "close.day.bin"
    size = p.stat().st_size
    with open(p, "rb") as f:
        start = int(np.frombuffer(f.read(4), dtype="<f")[0])
    return cal[start + (size - 4) // 4 - 1]


latest = (Path(_ROOT + r"/projects/csi300_lgbm/data/csi300_latest.txt")
          .read_text(encoding="utf-8").split())
lag = [(s, end_date(s)) for s in latest if end_date(s) != "2026-10-30"]
print("\n300 只中末日不是 2026-10-30 的:", lag)

# 抽样核对：追加后的 close(前复权) 与腾讯不复权价 × factor 是否一致
import requests
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
for sym in ["SH600000", "SZ002241", "SH601857", "SH600519"]:
    code = ("sh" if sym.startswith("SH") else "sz") + sym[2:]
    try:
        r = requests.get("https://web.ifzq.gtimg.cn/appstock/app/kline/kline",
                         params={"param": f"{code},day,,,10"}, headers=UA, timeout=20)
        rows = r.json()["data"][code]["day"]
        raw = {x[0]: float(x[2]) for x in rows}
        p = DATA / "features" / sym.lower() / "close.day.bin"
        with open(p, "rb") as f:
            start = int(np.frombuffer(f.read(4), dtype="<f")[0])
        arr = np.frombuffer(p.read_bytes()[4:], dtype="<f")
        vals = {cal[start + i]: float(arr[i]) for i in range(len(arr))}
        pf = DATA / "features" / sym.lower() / "factor.day.bin"
        with open(pf, "rb") as f:
            fs = int(np.frombuffer(f.read(4), dtype="<f")[0])
        farr = np.frombuffer(pf.read_bytes()[4:], dtype="<f")
        fac = {cal[fs + i]: float(farr[i]) for i in range(len(farr))}
        msg = []
        for d in ["2026-10-28", "2026-10-29", "2026-10-30"]:
            if d in raw and d in vals:
                expect = raw[d] * fac.get(d, np.nan)
                msg.append(f"{d}: qlib {vals[d]:.4f} vs 腾讯×factor {expect:.4f} "
                           f"(差 {abs(vals[d]-expect)/max(expect,1e-9)*100:.3f}%)")
        print(f"{sym}: " + " | ".join(msg))
    except Exception as e:                                     # noqa: BLE001
        print(f"{sym}: 校验失败 {e}")
