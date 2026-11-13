"""多线程分段下载 chenditc/investment_data 的 qlib 数据集（日更版 2026-10-27）。

为什么分段：单连接实测只有 27 KB/s（ETA 5 小时），GitHub release 资源按连接限速；
拆成 N 段并发通常能到 200-400 KB/s。下载完仍用 manifest 里的 SHA256 校验，完整性有保证。

特性：
  - 每段独立断点续传（重跑同一条命令即可继续）
  - 复用已存在的单文件部分下载（把它切成前两段，不浪费）
  - 全部完成后拼接 + 校验 SHA256
"""

import hashlib
import os
import shutil
import sys
import threading
import time

import requests

TAG = "2026-10-27"
BASE = f"https://github.com/chenditc/investment_data/releases/download/{TAG}"
URL = f"{BASE}/qlib_bin.tar.gz"
MANIFEST_URL = f"{BASE}/qlib_bin.manifest.json"

DATA_DIR = r"D:\Project\qlib\data"
DEST = os.path.join(DATA_DIR, f"qlib_bin_{TAG}.tar.gz")
PARTS_DIR = os.path.join(DATA_DIR, f"parts_{TAG}")
N_PARTS = 16


def load_expectations():
    r = requests.get(MANIFEST_URL, timeout=60, headers={"User-Agent": "qlib-fetch"})
    r.raise_for_status()
    j = r.json()
    return int(j["archive_size_bytes"]), j["archive_sha256"].split(":")[-1]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024 * 8), b""):
            h.update(b)
    return h.hexdigest()


def segment_bounds(size, n):
    step = size // n
    out = []
    for i in range(n):
        start = i * step
        end = size - 1 if i == n - 1 else (i + 1) * step - 1
        out.append((i, start, end))
    return out


def reuse_existing_single_file(size, bounds):
    """把之前单文件下载的残片切给前几段，避免重复下载。"""
    if not os.path.exists(DEST):
        return
    have = os.path.getsize(DEST)
    if have == 0 or have >= size:
        return
    print(f"[复用] 已有单文件残片 {have/1048576:.1f} MB，切分到各段 ...")
    with open(DEST, "rb") as src:
        for i, start, end in bounds:
            part_len = end - start + 1
            p = os.path.join(PARTS_DIR, f"part{i:02d}")
            if os.path.exists(p) and os.path.getsize(p) >= part_len:
                continue
            if start >= have:
                break
            src.seek(start)
            chunk = src.read(part_len)
            if not chunk:
                break
            with open(p, "wb") as f:
                f.write(chunk)
            print(f"   part{i:02d}: 复用 {len(chunk)/1048576:.1f} MB")
    print("[复用] 完成")


def dl_part(i, start, end, size):
    part_len = end - start + 1
    p = os.path.join(PARTS_DIR, f"part{i:02d}")
    for attempt in range(1, 31):
        have = os.path.getsize(p) if os.path.exists(p) else 0
        if have >= part_len:
            return
        headers = {"User-Agent": "qlib-fetch", "Range": f"bytes={start + have}-{end}"}
        try:
            with requests.get(URL, headers=headers, stream=True, timeout=(30, 90)) as r:
                if r.status_code not in (200, 206):
                    r.raise_for_status()
                with open(p, "ab") as f:
                    for chunk in r.iter_content(chunk_size=256 * 1024):
                        if chunk:
                            f.write(chunk)
        except Exception as e:  # noqa: BLE001
            if attempt % 5 == 0:
                print(f"   part{i:02d} 第 {attempt} 次重试: {type(e).__name__}", flush=True)
            time.sleep(2)


def main():
    size, exp_sha = load_expectations()
    print(f"目标: {size:,} bytes ({size/1048576:.1f} MB)  sha256={exp_sha[:16]}...")
    os.makedirs(PARTS_DIR, exist_ok=True)
    bounds = segment_bounds(size, N_PARTS)
    reuse_existing_single_file(size, bounds)

    def worker(b):
        dl_part(b[0], b[1], b[2], size)

    t0 = time.time()
    threads = [threading.Thread(target=worker, args=(b,), daemon=True) for b in bounds]
    for t in threads:
        t.start()

    while any(t.is_alive() for t in threads):
        time.sleep(20)
        got = 0
        for i, start, end in bounds:
            p = os.path.join(PARTS_DIR, f"part{i:02d}")
            got += min(os.path.getsize(p) if os.path.exists(p) else 0, end - start + 1)
        el = time.time() - t0
        rate = got / el / 1024 if el > 0 else 0
        eta = (size - got) / max(got / el, 1) / 60 if got else 999
        print(f"  {got/size*100:5.1f}%  {got/1048576:7.1f}/{size/1048576:.1f} MB  "
              f"{rate:6.0f} KB/s  eta={eta:5.1f}min", flush=True)

    got = sum(min(os.path.getsize(os.path.join(PARTS_DIR, f"part{i:02d}")) if
                  os.path.exists(os.path.join(PARTS_DIR, f"part{i:02d}")) else 0, e - s + 1)
              for i, s, e in bounds)
    if got < size:
        print(f"\n未完成 {got:,}/{size:,} → 重跑本命令续传")
        sys.exit(2)

    print("\n拼接各段 ...")
    with open(DEST, "wb") as out:
        for i, s, e in bounds:
            with open(os.path.join(PARTS_DIR, f"part{i:02d}"), "rb") as f:
                shutil.copyfileobj(f, out, 1024 * 1024 * 8)
    print(f"拼接完成 {os.path.getsize(DEST):,} bytes")

    print("校验 SHA256 ...")
    got_sha = sha256_of(DEST)
    ok = got_sha == exp_sha
    print("  got     :", got_sha)
    print("  expected:", exp_sha)
    print("→", "✅ 校验通过" if ok else "❌ 校验失败")
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
