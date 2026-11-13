"""探针：确认 handler 列索引是 MultiIndex，col_set 必须用元组。"""

import qlib
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH


def main():
    qlib.init(provider_uri=r"D:\Project\qlib\qlib_data\cn_data", region=REG_CN)
    h = Alpha158(
        instruments="csi300", start_time="2018-01-01", end_time="2020-08-01",
        fit_start_time="2018-01-01", fit_end_time="2019-12-31",
        infer_processors=[], learn_processors=[],
    )
    ds = DatasetH(handler=h, segments={"train": ("2018-01-01", "2019-12-31")})

    df = ds.prepare("train")
    print("prepare() columns 前 3 个 repr:", [repr(c) for c in df.columns[:3]])
    print("prepare() columns 类型:", type(df.columns).__name__, "| nlevels:", getattr(df.columns, "nlevels", 1))

    raw = ds.handler.fetch(slice("2018-01-01", "2019-12-31"))
    print("handler.fetch() columns 前 3 个 repr:", [repr(c) for c in raw.columns[:3]])

    for cs in ([("label", "LABEL0")], [("feature", "KMID"), ("label", "LABEL0")]):
        try:
            x = ds.prepare("train", col_set=cs)
            print(f"col_set={cs} → OK, 列={[repr(c) for c in x.columns]}")
        except Exception as e:
            print(f"col_set={cs} → {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
