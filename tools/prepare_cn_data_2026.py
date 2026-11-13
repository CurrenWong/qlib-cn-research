"""收到 qlib_bin.tar.gz 之后的一键处理：校验 → 看结构 → 解压 → 验证。

用法：
    .venv\\Scripts\\python.exe tools\\prepare_cn_data_2026.py                 # 全流程
    .venv\\Scripts\\python.exe tools\\prepare_cn_data_2026.py --verify-only   # 只校验 + 看结构
    .venv\\Scripts\\python.exe tools\\prepare_cn_data_2026.py --src <别的路径>

它会：
  1. 用 manifest 里的 SHA256 + 大小校验压缩包（不通过直接退出，绝不拿坏数据）
  2. 打印 tar 内顶层结构（确认是 calendars/features/instruments 还是多一层目录）
  3. 解压到 D:\\Project\\qlib\\qlib_data\\cn_data_2026（已存在则跳过解压）
  4. 用 qlib 打开验证：日历区间、600418 行数与最后价格、instruments 数量
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile

import requests

TAG = "2026-10-27"
BASE = f"https://github.com/chenditc/investment_data/releases/download/{TAG}"
MANIFEST_URL = f"{BASE}/qlib_bin.manifest.json"

DATA_DIR = r"D:\Project\qlib\data"
DEFAULT_SRC = os.path.join(DATA_DIR, f"qlib_bin_{TAG}.tar.gz")
TARGET = r"D:\Project\qlib\qlib_data\cn_data_2026"

PROVIDER = r"D:\Project\qlib\qlib_data\cn_data_2026"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024 * 8), b""):
            h.update(b)
    return h.hexdigest()


def verify(src):
    print("=" * 70)
    print("步骤 1/4：校验压缩包")
    print("=" * 70)
    if not os.path.exists(src):
        print(f"❌ 文件不存在: {src}")
        print("   下载链接：", f"{BASE}/qlib_bin.tar.gz")
        return False
    size = os.path.getsize(src)
    print(f"文件: {src}")
    print(f"大小: {size:,} bytes ({size/1048576:.1f} MB)")

    try:
        j = requests.get(MANIFEST_URL, timeout=60, headers={"User-Agent": "qlib-fetch"}).json()
        exp_size = int(j["archive_size_bytes"])
        exp_sha = j["archive_sha256"].split(":")[-1]
        print(f"清单: tag={j.get('release_tag')} 目标交易日={j.get('target_trade_date')}")
        print(f"  期望大小 {exp_size:,} | 期望 sha256 {exp_sha[:16]}...")
        if size != exp_size:
            print(f"❌ 大小不符（差 {exp_size - size:,} bytes）→ 没下完")
            return False
        print("  计算 SHA256（约需 10-30 秒）...")
        got = sha256_of(src)
        if got != exp_sha:
            print(f"❌ SHA256 不匹配\n   got={got}\n   exp={exp_sha}")
            return False
        print("✅ 大小 + SHA256 校验通过")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ 无法取 manifest（{type(e).__name__}: {e}），退化为只校验 gzip 完整性")
        try:
            with tarfile.open(src, "r:gz") as tf:
                n = sum(1 for _ in tf)
            print(f"✅ gzip/tar 结构正常，{n} 个条目")
            return True
        except Exception as e2:  # noqa: BLE001
            print(f"❌ 压缩包损坏: {e2}")
            return False


def show_structure(src):
    print("\n" + "=" * 70)
    print("步骤 2/4：查看内部结构")
    print("=" * 70)
    tops = {}
    with tarfile.open(src, "r:gz") as tf:
        for m in tf:
            top = m.name.split("/")[0]
            tops[top] = tops.get(top, 0) + 1
    for k, v in sorted(tops.items(), key=lambda x: -x[1])[:8]:
        print(f"  {k:40s} {v} 个条目")
    has_root_dirs = all(k in ("calendars", "features", "instruments") for k in tops if k)
    print(f"\n  → 顶层直接是 calendars/features/instruments: {has_root_dirs}")
    return list(tops.keys())


def extract(src, tops):
    print("\n" + "=" * 70)
    print("步骤 3/4：解压")
    print("=" * 70)
    if os.path.exists(os.path.join(TARGET, "calendars")):
        print(f"目标已存在，跳过解压: {TARGET}")
        return
    os.makedirs(TARGET, exist_ok=True)
    # 用系统 tar（Windows 10+ 自带 bsdtar，比 python tarfile 快）
    strip = "" if ("calendars" in tops) else "--strip-components=1"
    cmd = f'tar -xzf "{src}" -C "{TARGET}" {strip}'
    print("执行:", cmd)
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        print("系统 tar 失败，改用 python tarfile ...")
        with tarfile.open(src, "r:gz") as tf:
            tf.extractall(TARGET)
    print("解压完成 →", TARGET)


def validate():
    print("\n" + "=" * 70)
    print("步骤 4/4：用 qlib 验证数据")
    print("=" * 70)
    sys.path.insert(0, r"D:\Project\qlib")
    import pandas as pd

    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=PROVIDER, region=REG_CN)

    cal = pd.DatetimeIndex(D.calendar(freq="day"))
    print(f"日历: {cal[0].date()} ~ {cal[-1].date()}  共 {len(cal)} 个交易日")

    for code in ["SH600418", "SH000300"]:
        df = D.features([code], ["$close", "$volume"], start_time="2018-01-01", end_time="2030-01-01", freq="day")
        if len(df):
            d = df.xs(code, level="instrument")
            print(f"{code}: {len(d)} 行 | {d.index[0].date()} ~ {d.index[-1].date()} "
                  f"| 末价 {float(d['$close'].iloc[-1]):.3f}")
        else:
            print(f"{code}: ❌ 无数据")

    for mkt in ["all", "csi300"]:
        try:
            lst = D.list_instruments(D.instruments(mkt), start_time="2026-01-01", end_time="2026-10-27", as_list=True)
            print(f"{mkt}: {len(lst)} 只")
        except Exception as e:  # noqa: BLE001
            print(f"{mkt}: 读取失败 {type(e).__name__}: {e}")


def cleanup_hint():
    print("\n" + "=" * 70)
    print("可选清理（我不主动删，等你确认）")
    print("=" * 70)
    for p in [os.path.join(DATA_DIR, f"parts_{TAG}"), DEFAULT_SRC]:
        if os.path.exists(p):
            print(f"  {p}")


def main():
    src = DEFAULT_SRC
    if "--src" in sys.argv:
        src = sys.argv[sys.argv.index("--src") + 1]

    if not verify(src):
        sys.exit(1)
    tops = show_structure(src)
    if "--verify-only" in sys.argv:
        print("\n(--verify-only，到此为止)")
        return
    extract(src, tops)
    validate()
    cleanup_hint()


if __name__ == "__main__":
    main()
