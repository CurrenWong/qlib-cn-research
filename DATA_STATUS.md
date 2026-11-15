# 数据状态（自动生成，勿手改）

> 本文件由 `tools/write_data_status.py` 自动生成；`append_latest_bars.py` /
> `update_symbol_bins.py` 每次更新成功后会自动刷新它。
> 手动刷新：`.venv\Scripts\python.exe tools\write_data_status.py`

## 当前状态

| 项 | 值 |
|---|---|
| **数据最新到** | **2026-10-30** |
| 状态文件生成时间 | 2026-11-05 21:25:35 |
| 数据目录 | `qlib_data\cn_data_2026` |
| 交易日历 | 2000-01-04 ~ 2026-10-30（6499 个交易日） |
| 股票数 | instruments/all.txt 共 6172 条（含已退市；按日期区间过滤后 2026 年在市约 5600 只） |
| 数据来源 | `chenditc/investment_data` release **2026-10-27**（qlib_bin.tar.gz，569,575,728 bytes）+ 后续按日追加 |

### 关键标的

| 代码 | 起始 | **最新交易日** | 收盘（复权） | factor | 行数 |
|---|---|---|---|---|---|
| SH600418 | 2001-08-24 | **2026-10-30** | 8.8894 | 0.483120 | 6107 天 |
| SH000300 | 2005-01-04 | **2026-10-30** | 4.0553 | 0.001018 | 5299 天 |

## 更新日志

| 更新时间 | 数据最新到 | 日历天数 | 标的末价 |
|---|---|---|---|
| 2026-10-31 14:14:11 | 2026-10-28 | 6497 | SH600418 9.7542 / SH000300 4.1554 |
| 2026-11-05 21:25:35 | 2026-10-30 | 6499 | SH600418 8.8894 / SH000300 4.0553 |

## 怎么更新（不注册定时任务，手动跑）

```cmd
:: 普通交易日（只追加当天，历史零改动；用不复权接口，前复权接口被 WAF 封时也能用）
cd /d <repo>
.venv\Scripts\python.exe tools\append_latest_bars.py --dir qlib_data\cn_data_2026

:: 分红送股之后（factor 变了，必须全历史重写）
.venv\Scripts\python.exe tools\update_symbol_bins.py --dir qlib_data\cn_data_2026

:: 只想刷新本文件
.venv\Scripts\python.exe tools\write_data_status.py
```

每次更新会自动备份到 `qlib_data\cn_data_2026\_backup\<时间戳>\`。

## 相关文档

- [`docs/DATA_UPDATE.md`](docs/DATA_UPDATE.md) —— 三种更新方案对比、复权与日历对齐的坑
- [`docs/QLIB_USAGE.md`](docs/QLIB_USAGE.md) —— qlib 使用手册
- [`projects/jac_600418/README.md`](projects/jac_600418/README.md) —— 江淮汽车策略（第 12 节的 7.8 年样本外检验基于本数据）
