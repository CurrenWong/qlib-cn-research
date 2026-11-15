"""清理下载残留（用户明确授权的三处）。删前打印，删后核对。"""

import os
import shutil

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

TARGETS = [
    _ROOT + r"/data/qlib_bin_2026-10-27.tar.gz",   # 46MB 单线程残片
    _ROOT + r"/data/parts_2026-10-27",             # 16 个分段残片
    str(_Path.home() / "Downloads" / "qlib_bin.tar.gz"),  # 543MB 原始压缩包（已解压）
]

KEEP = [
    (_ROOT + r"/projects/jac_600418/results_2026",
     "第 12.5 节「选型不稳定」的证据（新数据上重跑 walk-forward 的结果）"),
    (_ROOT + r"/data/qlib_data_cn_1d_latest.zip",
     "主数据集的原始压缩包（187MB，可作备份；重下很慢）"),
    (_ROOT + r"/qlib_data/cn_data_2026",
     "已解压的新数据集，正在使用"),
]


def size_of(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def main():
    print("=" * 70)
    print("待删除")
    print("=" * 70)
    freed = 0
    for p in TARGETS:
        if os.path.exists(p):
            sz = size_of(p)
            kind = "目录" if os.path.isdir(p) else "文件"
            print(f"  [删除] {kind} {p}  ({sz/1048576:.1f} MB)")
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            freed += sz
        else:
            print(f"  [跳过] 不存在 {p}")

    print(f"\n共释放 {freed/1048576:.1f} MB")

    print("\n" + "=" * 70)
    print("保留（未删）")
    print("=" * 70)
    for p, why in KEEP:
        if os.path.exists(p):
            print(f"  [保留] {p}  ({size_of(p)/1048576:.1f} MB)\n        理由：{why}")

    print("\n" + "=" * 70)
    print("核对结果")
    print("=" * 70)
    for p in TARGETS:
        print(f"  {'❌ 仍存在' if os.path.exists(p) else '✅ 已删除'}  {p}")

    print("\nD 盘剩余空间：")
    import shutil as sh

    t = sh.disk_usage("D:\\")
    print(f"  D: {t.free/1024**3:.0f} GB 可用 / {t.total/1024**3:.0f} GB")
    c = sh.disk_usage("C:\\")
    print(f"  C: {c.free/1024**3:.1f} GB 可用 / {c.total/1024**3:.0f} GB")


if __name__ == "__main__":
    main()
