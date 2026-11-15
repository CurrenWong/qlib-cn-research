"""带断点续传的 qlib 数据集下载器（走系统证书库，兼容本地代理）。"""

import os
import sys
import time

import requests

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[1])

URL = "https://github.com/SunsetWolf/qlib_dataset/releases/download/v2/qlib_data_cn_1d_latest.zip"
DEST = _ROOT + r"/data/qlib_data_cn_1d_latest.zip"

os.makedirs(os.path.dirname(DEST), exist_ok=True)

total = None
for attempt in range(1, 6):
    have = os.path.getsize(DEST) if os.path.exists(DEST) else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    try:
        with requests.get(URL, headers=headers, stream=True, timeout=(30, 120), allow_redirects=True) as r:
            if r.status_code == 416:  # already complete
                print("server says range not satisfiable -> assume complete")
                break
            r.raise_for_status()
            cr = r.headers.get("Content-Range", "")
            if "/" in cr:
                total = int(cr.split("/")[-1])
            elif r.status_code == 200:
                total = int(r.headers.get("Content-Length", 0)) or None
                have = 0
            mode = "ab" if r.status_code == 206 and have else "wb"
            print(f"attempt={attempt} status={r.status_code} resume_from={have} total={total} mode={mode}", flush=True)
            done = 0 if mode == "wb" else have
            t0 = time.time()
            with open(DEST, mode) as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
                    done += len(chunk)
                    if total and done % (1024 * 1024 * 8) < 1024 * 256:
                        el = time.time() - t0
                        rate = (done - have) / el / 1024 if el > 0 else 0
                        pct = done / total * 100
                        eta = (total - done) / max(rate * 1024, 1)
                        print(f"  {pct:5.1f}%  {done/1048576:7.1f}/{total/1048576:.1f} MB  {rate:6.0f} KB/s  eta={eta/60:4.1f}min", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"attempt={attempt} failed: {type(e).__name__}: {e}", flush=True)
        time.sleep(3)
        continue
    size = os.path.getsize(DEST)
    if total is None or size >= total:
        print(f"download finished: {size} bytes", flush=True)
        break
    print(f"short read {size}/{total}, retrying...", flush=True)

size = os.path.getsize(DEST)
print(f"final size={size} total={total}")
sys.exit(0 if (total is None or size == total) else 2)
