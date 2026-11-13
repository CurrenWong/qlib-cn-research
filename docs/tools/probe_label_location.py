"""探针：handler 内部 _infer / _learn 两套数据的列差异（标签到底在哪）。"""

import qlib
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH


def main():
    qlib.init(provider_uri=r"D:\Project\qlib\qlib_data\cn_data", region=REG_CN)

    h = Alpha158(
        instruments="csi300",
        start_time="2018-01-01",
        end_time="2020-08-01",
        fit_start_time="2018-01-01",
        fit_end_time="2019-12-31",
        infer_processors=[],
        learn_processors=[],
    )
    print("handler._infer 列数:", len(h._infer.columns), "| 含LABEL:", [c for c in h._infer.columns if "LABEL" in str(c)])
    print("handler._learn  列数:", len(h._learn.columns), "| 含LABEL:", [c for c in h._learn.columns if "LABEL" in str(c)])
    print("handler._data   列数:", len(h._data.columns), "| 含LABEL:", [c for c in h._data.columns if "LABEL" in str(c)])
    print("inferred 列类型:", h._infer.columns[:3].tolist(), "…")

    ds = DatasetH(handler=h, segments={"train": ("2018-01-01", "2019-12-31")})
    df = ds.prepare("train")
    print("prepare(默认) 列数:", len(df.columns), "| 含LABEL:", [c for c in df.columns if "LABEL" in str(c)])
    print("prepare index:", df.index.names)

    df2 = ds.prepare("train", data_key="learn")
    print("prepare(learn) 列数:", len(df2.columns), "| 含LABEL:", [c for c in df2.columns if "LABEL" in str(c)])

    # 单列取用到底行不行
    for cs in (["LABEL0"], "LABEL0", ["KMID"], ["KMID", "LABEL0"]):
        try:
            x = ds.prepare("train", col_set=cs)
            print(f"col_set={cs!r} → OK, 列={list(x.columns)}")
        except Exception as e:
            print(f"col_set={cs!r} → {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
