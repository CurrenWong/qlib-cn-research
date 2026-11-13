"""探针：模型特征重要度返回的是 Column_N，怎么映射回因子名。"""

import qlib
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset import DatasetH


def main():
    qlib.init(provider_uri=r"D:\Project\qlib\qlib_data\cn_data", region=REG_CN)
    h = Alpha158(
        instruments="csi300", start_time="2018-01-01", end_time="2020-08-01",
        fit_start_time="2018-01-01", fit_end_time="2019-12-31",
        infer_processors=[], learn_processors=[],
    )
    ds = DatasetH(handler=h, segments={
        "train": ("2018-01-01", "2019-12-31"),
        "valid": ("2019-01-01", "2019-12-31"),
        "test": ("2020-01-01", "2020-08-01"),
    })
    m = LGBModel(loss="mse", learning_rate=0.05, num_leaves=31, num_boost_round=50, early_stopping_rounds=50)
    m.fit(ds)

    imp = m.get_feature_importance("gain")
    print("重要度 index 前 5:", list(imp.index[:5]))

    cols = ds.handler.get_cols()
    print("handler.get_cols() 长度:", len(cols), "前 5:", cols[:5])

    df = ds.prepare("test")
    print("prepare 列前 5:", list(df.columns[:5]))

    # 两种映射方式
    try:
        print("handler.get_cols('__all') 前 5:", ds.handler.get_cols("__all")[:5])
    except Exception as e:
        print("get_cols('__all') 失败:", e)

    imp2 = imp.copy()
    try:
        imp2.index = cols
        print("映射后前 5:", list(imp2.sort_values(ascending=False).index[:5]))
    except Exception as e:
        print("映射失败:", e)


if __name__ == "__main__":
    main()
