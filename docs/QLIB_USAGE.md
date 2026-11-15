# Qlib 使用手册（v0.9.8 / Windows 实测版）

> 本机环境：`<repo>`，venv Python 3.12.12，pyqlib **0.9.8**（git `5435523`），数据 `qlib_data\cn_data`（2007-01-04 ~ 2020-09-25）
> 所有 API 签名、参数、字段口径均从**已安装的包**里扒出来核对过；`snippets\` 下三份代码**实跑通过**。
> 配套：环境安装见 [../README.md](../README.md)，完整策略案例见 [../projects/jac_600418/README.md](../projects/jac_600418/README.md)。

---

## 0. 五层架构：先建立心智模型

```
                          ┌─────────────────────────────────────┐
   实验管理层  qlib.workflow│ R / Recorder / mlruns / RecordTemp  │
                          └───────────────┬─────────────────────┘
   策略回测层  qlib.backtest│ Strategy → Executor → Exchange → Account → Report
                          └───────────────┬─────────────────────┘
   模型层      qlib.contrib │ LGBModel / XGBModel / LinearModel / 自定义
   .model                 └───────────────┬─────────────────────┘
   数据集层    qlib.data.   │ DatasetH ← DataHandlerLP ← DataLoader
   dataset                └───────────────┬─────────────────────┘
   数据层      qlib.data    │ D.calendar / D.instruments / D.features（表达式引擎）
                          └─────────────────────────────────────┘
```

一句话分工：**数据层出 DataFrame → 数据集层切成 train/valid/test → 模型层出预测分数 → 回测层把分数变成仓位和成交 → 实验层把一切存档**。

---

## 1. 30 秒上手

```python
import qlib
from qlib.constant import REG_CN
from qlib.data import D

qlib.init(provider_uri=r"qlib_data\cn_data", region=REG_CN)

df = D.features(
    ["SH600000"],
    ["$close", "Mean($close,20)/$close-1"],   # 表达式引擎
    start_time="2020-01-01", end_time="2020-03-31", freq="day",
)
print(df.tail())
```

⚠️ **Windows 必须加 `if __name__ == "__main__":`**，见第 8 节第 1 条。

---

## 2. 数据层

### 2.1 `qlib.init`

```python
qlib.init(
    provider_uri="~/.qlib/qlib_data/cn_data",  # 数据目录（可以是 str/dict，dict 支持多频率）
    region="cn",                                # cn / us，决定交易日历、涨跌停、交易单位
    # 常用可选项：
    # expression_cache="DiskExpressionCache",  # 表达式结果缓存目录
    # dataset_cache="DiskDatasetCache",        # DatasetD 缓存
    # kernels=1,                               # 并行进程数
    # redis_host/redis_port,                   # 用 Redis 缓存表达式
)
```

初始化只做一次，重复调用会警告。初始化后 `C` 全局配置里就有 `data_path`。

### 2.2 `D` 的四个方法（全部核实）

| 方法 | 返回 | 说明 |
|---|---|---|
| `D.calendar(start_time=None, end_time=None, freq="day", future=False)` | `numpy.ndarray[datetime64]` | 交易日历；**不是** DatetimeIndex，用 `.year` 等方法前先 `pd.DatetimeIndex(...)` |
| `D.instruments(market="all")` | `dict{instrument: [(start, end), ...]}` | 构造股票池配置对象，传给 `list_instruments` / `features` |
| `D.list_instruments(instruments, start_time=None, end_time=None, as_list=False, freq="day")` | `list` 或 `dict` | `as_list=True` → 纯代码列表；`False` → `{代码: [(起, 止)]}`（**不是** DataFrame） |
| `D.features(instruments, fields, start_time, end_time, freq="day", disk_cache=False, inst_processors=[])` | `DataFrame`，索引 `(instrument, datetime)` | 主入口：拿特征/标签 |

内置 market：`all` / `csi100` / `csi300` / `csi500`（本数据只有这 4 个 instruments 文件）。也可以直接传代码列表 `["SH600000","SH600519"]`。

```python
inst = D.instruments("csi300")
members = D.list_instruments(inst, start_time="2020-01-01", end_time="2020-03-31", as_list=True)
# → ['SH600000', 'SH600004', ..., ] 共 300 只
```

### 2.3 `$` 字段

| 字段 | 含义 | | 字段 | 含义 |
|---|---|---|---|---|
| `$open` | 开盘价 | | `$volume` | 成交量（股） |
| `$high` | 最高价 | | `$factor` | 复权因子 |
| `$low` | 最低价 | | `$change` | 涨跌幅 |
| `$close` | 收盘价（已复权） | | `$vwap` | 均价 |
| `$amount` / `$money` | 成交额（视数据而定） | | | |

本数据每只股票目录下只有：`open/high/low/close/volume/change/factor` 的 `.day.bin`。

### 2.4 表达式引擎算子（`qlib.data.ops`，全部核实）

**算术 / 逻辑**：`Add Sub Mul Div Power`、`Greater Ge Gt Less Le Lt Eq Ne And Or Not If(cond, a, b)`

**逐元素**：`Abs Log Sign`

**滚动（单序列）**：

| 算子 | 含义 | 算子 | 含义 |
|---|---|---|---|
| `Ref(A, N)` | N 日前的值（**N 可为负 = 未来**） | `Mean(A, N)` | 滚动均值 |
| `Sum(A, N)` | 滚动求和 | `Std(A, N)` / `Var(A, N)` | 滚动标准差/方差 |
| `Max(A, N)` / `Min(A, N)` | 滚动极值 | `Med(A, N)` | 滚动中位数 |
| `Mad(A, N)` | 平均绝对偏差 | `Skew(A, N)` / `Kurt(A, N)` | 偏度/峰度 |
| `Rank(A, N)` | 滚动百分位排名 | `Quantile(A, N, q)` | 滚动分位数 |
| `Slope(A, N)` | 滚动斜率 | `Rsquare(A, N)` | 滚动 R² |
| `Resi(A, N)` | 滚动回归残差 | `Delta(A, N)` | N 日差分 |
| `EMA(A, N)` / `WMA(A, N)` | 指数/加权均线 | `Count(A, N)` | 条件计数 |
| `IdxMax(A, N)` / `IdxMin(A, N)` | 极值位置 | | |

**双序列**：`Corr(A, B, N)` 滚动相关、`Cov(A, B, N)` 滚动协方差

**特殊**：`Mask(A, instrument)`、`ChangeInstrument(instrument, A)`、`TResample(A, freq, func)`

书写要点：
- 函数参数里可以写算术：`Mean(($high-$low)/$close, 14)` ✅ 实测可解析
- 比较/条件：`If($close>Mean($close,20), 1, 0)`
- 标签用未来函数：`Ref($close,-2)/Ref($close,-1)-1` = 「明天收盘买、后天收盘卖」的收益
- 字段名带 `$`，函数名首字母大写，逗号后可有空格

### 2.5 索引层级：两个地方不一样（重要）

| 来源 | 索引顺序 |
|---|---|
| `D.features(...)` | **`(instrument, datetime)`** |
| `DatasetH.prepare(...)`（handler 数据） | **`(datetime, instrument)`** |

跨用的处理方式：
```python
flat = df.xs("SH600000", level="instrument")              # 去 instrument 层
one  = df.loc[(slice(None), "SH600000"), :]                # 保留两层取单票
df2  = df.swaplevel().sort_index()                         # 换层级顺序
```
qlib 的 `SignalWCache` 内部会 `convert_index_format(level="datetime")` 自动把 datetime 换到第 0 层，所以信号给 `backtest()` 时两种顺序都能吃。

### 2.6 缓存

```python
D.features(..., disk_cache=True)        # 单次调用落盘缓存（data.py 的 dataset_cache）
D.calendar(...), D.instruments(...)     # 进程内 lru_cache，同一进程只读一次
qlib.init(expression_cache="DiskExpressionCache")   # 表达式级缓存，重复算同一表达式会快很多
```

### 2.7 数据准备脚本

```cmd
:: 下载官方数据（会下到目标目录并解压）
.venv\Scripts\python.exe qlib-src\scripts\get_data.py qlib_data --target_dir D:\...\cn_data --region cn
::   name 可选 qlib_data / qlib_data_simple；interval 可选 1d / 1min
::   注意：官方脚本不支持断点续传，网络差时自己用 Range 续传更省事

:: 把自己的 csv 转成 qlib .bin
.venv\Scripts\python.exe qlib-src\scripts\dump_bin.py dump_all --csv_path <csv目录> --qlib_dir <输出目录>

:: 数据体检
.venv\Scripts\python.exe qlib-src\scripts\check_data_health.py check_data --qlib_dir <目录>
```

`.bin` 目录结构：
```
cn_data\
├── calendars\day.txt          每行一个交易日
├── instruments\all.txt        每行 "代码\t起始日\t结束日"
└── features\sh600000\
    ├── close.day.bin          首 4 字节 float32 存起始索引，之后是 float32 值
    ├── volume.day.bin
    └── factor.day.bin
```

---

## 3. 数据集层（特征工程）

### 3.1 内置因子库

| Handler | 因子数 | 说明 |
|---|---|---|
| `Alpha158` | **158 特征 + `LABEL0`** | K 线形态（KMID/KLEN/KUP/KLOW/KSFT 及 2 阶）+ ROC + MA + STD + BETA + RSQR + RESI + MAX/MIN/QTLU + RANK + RSV + IMAX/IMIN + CORR/CORD + CNTP/CNTN/CNTD + SUMP/SUMN/SUMD + VMA/VSTD/WVMA/VSUMP/VSUMN/VSUMD，共 10 组 |
| `Alpha360` | 360 | 最近 60 天 OHLCV 的原始序列（深度学习用） |

Alpha158 实测输出：`159` 列，索引 `(datetime, instrument)`，特征名如 `KMID, KLEN, KMID2, KUP, ..., VSUMD60`，标签列 `LABEL0`。

### 3.2 `DatasetH`：切样本

```python
from qlib.data.dataset import DatasetH
from qlib.contrib.data.handler import Alpha158

handler = Alpha158(
    instruments="csi300",
    start_time="2018-01-01", end_time="2020-08-01",
    fit_start_time="2018-01-01", fit_end_time="2019-12-31",   # 归一化统计量只用这段拟合
)
dataset = DatasetH(handler=handler, segments={
    "train": ("2018-01-01", "2019-12-31"),
    "valid": ("2019-01-01", "2019-12-31"),
    "test":  ("2020-01-01", "2020-08-01"),
})
```

`dataset.prepare(segments, col_set="__all", data_key="infer", **kwargs)`：

| 参数 | 可选值 | 说明 |
|---|---|---|
| `col_set` | `"__all"` / `"__raw"` / **元组列表** | ⚠️ 指定列必须写 `[("label","LABEL0")]` / `[("feature","KMID")]` |
| `data_key` | `"infer"`（默认）/ `"learn"` / `"raw"` | infer = 处理后的特征；learn = 特征+标签（训练用） |

> `TSDatasetH` 是同样 API 的时序版，多一个 `step_len`（每条样本含过去 N 天），给 RNN/Transformer 用。

### 3.3 处理器链（processor）

`DataHandlerLP` 的两条链：
- `infer_processors`：**推理期**（含 test）施加
- `learn_processors`：**训练期**施加（通常多一个 `DropnaLabel` 丢掉无标签样本）

常用处理器：

| 处理器 | 作用 |
|---|---|
| `DropnaLabel` | 丢标签 NaN 的行（几乎必加） |
| `RobustZScoreNorm(fields_group="feature", clip_outlier=True)` | 截面稳健标准化 |
| `CSZScoreNorm(fields_group="label")` | 标签截面标准化 |
| `CSRankNorm(fields_group="label")` | 标签转截面排名（0~1），降异常值影响 |
| `Fillna(fields_group="feature")` | 缺失值填充 |
| `ZScoreNorm` / `MinMaxNorm` | 常规定标 |
| `DropCol` | 丢列 |

⚠️ 标签处理（`DropnaLabel` / `CSRankNorm`）要放 `learn_processors`，放 `infer_processors` 会报错或没效果。

### 3.4 自定义 handler

```python
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset.processor import DropnaLabel, RobustZScoreNorm, Fillna

class MyHandler(DataHandlerLP):
    def __init__(self, instruments="csi300", start_time=None, end_time=None,
                 fit_start_time=None, fit_end_time=None,
                 infer_processors=(), learn_processors=(), **kwargs):
        infer_processors = [
            RobustZScoreNorm(fit_start_time=fit_start_time, fit_end_time=fit_end_time, fields_group="feature"),
            Fillna(fields_group="feature"),
        ]
        learn_processors = [DropnaLabel()] + list(infer_processors)
        data_loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (self.get_feature_config(), self.get_column_names()),
                    "label": (["Ref($close,-2)/Ref($close,-1)-1"], ["LABEL0"]),
                },
                "freq": "day",
            },
        }
        super().__init__(instruments=instruments, start_time=start_time, end_time=end_time,
                         data_loader=data_loader,
                         infer_processors=infer_processors, learn_processors=learn_processors, **kwargs)

    def get_feature_config(self):
        return [
            "$close/Ref($close,5)-1",
            "Mean($close,20)/$close-1",
            "Std($close,20)/Mean($close,20)",
            "$volume/Mean($volume,20)-1",
        ]

    def get_column_names(self):
        return ["mom5", "ma20_dev", "vol20", "volz20"]
```

---

## 4. 模型层

`qlib.model` 只导出基类 `Model`；具体模型都在 `qlib.contrib.model`：

| 类 | module_path | 说明 |
|---|---|---|
| `LGBModel` | `qlib.contrib.model.gbdt` | LightGBM（最常用），`loss="mse"` 或 `"binary"`，参数直接透传 lgb |
| `XGBModel` / `CatBoostModel` | `qlib.contrib.model.xgboost` / `.catboost_model` | 需另装 xgboost / catboost |
| `LinearModel` / `Ridge` / `Lasso` / `LinearRegression` | `qlib.contrib.model.linear` | 线性族（⚠️ 模块名是 `linear` 不是 `linear_model`） |
| `DEnsembleModel` | `qlib.contrib.model.double_ensemble` | DoubleEnsemble |
| PyTorch 系列（`ALSTM`/`GRU`/`Transformer`/`TFT`…） | `qlib.contrib.model.pytorch_*` | 需另装 torch |

统一接口：
```python
model.fit(dataset)                                  # 用 train/valid 段，自动早停
pred = model.predict(dataset, segment="test")       # Series，MultiIndex(instrument, datetime)
imp  = model.get_feature_importance("gain")         # ⚠ index 是 Column_N
model.model.best_iteration_                         # qlib 的 LGBModel 把 booster 放在 .model 上
```

自定义模型只需实现两个方法：

```python
from qlib.model.base import Model

class MyModel(Model):
    def fit(self, dataset):
        df = dataset.prepare("train", col_set=["feature", "label"], data_key="learn")
        X, y = df["feature"], df["label"]
        ...
        return self
    def predict(self, dataset):
        df = dataset.prepare("test", col_set="feature")
        return pd.Series(self._predict(df.values), index=df.index)
```

自定义模块要被 qlib 的 yaml 引用，需要 `module_path` 可导入（把项目目录加进 `sys.path` 或做成包）。

---

## 5. 回测层（核心）

### 5.1 一张图看懂调用链

```
backtest(start, end, strategy, executor, benchmark, account, exchange_kwargs)
   ├─ create_account_instance()   →  Account(初始资金, 基准配置)
   ├─ get_exchange(**exchange_kwargs) → Exchange(成本/涨跌停/撮合价)
   ├─ init_instance_by_config(strategy) → Strategy
   ├─ init_instance_by_config(executor)→ SimulatorExecutor
   └─ backtest_loop():
        每个交易日:
          1. strategy.generate_trade_decision()   ← 用【上一日】的信号
          2. executor.execute(decision)           ← 当日撮合，改仓位
          3. account.update_portfolio_metrics()   ← 记净值/成本/换手
        ↓
      (portfolio_dict, indicator_dict)
```

### 5.2 `backtest()` 完整签名（实测）

```python
from qlib.backtest import backtest

portfolio_dict, indicator_dict = backtest(
    start_time="2020-01-01",
    end_time="2020-08-01",
    strategy={...},            # dict 或已实例化对象
    executor={...},            # dict 或已实例化对象
    benchmark="SH000300",
    account=1_000_000,
    exchange_kwargs={...},
    pos_type="Position",
)
```

**返回值**：
- `portfolio_dict[key]` → `(report_df, positions)`，`key` 是 `"{}{}".format(*Freq.parse("day"))` = **`"1day"`**
- `indicator_dict[key]` → `(indicator_df, Indicator对象)`，含 `ffr`(成交率) / `pa`(价格优势) / `pos`

### 5.3 `report` 字段口径（必须记住）

| 列 | 含义 | 口径 |
|---|---|---|
| `account` | 总资产（现金+股票市值） | 时点值 |
| `cash` | 现金 | 时点值 |
| `value` | 股票市值 | 时点值 |
| `return` | 当期收益率 | 当期值 |
| `turnover` | 当期换手率 | **当期值**（0.95 = 95%） |
| `total_turnover` | 累计换手金额 | **累计值** ⚠️ 不能再 `.sum()` |
| `cost` | 当期成本占账户比例 | 当期值 |
| `total_cost` | 累计成本金额 | **累计值** ⚠️ 不能再 `.sum()` |
| `bench` | 基准当期收益率 | 当期值 |

正确取法：
```python
total_cost     = report["total_cost"].iloc[-1]          # 累计成本（元）
ann_turnover   = report["total_turnover"].iloc[-1] / account / years
exposure       = (report["value"] / report["account"]).mean()
rebalance_days = int((report["turnover"].fillna(0) > 0).sum())
```

### 5.4 `Exchange` 参数（成本与撮合）

| 参数 | 默认 | 说明 |
|---|---|---|
| `freq` | `"day"` | 撮合频率 |
| `codes` | `"all"` | **强烈建议传具体代码列表**，见第 8 节第 5 条 |
| `deal_price` | `None` | `"close"` / `"open"` / `"vwap"`，或 `(买价, 卖价)` 元组 |
| `open_cost` / `close_cost` | 0.0015 / 0.0025 | 买入/卖出费率（卖出含印花税） |
| `min_cost` | 5.0 | 单笔最低佣金（元） |
| `limit_threshold` | `None`→C 默认 | 涨跌停阈值，主板 `0.095`，创业板/科创板 `0.195` |
| `volume_threshold` | `None` | 成交量限制，**必须是 dict 或 tuple**，传数字会 AssertionError |
| `impact_cost` | 0.0 | 冲击成本 |
| `extra_quote` | `None` | 外部行情 DataFrame（补充字段） |
| `trade_unit` | `None` | 交易单位（A 股 100 股），在 `kwargs` 里传 |

### 5.5 内置策略

| 策略 | module_path | 适用 |
|---|---|---|
| `TopkDropoutStrategy(topk, n_drop, method_sell, method_buy, hold_thresh, only_tradable, forbid_all_trade_at_limit)` | `qlib.contrib.strategy` | 多标的、按分数选前 K 只，每日换 n_drop 只 |
| `WeightStrategyBase` | `qlib.contrib.strategy` | **基类**：实现 `generate_target_weight_position()` 返回 `{代码: 权重}` |
| `BaseSignalStrategy(risk_degree=0.95)` | `qlib.contrib.strategy` | 基类：只管信号，不管下单 |
| `EnhancedIndexingStrategy(riskmodel_root, market, ...)` | `qlib.contrib.strategy` | 带风险模型约束的指数增强（需要风险模型数据 + cvxpy） |
| `SoftTopkStrategy(max_sold_weight, trade_impact_limit, ...)` | `qlib.contrib.strategy.cost_control` | 带成本控制的 TopK |
| `OrderGenWOInteract` / `OrderGenWInteract` | `qlib.contrib.strategy.order_generator` | 权重→订单生成器（不交互/交互行情） |

### 5.6 自定义策略（单标的择时的完整模板）

```python
from typing import Dict
import pandas as pd
from qlib.contrib.strategy.signal_strategy import WeightStrategyBase


class MyTimingStrategy(WeightStrategyBase):
    """分数 > 阈值就满仓，否则空仓。"""

    def __init__(self, *, signal=None, threshold: float = 0.0, target_weight: float = 1.0, **kwargs):
        super().__init__(signal=signal, **kwargs)      # signal: MultiIndex(instrument, datetime)
        self.threshold = threshold
        self.target_weight = target_weight

    def generate_target_weight_position(self, score, current, trade_start_time, trade_end_time) -> Dict[str, float]:
        # score: pd.Series，index 是 instrument（qlib 已按日期 resample 好）
        return {sid: self.target_weight for sid, s in score.items()
                if s is not None and not pd.isna(s) and float(s) > self.threshold}
```

挂到回测里：
```python
strategy = {
    "class": "MyTimingStrategy",
    "module_path": "my_module",          # 需要 sys.path 能 import 到
    "kwargs": {"signal": signal, "threshold": 0.001, "target_weight": 1.0},
}
```

### 5.7 时间轴语义（最容易搞错）

```
T 日：算因子 → 出信号 score[T]           （只用 T 日及之前的数据）
T+1 日：strategy 决策（读 score[T]）→ 当日收盘价成交
T+2 日：下一次决策，按 score[T+1] 调仓
```

所以：
- 标签 `Ref($close,-2)/Ref($close,-1)-1` 在 T 日的值 = `close[T+2]/close[T+1]-1`，**正好**是 T 日信号对应的持仓收益 ✅
- `TopkDropoutStrategy` 内部 `get_step_time(trade_step, shift=1)` 就是取上一日
- 如果你在策略里还要用别的序列（如均线），**必须对齐到信号日**，不能用成交日的数据

### 5.8 绩效指标（qlib 不直接给，自己算）

```python
nav = report["account"] / report["account"].iloc[0]
ret = nav.pct_change().dropna()
years   = len(ret) / 252
ann     = nav.iloc[-1] ** (1 / years) - 1
vol     = ret.std() * 252 ** 0.5
sharpe  = (ann - 0.02) / vol
mdd     = (nav / nav.cummax() - 1).min()
calmar  = ann / abs(mdd)

# 相对基准
ex      = ret - report["bench"].reindex(ret.index).fillna(0)
te      = ex.std() * 252 ** 0.5
ann_ex  = (1 + ex.mean()) ** 252 - 1
ir      = ann_ex / te
```

`qlib.contrib.evaluate` 里还有 `risk_analysis(returns)` / `indicator_analysis`，输出 `mean/std/annualized_return/information_ratio/max_drawdown`，但它把超额收益也叫 information_ratio，口径和上面不同，注意区分。

---

## 6. 实验管理层

### 6.1 `R` + Recorder（代码方式）

```python
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, SigAnaRecord, PortAnaRecord

with R.start(experiment_name="my_exp"):
    R.log_params(**{"lr": 0.05, "topk": 50})
    model.fit(dataset)
    R.save_objects(**{"pred.pkl": model.predict(dataset, segment="test")})
    R.save_objects(**{"model.pkl": model})

    rec = R.get_recorder()
    SignalRecord(model, dataset, rec).generate()      # 存 pred/label
    SigAnaRecord(rec).generate()                      # 存 IC/Rank IC/ICIR
    PortAnaRecord(rec).generate()                     # 跑回测，存 report/analysis/indicator
```

产物落在 `./mlruns/<实验id>/<recorder id>/artifacts/`。`R.log_metrics` / `R.list_metrics` / `R.load_object("pred.pkl")` 可读回。

### 6.2 `qrun` + yaml（推荐，配置即实验）

```yaml
qlib_init:
    provider_uri: "qlib_data/cn_data"
    region: cn
market: &market csi300
benchmark: &benchmark SH000300
data_handler_config: &data_handler_config
    start_time: 2008-01-01
    end_time: 2020-08-01
    fit_start_time: 2008-01-01
    fit_end_time: 2014-12-31
    instruments: *market
port_analysis_config: &port_analysis_config
    strategy:
        class: TopkDropoutStrategy
        module_path: qlib.contrib.strategy
        kwargs: {signal: <PRED>, topk: 50, n_drop: 5}
    backtest:
        start_time: 2017-01-01
        end_time: 2020-08-01
        account: 100000000
        benchmark: *benchmark
        exchange_kwargs: {limit_threshold: 0.095, deal_price: close, open_cost: 0.0005, close_cost: 0.0015, min_cost: 5}
task:
    model:
        class: LGBModel
        module_path: qlib.contrib.model.gbdt
        kwargs: {loss: mse, learning_rate: 0.2, num_leaves: 210, num_threads: 16}
    dataset:
        class: DatasetH
        module_path: qlib.data.dataset
        kwargs:
            handler: {class: Alpha158, module_path: qlib.contrib.data.handler, kwargs: *data_handler_config}
            segments:
                train: [2008-01-01, 2014-12-31]
                valid: [2015-01-01, 2016-12-31]
                test:  [2017-01-01, 2020-08-01]
    record:
        - {class: SignalRecord, module_path: qlib.workflow.record_temp, kwargs: {model: <MODEL>, dataset: <DATASET>}}
        - {class: SigAnaRecord, module_path: qlib.workflow.record_temp, kwargs: {ana_long_short: False, ann_scaler: 252}}
        - {class: PortAnaRecord, module_path: qlib.workflow.record_temp, kwargs: {config: *port_analysis_config}}
```

```cmd
.venv\Scripts\python.exe qlib-src\qlib\cli\run.py my_config.yaml
:: 或指定实验名/存储位置
.venv\Scripts\python.exe qlib-src\qlib\cli\run.py my_config.yaml --experiment_name exp1 --uri_folder mlruns
```

占位符：`<MODEL>` / `<DATASET>` / `<PRED>` 由 `qrun` 自动替换。

---

## 7. 常用 CLI 命令速查

```cmd
:: 下载 / 转换 / 体检数据
python qlib-src\scripts\get_data.py qlib_data --target_dir <dir> --region cn
python qlib-src\scripts\dump_bin.py dump_all --csv_path <csv> --qlib_dir <dir>
python qlib-src\scripts\check_data_health.py check_data --qlib_dir <dir>

:: 跑 yaml 工作流
python qlib-src\qlib\cli\run.py <config.yaml>

:: 官方基准示例（LightGBM + Alpha158，约 5 分钟）
python qlib-src\qlib\cli\run.py qlib-src\examples\benchmarks\LightGBM\workflow_config_lightgbm_Alpha158.yaml

:: 看实验结果
python -c "from qlib.workflow import R; print(R.list_experiments())"
```

---

## 8. 踩坑清单（全部本机实测）

### ① Windows：没有 `__main__` 保护 → 无限 fork 💥

```
RuntimeError: An attempt has been made to start a new process before the current process
has finished its bootstrapping phase.
```

原因：`D.features` / handler 通过 joblib 起子进程（spawn），子进程会重新 import 主模块，模块级代码又触发一次 → 雪崩。
**规则：任何调用 `D.features`、`Alpha158(...)`、`DatasetH.prepare` 的脚本，入口必须包在 `if __name__ == "__main__": main()` 里。**（单标的取数有时侥幸不崩，别赌）

### ② `col_set` 必须写元组

```python
dataset.prepare("train", col_set=["LABEL0"])              # ❌ KeyError: "['LABEL0'] not in index"
dataset.prepare("train", col_set=[("label", "LABEL0")])   # ✅
```
handler 内部列是 MultiIndex `("feature","KMID")` / `("label","LABEL0")`，而 `col_set` 在列被压平**之前**生效。

### ③ 标签在 `data_key="learn"`

`prepare` 默认 `data_key="infer"`（处理后的**特征**）。要拿标签得 `data_key="learn"`。完整取全表（含 LABEL0）用默认 `col_set="__all"`，此时列名已压平成字符串。

### ④ `portfolio_dict` 的 key 是 `"1day"`

```python
portfolio_dict["day"]        # ❌ KeyError
key = next(k for k in portfolio_dict if k.endswith("day"))   # ✅ "1day"
```

### ⑤ `codes` 默认 `"all"` → 全市场加载，后果很重

- 慢 10 倍（3796 只票全读）
- 只要有一批股票缺 `factor.day.bin`，`trade_w_adj_price` 会被**全局**置 True → 整手撮合失效、涨跌停判定退化

```
WARNING ... factor.day.bin file not exists or factor contains `nan`. Order using adjusted_price.
WARNING ... trade unit 100 is not supported in adjusted_price mode.
```
**规则：`exchange_kwargs={"codes": ["SH600418"]}` 明确限定范围。**

### ⑥ 回测结束日不能是日历最后一天

```
IndexError: index 4943 is out of bounds for axis 0 with size 4943
```
`get_step_time()` 会取「下一根 K 线」，最后一天取不到。把 `end_time` 往前挪一个交易日。

### ⑦ `init_instance_by_config` 只读 `config["kwargs"]`

```python
{"class": "X", "module_path": "m", "topk": 50}                    # ❌ 被忽略，静默用默认值
{"class": "X", "module_path": "m", "kwargs": {"topk": 50}}        # ✅
```

### ⑧ `volume_threshold` 必须是 dict/tuple

```
AssertionError  (exchange.py:326 _get_vol_limit: assert isinstance(volume_threshold, dict))
```

### ⑨ 成本/换手是累计值

`total_cost` / `total_turnover` 已经是累计口径，再 `.sum()` 会得到天文数字（曾算出「年化换手 6.4e11%」）。

### ⑩ 特征重要度是 `Column_N`

`model.get_feature_importance()` 的 index 是 `Column_0..N`，用 `handler.get_cols()[:len(imp)]` 映射回因子名。

### ⑪ `qlib.contrib.model.linear`（不是 `linear_model`）

`Ridge` / `Lasso` / `LinearRegression` / `LinearModel` 都在 `qlib.contrib.model.linear`，且它们**是 sklearn 类**，不是 qlib 的 `Model` 子类——不能直接塞进 yaml 的 `task.model`，要自己包一层。

### ⑫ `qlib.model.ens` 在 0.9.8 是空的

网上文档里的 `Rolling` / `Average` 集成器这个版本没有。要集成自己写。

### ⑬ 无害噪音（不用管）

| 输出 | 原因 |
|---|---|
| `ModuleNotFoundError. XGBModel/CatBoostModel/PyTorch models are skipped` | 可选依赖未装 |
| `Gym has been unmaintained since 2022 ...` | gym 0.26 的提示 |
| `git diff ... fatal: not a git repository` + 一屏 git 帮助 | 实验管理器在非 git 目录下取代码版本失败 |
| `mlflow filesystem tracking backend deprecated` | mlflow 3.x 提示 |
| `$close field data contains nan` | 停牌日无价 |
| `load calendar error: freq=day, future=True; return current calendar!` | 没有未来日历文件，回测末期自动截断 |
| `BareException` 之外的 `BaseExecutor common_infra is not set` | 直接调 `backtest()` 不走 `qrun` 时会出现 |

### ⑭ 环境：GitHub 被 Watt Toolkit 中间人

`requests` 报 `SSL: CERTIFICATE_VERIFY_FAILED unable to get local issuer certificate` → `uv pip install pip-system-certs`（详见 [../README.md](../README.md) 第 3 节）。

### ⑮ `D.calendar` 返回 ndarray；`list_instruments(as_list=False)` 返回 dict

不是 DatetimeIndex / DataFrame，别直接 `.year` / `.columns`。

---

## 9. 最佳实践（防坑于未然）

1. **先定时间轴，再写代码**：写清「T 日出信号 → T+1 成交」，然后让标签、策略、回测三者对齐。对不上就是隐性泄漏或反向交易。
2. **防泄漏三件套**
   - 标签跨段：`Ref($close,-2)/Ref($close,-1)` 会吃边界后 2 天数据，训练集末尾砍 2 行
   - 归一化：`fit_start_time/fit_end_time` 只用训练段
   - 选型：阈值/超参只在 valid 上选，test 只跑一次
3. **单一验证段会过拟合 regime**：用滚动向前（walk-forward）多折，且候选池里必须放「全仓持有 / 纯规则」基线，否则选型没有"别折腾"这个选项。
4. **成本必须进回测**：日频策略换手很容易到 20~30 倍/年，成本吃掉 4~6% 本金是常态。跑一组零成本对照量化拖累。
5. **回测完先做执行校验**：独立重算期望仓位，和 `report["value"]/report["account"]` 比对一致率（正常应 >98%，差异应能归因到停牌/涨跌停/整手）。
6. **单票 vs 多票**：`TopkDropoutStrategy` 给多票；单票用 `WeightStrategyBase` 子类 + 目标权重。
7. **信号统一成 MultiIndex**：`pd.Series` + `MultiIndex(instrument, datetime)` 是 qlib 的通用货币，模型预测、自定义信号、落盘复用都走这个格式。

---

## 10. API 速查表

```python
# ---- 初始化
qlib.init(provider_uri, region="cn", expression_cache=None, dataset_cache=None)

# ---- 数据
D.calendar(start_time, end_time, freq="day")            -> ndarray
D.instruments(market="all")                             -> dict
D.list_instruments(instruments, start_time, end_time, as_list=False)  -> list/dict
D.features(instruments, fields, start_time, end_time, freq="day", disk_cache=False) -> DataFrame[(instrument,datetime)]

# ---- 数据集
Alpha158(instruments, start_time, end_time, fit_start_time, fit_end_time)   # 158+1 列
DatasetH(handler=..., segments={"train":(s,e), "valid":..., "test":...})
dataset.prepare(seg, col_set="__all", data_key="infer")  # col_set 用元组
dataset.handler.get_cols()                               -> list[str]

# ---- 模型
LGBModel(loss="mse", learning_rate=0.05, num_leaves=31, num_boost_round=1000, early_stopping_rounds=50)
model.fit(dataset) / model.predict(dataset, segment="test") / model.get_feature_importance("gain")

# ---- 回测
backtest(start_time, end_time, strategy, executor, benchmark="SH000300", account=1e6, exchange_kwargs={})
  strategy = {"class": ..., "module_path": ..., "kwargs": {...}}
  executor = {"class": "SimulatorExecutor", "module_path": "qlib.backtest.executor",
              "kwargs": {"time_per_step": "day", "generate_portfolio_metrics": True}}
  exchange_kwargs = {"codes": [...], "deal_price": "close", "open_cost": 0.0005,
                     "close_cost": 0.0015, "min_cost": 5, "limit_threshold": 0.095}
  -> portfolio_dict["1day"] = (report_df, positions)
     indicator_dict["1day"] = (indicator_df, Indicator)

# ---- 实验
R.start(experiment_name="x") / R.log_params(**p) / R.save_objects(**{"pred.pkl": s}) / R.get_recorder()
SignalRecord(model, dataset, recorder).generate()
SigAnaRecord(recorder).generate()
PortAnaRecord(recorder).generate()

# ---- 命令
python qlib-src\qlib\cli\run.py config.yaml
```

---

## 11. 参考

- 官方文档：https://qlib.readthedocs.io/
- 仓库：https://github.com/microsoft/qlib
- 数据说明：https://qlib.readthedocs.io/en/latest/component/data.html
- 本机示例：`../examples/01_quickstart.py`、`../examples/workflow_lgb_alpha158.yaml`
- 本机完整策略：`../projects/jac_600418/`
- 原始 API dump：`_api_dump/api_dump.txt`（从安装包直接导出，737 行）
- 可运行片段：`snippets/snippet_01_data.py`、`snippet_02_handler_model.py`、`snippet_03_backtest.py`
