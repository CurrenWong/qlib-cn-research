## 0. 文档索引

| 文档 | 内容 |
|---|---|
| **[AGENTS.md](AGENTS.md)** | **项目工作手册（给 agent 看）**：环境硬约束、两套数据源与更新流程、策略选型协议、18 条 qlib 实测踩坑、公众号发布流程、工作约定 |
| [DATA_STATUS.md](DATA_STATUS.md) | **数据状态（自动生成）**：当前数据更新到哪天、关键标的末价、更新日志、手动更新命令 |
| [tools/README.md](tools/README.md) | **脚本索引**：抓取 / 校验 / 数据更新 / 归档，各脚本干什么、要不要 token |
| [docs/QLIB_USAGE.md](docs/QLIB_USAGE.md) | **qlib 使用手册**：五层架构、数据层 / 特征层 / 模型层 / 回测层 API、report 字段口径、15 条实测踩坑、最佳实践 |
| [docs/DATA_UPDATE.md](docs/DATA_UPDATE.md) | **数据更新方案**：日更自建（腾讯/东财 + 全历史重写）/ 官方 dump_update 的复权陷阱 / 定期全量替换，含实测验证 |
| [projects/jac_600418/README.md](projects/jac_600418/README.md) | 江淮汽车 600418 择时策略（完整案例：walk-forward 选型 + 验证/测试 + 沪深300 对比 + 7.8 年扩展样本外） |
| [projects/jac_600418/news_attribution/REPORT.md](projects/jac_600418/news_attribution/REPORT.md) | **涨跌新闻归因**：772 个明显涨跌事件的新闻/公告归因（30.1% 有事前证据）+ 11 类公告的事件研究；含 akshare 接口实测与 qlib 前复权价陷阱 |
| [projects/iflytek_002230/README.md](projects/iflytek_002230/README.md) | **科大讯飞 002230 涨跌归因与结构分析**：574 个事件（2008 上市至今）+ 18 年收益解剖 + 涨跌停赚钱效应；结论：AI 标签的边际效应在衰减 |
| [docs/wechat_attrib/article.md](docs/wechat_attrib/article.md) | **公众号长文（新闻归因）**：把江淮 + 科大讯飞两个标的、1347 次大波动、4665 条公告的方法与结果整理成一篇；含 6 张配图与 HTML→PNG 预览 |
| 本文件 | qlib 环境安装、数据准备、官方示例跑通结果 |

---

## 0.1 仓库结构与版本控制约定（2026-11-13 起）

**只有代码和文档进 git，数据和二进制一律不进。**

```
D:\Project\qlib
├── AGENTS.md / README.md / PLAN.md / DATA_STATUS.md   # 文档（进 git）
├── .gitignore                                        # 二进制/大数据/缓存的过滤规则
├── tools\                    # 脚本（进 git；scratch 除外）
│   ├── README.md             #   ← 脚本索引，先看这个
│   ├── tushare_common.py     #   公共库
│   ├── fetch_stock_prices.py / fetch_sw_industry.py / industry_bias_heatmap.py
│   ├── selftest_fetch.py / verify_*.py / check_tushare.py
│   ├── archive\              #   一次性排障脚本（进 git，不再维护）
│   └── scratch\              #   临时探测脚本（**不进 git**，但保留在磁盘）
├── docs\                     # 手册与文章（.md/.py 进 git，配图 png 不进）
├── projects\                 # 各标的/主题子项目（代码 .md/.py 进 git，产物不进）
├── examples\                 # 官方示例改造版（进 git）
├── data\                     # 抓下来的行情/行业数据（**不进 git**）
├── qlib_data\                # qlib bin 数据集 1.0 GB / 9.5 万文件（**不进 git**）
├── qlib-src\                 # qlib 上游浅克隆，自带 .git（**不进 git**）
├── mlruns\                   # MLflow 记录（**不进 git**）
└── .venv\                    # 虚拟环境 840 MB（**不进 git**）
```

**为什么不把数据放进来**：`qlib_data\` 1.0 GB、`data\` 190 MB、`projects\trend_combo` 单目录 1.19 GB
（13 个 parquet 就占 1.5 GB）。这些都可由脚本重新生成（见 `tools/README.md`），放进 git 只会让
clone 变成灾难。图片同理——`docs\` 和 `projects\` 里的 png 合计 90+ MB，全部按扩展名过滤。

**新同学上手三步**：

```cmd
cd /d D:\Project\qlib
:: 1. 环境（见 §4）
uv venv --python 3.12 && uv pip install --python .venv\Scripts\python.exe -r requirements.lock.txt
:: 2. 数据（不进 git，得自己生成）
.venv\Scripts\python.exe tools\fetch_data.py && .venv\Scripts\python.exe tools\unzip_data.py
.venv\Scripts\python.exe tools\fetch_sw_industry.py
:: 3. 自检确认环境对
.venv\Scripts\python.exe tools\selftest_fetch.py
```

---

# Qlib 本地环境（D:\Project\qlib）

用 uv 虚拟环境安装 [microsoft/qlib](https://github.com/microsoft/qlib)，并跑通官方示例。
**状态：全部跑通（2026-10-28）。**

## 1. 环境事实

| 项 | 值 |
|---|---|
| uv | 0.9.4 |
| Python | 3.12.12（venv 由 `C:\Users\curre\.conda\envs\copaw\python.exe` 派生） |
| pyqlib | **0.9.8**，来自 git commit `54355232463878d2eebb91fe0ee5fa7fa1f5976c`（`git+https://github.com/microsoft/qlib.git`） |
| 依赖规模 | 194 个包，numpy 2.5.4 / pandas 2.3.3 / lightgbm 4.7.0 / mlflow 3.12.0 |
| 依赖锁 | `requirements.lock.txt` |

## 2. 目录结构

```
D:\Project\qlib
├── .venv\                        # uv 虚拟环境（含 qlib 0.9.8）
├── qlib-src\                     # qlib 官方仓库浅克隆（拿 examples / scripts）
├── qlib_data\cn_data\            # 数据集：calendars / instruments / features(31000 只股票)，271 MB
├── data\qlib_data_cn_1d_latest.zip   # 原始数据包 187.4 MB
├── examples\01_quickstart.py     # 示例一：官方 Quick Start
├── examples\workflow_lgb_alpha158.yaml  # 示例二：LightGBM + Alpha158 工作流配置（已改成本地数据路径）
├── tools\fetch_data.py           # 断点续传下载器
├── tools\unzip_data.py           # 解压脚本
├── tools\inspect_cert.py         # 排查 TLS 证书用
├── mlruns\                       # mlflow 实验记录（experiment 610952336028646039）
└── run_quickstart.log / run_lgb_clean.log  # 运行日志（已去掉 tqdm 刷屏行）
```

## 3. ⚠️ 关键坑：GitHub 走 Watt Toolkit 加速导致 SSL 校验失败

本机 GitHub 流量被 **Watt Toolkit（原 Steam++，证书 CN=SteamTools Certificate / O=BeyondDimension）**
中间人代理。conda 派生的 Python 用 OpenSSL 自带 CA 库，不认这个自签 CA，报：

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate
```

**解决：** `uv pip install pip-system-certs`（5.3）→ venv 内 requests/ssl 改走 Windows 系统证书库，
问题消失。已安装，以后在这个 venv 里下 GitHub 资源不需要额外设置。

> 备注：`curl` 访问 github.com 即使不加 `-k` 也会失败（exit 35），加 `-k` 才通，同因。

## 4. 复现命令

```cmd
:: 建环境 + 装 qlib（源码版）
cd /d D:\Project\qlib
uv venv --python 3.12
uv pip install --python .venv\Scripts\python.exe "git+https://github.com/microsoft/qlib.git"
uv pip install --python .venv\Scripts\python.exe pip-system-certs

:: 数据（187MB，走断点续传；官方 get_data.py 也可，只是它下到 ~/.qlib 且不支持续传）
.venv\Scripts\python.exe tools\fetch_data.py
.venv\Scripts\python.exe tools\unzip_data.py

:: 示例一：Quick Start
.venv\Scripts\python.exe examples\01_quickstart.py

:: 示例二：LightGBM + Alpha158（全流程：训练 → 预测 → IC → 回测，约 5 分钟 / 16 核）
.venv\Scripts\python.exe qlib-src\qlib\cli\run.py examples\workflow_lgb_alpha158.yaml
```

## 5. 跑通结果

### 示例一 Quick Start（`run_quickstart.log`）
- `qlib.init` 成功，data_path = `D:/Project/qlib/qlib_data/cn_data`
- 日历：`2010-01-04, 2010-01-05`
- csi500 成分股列表正常返回 `['SH600006','SH600008','SH600021',...]`
- `D.features(['SH600000'], ['$close','$volume','Ref($close,1)','Mean($close,3)','$high-$low'], 2010-01-01~2017-12-31)` → 1897 行

### 示例二 LightGBM Alpha158（`run_lgb_clean.log`）
| 指标 | 值 |
|---|---|
| IC | 0.04681 |
| ICIR | 0.38157 |
| Rank IC | 0.04905 |
| Rank ICIR | 0.40675 |
| 组合年化收益（含成本） | 12.60% |
| 信息比率 IR | 1.4286 |
| 最大回撤 | -7.23% |
| 超额收益年化（含成本） | 8.07%（IR 0.9145，MDD -8.61%） |

与官方 README 的 LightGBM/Alpha158 基准同量级，数据链路正常。

## 5b. 子项目：江淮汽车（600418）择时策略

单独目录：**`D:\Project\qlib\projects\jac_600418\`**，完整策略文档见
[`projects\jac_600418\README.md`](projects/jac_600418/README.md)。

- 策略：Ridge(α=100) 21 因子回归 → 5 日平滑 → 「分数 > 训练集 q=0.4 分位点 **且** 收盘价 > MA20」→ 满仓，否则空仓
- 选型：滚动向前 walk-forward（2013~2018 六折，目标 = 相对沪深300 的信息比率均值），跨折 IR +0.237、5/6 折为正
- 样本切分：训练 2008-2016 / **验证 2017-2018** / **测试 2019-01~2020-09-24**
- 结果（qlib 撮合，含成本）：

| 区间 | 策略 | 沪深300 | 买持江淮 | IR |
|---|---|---|---|---|
| 验证集 2017-2018 | **+13.76%** | -9.92% | -57.75% | **+0.571** |
| 测试集 2019-2020 | **-18.96%** | +53.66% | +53.00% | **-0.898** |

结论是**诚实的样本外失败**：测试期江淮本身几乎追平沪深300（+28.9% vs +29.2%），
是择时（30% 仓位 + 30 倍年化换手）把收益做没了。文档里有完整归因、季度拆解、
执行正确性校验（仓位一致率 98.6~99%）和 qlib 工程备忘。

## 6. 已知无害告警

- `ModuleNotFoundError: CatBoostModel / XGBModel / PyTorch models are skipped` — 未装可选模型，正常。
- `$close field data contains nan` / `factor.day.bin file not exists` → 回测自动退化为 adjusted_price 模式。
- `Gym has been unmaintained since 2022 ... NumPy 2.0` — gym 0.26.2 的提示，本流程不含 RL。
- `mlflow filesystem backend deprecated` — mlflow 3.x 对 `./mlruns` 的弃用提示，不影响使用。

## 7. 待清理（未动，等确认）

- `C:\Users\curre\.qlib\qlib_data\cn_data\` — 首次用官方脚本下载失败留下的空目录（已把半成品 zip 移到 `data\` 复用）。
- `data_download.log` / `dl_stdout.log` / `dl_stderr.log` / `download_data.cmd` — 第一次失败尝试的残留。

