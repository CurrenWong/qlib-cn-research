"""下载 chenditc/investment_data 的 qlib 数据集（日更版，2026-10-27）。

特性：
  - HTTP Range 断点续传（被 timeout 杀掉后重跑同一个命令即可续传）
  - 下载完校验大小 + SHA256（值取自该 release 的 manifest.json）
  - 输出进度与控制台，可反复调用直到 complete

用法：
    .venv\\Scripts\\python.exe tools\\fetch_investment_data.py          # 下载（可重复调用续传）
    .venv\\Scripts\\python.exe tools\\fetch_investment_data.py --check   # 只校验现有文件
"""

import hashlib
import os
import sys
import time

import requests

TAG = "2026-10-27"
BASE = f"https://github.com/chenditc/investment_data/releases/download/{TAG}"
URL = f"{BASE}/qlib_bin.tar.gz"
MANIFEST_URL = f"{BASE}/qlib_bin.manifest.json"
DEST = rf"D:\Project\qlib\data\qlib_bin_{TAG}.tar.gz"


def load_expectations():
    """从 release 的 manifest.json 读大小与 SHA256（避免手抄错）。"""
    r = requests.get(MANIFEST_URL, timeout=60, headers={"User-Agent": "qlib-fetch"})
    r.raise_for_status()
    j = r.json()
    sha = j["archive_sha256"].split(":")[-1]
    size = int(j["archive_size_bytes"])
    print(f"manifest: tag={j.get('release_tag')} size={size:,} sha256={sha[:16]}...")
    return size, sha, j


EXPECTED_SIZE = 569_575_728
EXPECTED_SHA256 = "PLACEHOLDER"


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024 * 8)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def check(exp_size: int = None, exp_sha: str = None) -> bool:
    exp_size = exp_size or EXPECTED_SIZE
    exp_sha = exp_sha or EXPECTED_SHA256
    if not os.path.exists(DEST):
        print("文件不存在:", DEST)
        return False
    size = os.path.getsize(DEST)
    print(f"大小: {size:,} / {exp_size:,} bytes  ({size / 1024 / 1024:.1f} MB)")
    if size != exp_size:
        print("→ 大小不符，尚未下完")
        return False
    print("→ 大小正确，校验 SHA256 ...")
    got = sha256_of(DEST)
    print("  got     :", got)
    print("  expected:", exp_sha)
    ok = got == exp_sha
    print("→", "✅ SHA256 校验通过" if ok else "❌ SHA256 不匹配（文件损坏，需重下）")
    return ok


def download() -> int:
    exp_size, exp_sha, _ = load_expectations()
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    t_start = time.time()

    for attempt in range(1, 11):
        have = os.path.getsize(DEST) if os.path.exists(DEST) else 0
        if have >= exp_size:
            print("下载已完成（大小达标）")
            break
        headers = {"User-Agent": "qlib-fetch"}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with requests.get(URL, headers=headers, stream=True, timeout=(30, 120)) as r:
                if r.status_code == 416:
                    print("server: range not satisfiable → 视为已完成")
                    break
                r.raise_for_status()
                mode = "ab" if (r.status_code == 206 and have) else "wb"
                done = 0 if mode == "wb" else have
                print(f"[attempt {attempt}] status={r.status_code} 从 {have/1048576:.1f} MB 续传，模式={mode}", flush=True)
                last = time.time()
                with open(DEST, mode) as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        now = time.time()
                        if now - last > 15:
                            last = now
                            rate = done / (now - t_start) / 1024 if now > t_start else 0
                            pct = done / exp_size * 100
                            eta = (exp_size - done) / max(done / (now - t_start), 1) / 60
                            print(f"  {pct:5.1f}%  {done/1048576:7.1f}/{exp_size/1048576:.1f} MB  "
                                  f"{rate:6.0f} KB/s  eta={eta:4.1f}min", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[attempt {attempt}] 失败: {type(e).__name__}: {e}", flush=True)
            time.sleep(3)
            continue
        if os.path.getsize(DEST) >= exp_size:
            break

    size = os.path.getsize(DEST) if os.path.exists(DEST) else 0
    print(f"\n当前大小 {size:,} / {exp_size:,} bytes")
    if size >= exp_size:
        check(exp_size, exp_sha)
        return 0
    print("尚未完成 → 重新执行本命令即可续传")
    return 2


if __name__ == "__main__":
    if "--check" in sys.argv:
        exp_size, exp_sha, _ = load_expectations()
        sys.exit(0 if check(exp_size, exp_sha) else 1)
    sys.exit(download())
