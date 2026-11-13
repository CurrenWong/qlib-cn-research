# tools 索引

> 全部脚本都用项目 venv 跑：`.venv\Scripts\python.exe tools\<脚本>`
> 数据产物一律落在 `data\`（**不进 git**），中间临时脚本在 `tools\scratch\`（也不进 git）。

## 一、行情 / 行业数据抓取（2026-11-13 新增）

| 脚本 | 作用 | 需要 token |
|---|---|---|
| `tushare_common.py` | 公共库：token 解析、代码互转、行数预算切批、qlib bin 读取、带限频识别的重试 | 否（库本身） |
| `fetch_stock_prices.py` | 日线行情 raw / qfq / hfq + 乘权因子。腾讯双域名 + 响应缓存；也可走 Tushare | 可选 |
| `fetch_sw_industry.py` | 申万一级行业清单与成分（含计入日，可做 PIT） | 否 |
| `industry_bias_heatmap.py` | 行业乖离率（BIAS）+ 三张热力图 + 分位 | 否 |
| `check_tushare.py` | Tushare token 体检：认证 / 权限 / 限频三层分开判 | 需 token |

## 二、校验 / 自检

| 脚本 | 作用 |
|---|---|
| `selftest_fetch.py` | 抓取工具链自检（39 项；`--with-tushare` 才真打接口） |
| `verify_fetched_prices.py` | 抓回来的价 vs 本地 qlib bin 逐日对账 |
| `verify_sw_industry.py` | 申万行业表/成分表一致性 + 与本地宇宙的覆盖关系 |
| `verify_update.py` / `verify_production_data.py` | 数据更新后的重叠区间对账 |
| `compare_data_sources.py` / `check_cn_data_2026.py` | 数据源对比、cn_data_2026 健康检查 |

## 三、数据更新 / 维护

| 脚本 | 作用 |
|---|---|
| `append_latest_bars.py` | 日更：追加最新 bar 到 `qlib_data\cn_data_2026`（带备份） |
| `update_symbol_bins.py` | 按标的批量更新 bin |
| `write_data_status.py` | 生成 `DATA_STATUS.md`（别手改那个文件） |
| `prepare_cn_data_2026.py` / `cleanup_residuals.py` | 建库预处理、清理残档 |

## 四、归档（`tools\archive\`，一次性排障脚本）

`debug_tx_*.py`、`probe_*.py`、`inspect_cert.py` 等早期排障脚本。
**保留备查，不再维护**；新问题先看 `AGENTS.md` §4.4 的「免费源可用性矩阵」。

## 五、临时脚本（`tools\scratch\`）

当次会话写的探测/诊断脚本（`_probe_*.py`、`_check_*.py`、`_cmp_*.py`）。
**不入 git**，但也不删——按项目约定保留现场。
