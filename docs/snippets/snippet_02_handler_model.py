"""片段 2：特征工程 + 模型 —— 内置 handler / DatasetH / LGBModel

⚠️ Windows 必读：任何调用 D.features / handler 的脚本都要有
   `if __name__ == "__main__":` 保护（qlib 会用 joblib 起子进程）。

运行：..\\.venv\\Scripts\\python.exe snippets\\snippet_02_handler_model.py
"""

import qlib
from qlib.constant import REG_CN
from qlib.contrib.data.handler import Alpha158
from qlib.contrib.model.gbdt import LGBModel
from qlib.data.dataset import DatasetH

PROVIDER_URI = r"D:\Project\qlib\qlib_data\cn_data"


def main():
    qlib.init(provider_uri=PROVIDER_URI, region=REG_CN)

    # ---- 1. 内置因子库 Alpha158（158 个技术因子）----
    handler = Alpha158(
        instruments="csi300",
        start_time="2018-01-01",
        end_time="2020-08-01",
        fit_start_time="2018-01-01",
        fit_end_time="2019-12-31",
        infer_processors=[],       # 演示用：关掉推理期归一化
        learn_processors=[],
    )

    # ---- 2. 组装数据集：train / valid / test 三段 ----
    dataset = DatasetH(
        handler=handler,
        segments={
            "train": ("2018-01-01", "2019-12-31"),
            "valid": ("2019-01-01", "2019-12-31"),
            "test": ("2020-01-01", "2020-08-01"),
        },
    )

    # ⚠ 关键 1：handler 内部列是 MultiIndex —— ("feature","KMID") / ("label","LABEL0")
# ⚠ 关键 2：col_set 在列被压平之前生效，所以必须用元组写，写 ["LABEL0"] 会 KeyError
    tr = dataset.prepare("train", col_set=[("label", "LABEL0")])
    print(f"[数据集] train shape={tr.shape}")
    print("  列名：", [repr(c) for c in tr.columns])
    print("  ⚠ 注意：handler 数据的索引层级是 (datetime, instrument)，")
    print("          而 D.features 返回的是 (instrument, datetime)，两者不同！")

    # ---- 3. 训练模型（early stopping 用 valid 段）----
    model = LGBModel(
        loss="mse",
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        num_boost_round=1000,
        early_stopping_rounds=50,
    )
    model.fit(dataset)
    # qlib 的 LGBModel 把真正的 booster 放在 .model 上，早停轮次在它身上
    best_it = getattr(getattr(model, "model", None), "best_iteration_", None)
    print(f"\n[模型] 训练完成，best_iteration={best_it}")

    # ---- 4. 预测 ----
    pred = model.predict(dataset, segment="test")
    print(f"[预测] type={type(pred).__name__}，index={pred.index.names}，长度={len(pred)}")
    print(pred.head())

    # ---- 5. 特征重要度 ----
    imp = model.get_feature_importance("gain")
    # ⚠ 重要度 index 是 "Column_N"，不是因子名，要自己映射回 handler 的列名
    cols = dataset.handler.get_cols()
    imp.index = cols[: len(imp)]
    print("\n[重要度 Top10]")
    print(imp.sort_values(ascending=False).head(10).to_string())

    # ---- 6. 用 IC 评估预测力 ----
    # 默认 col_set="__all" 时列会被压平成字符串列名，可以直接 df["LABEL0"]
    test_df = dataset.prepare("test")
    ic = pred.corr(test_df["LABEL0"])
    print(f"\n[IC] test 段预测分数与标签的相关系数 = {ic:.4f}")
    print(f"[列名] Alpha158 共 158 个特征列 + LABEL0，例如：{list(test_df.columns[:4])}")


if __name__ == "__main__":
    main()
