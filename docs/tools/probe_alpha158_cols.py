"""探针：Alpha158 handler 的输出列名（必须加 __main__ 保护，否则 Windows 上无限 fork）。"""

import qlib
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])


def main():
    qlib.init(provider_uri=_ROOT + r"/qlib_data/cn_data", region=REG_CN)

    h = Alpha158(
        instruments="csi300",
        start_time="2018-01-01",
        end_time="2020-08-01",
        fit_start_time="2018-01-01",
        fit_end_time="2019-12-31",
        infer_processors=[],
        learn_processors=[],
    )
    ds = DatasetH(handler=h, segments={"train": ("2018-01-01", "2019-12-31")})
    df = ds.prepare("train")
    cols = list(df.columns)
    print("总列数:", len(cols))
    print("前 15 列:", cols[:15])
    print("后 10 列:", cols[-10:])
    print("含 LABEL 的列:", [c for c in cols if "LABEL" in str(c)])
    print("含 close 的列:", [c for c in cols if "close" in str(c).lower()][:10])
    print("shape:", df.shape)
    print("index names:", df.index.names)


if __name__ == "__main__":
    main()
