# 如何获得每日数据更新

> 背景：Microsoft 官方示例数据（`SunsetWolf/qlib_dataset`）冻结在 **2020-09-25**。
> 2026-10-28 换用 `chenditc/investment_data` 的日更 release 后，数据到 **2026-10-27**。
> 本文回答：之后每天怎么更新，三条路怎么选。

---

## 0. 结论先说

| 方案 | 适合场景 | 成本 | 风险 |
|---|---|---|---|
| **A. 自建日更**（腾讯/东财 API + 全历史重写）✅ 推荐 | 单票/小股票池研究（本项目） | 每天 30 秒 | 依赖第三方接口稳定性 |
| **B. qlib 官方 `dump_update`** | 你有自己的全市场 CSV 源（tushare 落盘等） | 每天几秒 | **前复权口径陷阱**（见 §3） |
| **C. 定期全量替换**（重下 chenditc 543MB） | 需要全市场 5000+ 只票 | 543MB / 次，实测代理下 27KB/s ≈ 5 小时 | 无（数据质量最好），但慢 |

**给本项目的建议**：A 做日更（只维护 600418 + 沪深300），C 每季度兜底一次全市场刷新。

---

## 1. 方案 A：自建日更（已实现并验证）

### 1.1 为什么能这么简单

单只股票 6000 根 K 线的全历史重写是**毫秒级**的，所以根本不需要"增量追加"——
每天把该票的全部历史重算重写一遍，天然避免了增量更新最容易出的口径不一致问题。

### 1.2 数据源实测对比

| 源 | 可达性（2026-10-28 实测） | 前复权 | 单次上限 | 备注 |
|---|---|---|---|---|
| 腾讯 `web.ifzq.gtimg.cn` | ✅ 稳定 | ✅ qfq | 640 根（需分页） | 主力源 |
| 东财 `push2his.eastmoney.com` | ❌ 连试 5 次全 `RemoteDisconnected`（半小时前还能用） | ✅ fqt=1 | 无限制 | 降级为备用 |

两者都给「前复权 / 不复权」两套序列，`factor = 前复权收盘 / 不复权收盘`。

### 1.3 已实现的脚本

`tools/update_symbol_bins.py`

```cmd
:: 每日一条命令（更新 600418 + 沪深300 到最新交易日）
cd /d <repo>
.venv\Scripts\python.exe tools\update_symbol_bins.py --dir qlib_data\cn_data_2026

:: 先看会改什么，不落盘
.venv\Scripts\python.exe tools\update_symbol_bins.py --dir ... --dry-run

:: 换标的
.venv\Scripts\python.exe tools\update_symbol_bins.py --dir ... --symbols SH600418,SH000300,SZ000858
```

它做四件事：
1. 腾讯分页抓全历史（前复权 + 不复权）→ `factor = adj/raw`
2. **口径自校准**：反解常数 k，把源数据换算到本数据目录的基准（见 §4.1）
3. **按日历对齐**后重写 `features/<code>/*.day.bin`（停牌日写 NaN，见 §4.2）
4. 补 `calendars/day.txt` 新日期、更新 `instruments/all.txt` 结束日

写之前自动备份到 `<qlib_dir>\_backup\<时间戳>\`。

### 1.4 本次实测验证（2026-10-28 跑通）

```
SH600418  校准: 价格 ×0.483120, 成交量 ×0.020699
          ✅ 连续性 2026-10-27: 旧 9.5658 vs 新 9.5658（差 0.000%）
          ✅ 写入 6105 天（2001-08-24 ~ 2026-10-28），含 178 个停牌 NaN
SH000300  ✅ 连续性 2026-10-27: 旧 4.1205 vs 新 4.1205（差 0.000%）
```

与原数据逐日对账（`tools/verify_update.py`）：

| 标的 | 重叠 9 天 | 新增 2026-10-28 |
|---|---|---|
| SH600418 | 最大差 **0.004%** | 9.7542（= 前复权 20.19 × 0.48312 ✓） |
| SH000300 | **0.000%** | 4.1554 |

178 个 NaN 与原数据的 178 个停牌日**完全一致**，说明日历对齐正确。

### 1.5 ⚠️ 腾讯 WAF 拦截与"纯追加"备用模式（2026-10-28 当天遇到）

分页抓全历史后，腾讯把**前复权**接口封了：

```
GET https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600418,day,,,640,qfq
→ HTTP 501  <script>...window.location.href="https://waf.tencent.com/501page.html"...
```
而**不复权**的旧接口仍然正常：

```
GET https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=sh600418,day,,,640
→ HTTP 200 {"data":{"sh600418":{"day":[["2024-03-07","16.160",...]]}}}
```

**关键洞察**：在没有除权除息的日子里，本数据目录的 `close.bin = 不复权价 × factor`，且 factor 不变，
所以「不复权价 × 已有的 factor」就能正确追加新的一天，**完全不需要重写历史**（历史零风险）。

于是新增 `tools/append_latest_bars.py`：

```cmd
:: 平时用这个（快、安全、不碰历史）
.venv\Scripts\python.exe tools\append_latest_bars.py --dir qlib_data\cn_data_2026

:: 一旦发生分红送股（factor 变了），必须用全历史重写模式
.venv\Scripts\python.exe tools\update_symbol_bins.py --dir qlib_data\cn_data_2026
```

| 场景 | 用哪个 | 原因 |
|---|---|---|
| 普通交易日 | `append_latest_bars.py` | 只追加，历史一个字节都不动 |
| **除权除息日之后** | `update_symbol_bins.py` | factor 变了，全历史前复权价都要重算 |
| 前复权接口被 WAF 封 | `append_latest_bars.py` | 它只用不复权接口 |

**2026-10-28 实测（纯追加模式，已应用到正式目录）**：
```
SH600418 校准 ×0.483120（与文件里的 factor 完全一致）→ 追加 1 天，共 6105 天
SH000300 校准 ×0.001018 → 追加 1 天，共 5297 天
历史 9 天对账：全部 0.000% 差异（历史零改动）
新增：600418 9.7542 / 沪深300 4.1554
备份：qlib_data\cn_data_2026\_backup\20261028_230121
```
历史抽查（新口径 = 旧源 ÷ 1.39）：2018-12-28 = 2.3057（旧 3.205 ✓）、2020-09-24 = 3.4920（旧 4.8527 ✓）。

### 1.6 加入 Windows 计划任务（每个交易日收盘后跑）

```cmd
schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 18:30 ^
  /TN "qlib_daily_update" ^
  /TR "cmd /c cd /d <repo> && .venv\Scripts\python.exe tools\update_symbol_bins.py --dir qlib_data\cn_data_2026 >> logs\update.log 2>&1"
```

- 18:30 跑（A 股 15:00 收盘，行情接口一般 16:00 后稳定）
- 周末/节假日跑也无害：没有新日期就什么都不写
- 查看/删除：`schtasks /Query /TN qlib_daily_update`、`schtasks /Delete /TN qlib_daily_update /F`

---

## 2. 方案 C：定期全量替换（兜底）

```cmd
:: 拿最新 tag
curl -s https://api.github.com/repos/chenditc/investment_data/releases/latest
:: 下载 + 校验 + 解压（tools\prepare_cn_data_2026.py 已封装）
.venv\Scripts\python.exe tools\prepare_cn_data_2026.py --src <下载到的 qlib_bin.tar.gz>
```

- 543 MB，解压后 ~697 MB（5606 只票）
- release 都带 `qlib_bin.manifest.json`（SHA256 + 目标交易日 + 未来日历），**务必校验**
- 实测代理下 27 KB/s → 5 小时；建议用多线程下载器或浏览器直下
- 优点：一次性把全市场刷新到最新、数据质量由上游交叉校验保证

**建议节奏**：每季度一次，或在新季度做研究前手动跑一次。

---

## 3. 方案 B：qlib 官方 `dump_update`（有坑，慎用）

```cmd
python qlib-src\scripts\dump_bin.py dump_update --csv_path <新数据csv目录> --qlib_dir <数据目录> --freq day
```

源码（`scripts/dump_bin.py` 的 `DumpDataUpdate`）行为：
- 只取 `date > instruments[code].end` 的行**追加**到 .bin 末尾
- 追加 `calendars/day.txt`
- **不重写历史**

### ⚠️ 前复权陷阱

qlib 的 `close.bin` 存的是**前复权价**，前复权基准是"最新一天"。**每次分红送股，整个历史的前复权价都会变**。
只追加新行 = 历史用旧基准、新数据用新基准 → **除权日出现价格跳空**，回测收益全错。

正确用法只有两种：
1. 源数据用**不复权价 + factor**（factor 每次全量重算）→ 追加是安全的；
2. **每天全量重写该票历史**（= 方案 A 的做法）。

如果坚持用 `dump_update`，务必在每次分红后跑一次 `dump_fix` 或全量 `dump_all` 重建。

---

## 4. 三个必须知道的技术细节

### 4.1 复权因子口径不同源：必须自校准

| 数据 | 2026-10-27 收盘 | factor |
|---|---|---|
| chenditc（本项目数据） | 9.5658 | 0.483120 |
| 腾讯/东财**前复权** | 20.19 | （无此概念，基准=最新日 → 隐含 1.0） |
| 腾讯/东财**不复权** | 19.80 | — |

chenditc 的 `close.bin = 不复权价 × factor`，而第三方"前复权"在最新一天恒等于不复权价 → 两者差一个常数 k。
**做法**：用重叠日反解 `k = 现有 close.bin 末日值 / 源前复权同日值`（本例 0.483120，与文件里的 factor 完全吻合），再把整条序列 ×k。

不做这步 → 写入后价格直接跳 2 倍。

### 4.2 qlib 的 .bin 是"日历对齐"的

`.bin` 格式：`float32[start_index] + float32[values...]`，**values 长度必须等于日历从 start_index 到末尾的天数**，停牌日写 NaN。

数据源返回的是**稀疏序列**（缺停牌日）。直接写会整体错位（我第一版就栽在这：600418 的 5927 根被写进 6105 天的跨度，导致 qlib 读不出最近数据）。

正确做法：`pd.Series(index=日历[start:]).loc[源日期] = 值`，再整体写入。

### 4.3 成交量单位

腾讯/东财的成交量单位是**手**（100 股），qlib 用**股**；而 chenditc 的 `$volume` 又是另一套量级。
同样用重叠日校准 `k_vol`（本例 0.0207、9.83），单位差异自动吸收。

---

## 5. 每日工作流（建议）

```
15:00 收盘
   ↓
18:30 计划任务 → tools\update_symbol_bins.py（30 秒）
   ↓
   ├─ 日历追加当天、features 全历史重写、instruments 更新结束日
   ├─ 自动备份到 _backup\<时间戳>\
   └─ 打印「连续性」一行：旧 vs 新重叠日差 <0.5% 才可信
   ↓
第二天 跑策略会自然把新一天纳入（qlib.init 只读目录，无需重启服务）
```

**每季度**额外做一次方案 C 全量替换，防止单票口径长期漂移。

---

## 6. 相关文件

| 文件 | 作用 |
|---|---|
| `tools/update_symbol_bins.py` | 方案 A 实现（日更） |
| `tools/verify_update.py` | 更新后与旧数据逐日对账 |
| `tools/prepare_cn_data_2026.py` | 方案 C（校验 + 解压全量包） |
| `tools/check_cn_data_2026.py` | 数据体检（字段完整性、IC 依赖的复权因子） |
| `tools/compare_data_sources.py` | 两个数据源收益率一致性对账 |
| `qlib_data\_test_update\` | 本次更新的验证副本（可删） |

---

## 7. 执行状态

| 事项 | 状态 |
|---|---|
| 清理下载残留（689 MB） | ✅ 已完成 |
| 2026-10-28 应用到正式目录 `cn_data_2026` | ✅ **已完成**（日历 → 2026-10-28，历史零改动，已备份） |
| 数据状态文档 | ✅ [`../DATA_STATUS.md`](../DATA_STATUS.md)（自动生成，含更新日志） |
| 定时任务 | ❌ **按需求不注册**，改为手动跑命令 |

**当前数据更新到 `2026-10-28`**，随时可查 `DATA_STATUS.md`（每次跑更新脚本会自动刷新）。

手动更新就两条命令（普通交易日只跑第一条）：

```cmd
cd /d <repo>
:: 普通交易日：只追加当天，历史零改动
.venv\Scripts\python.exe tools\append_latest_bars.py --dir qlib_data\cn_data_2026

:: 分红送股后：factor 变了，必须全历史重写
.venv\Scripts\python.exe tools\update_symbol_bins.py --dir qlib_data\cn_data_2026
```
