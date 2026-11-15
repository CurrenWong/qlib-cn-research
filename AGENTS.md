# AGENTS.md —— <repo> 项目工作手册

> 这份文件是给**在这个仓库里干活的 agent（含我自己）**看的：环境硬约束、数据怎么维护、策略协议、踩过的坑、以及不许做的事。
> 事实优先于描述；凡是和代码/输出对不上的，以代码为准，并回来改这份文件。

---

## 0. 这是什么项目

三件事装在一个仓库里：

1. **qlib 本地环境** —— GitHub 版 microsoft/qlib（不是 PyPI 版），跑通官方示例；
2. **子项目 `projects/jac_600418/`** —— 江淮汽车（600418）单票日频择时策略的完整研究与回测（**主战场，产出最多**）；
3. **数据管道 + 文档** —— 把冻结快照换成日更数据、写了使用手册和公众号长文。

当前结论摘要：策略**三次样本外失败**（详见 `projects/jac_600418/README.md` 第 0/12/13 节）。这个项目现在最大的价值不是那个策略，而是**一整套可复现的失败记录 + qlib 工程踩坑清单**。

---

## 1. 环境硬约束（改之前先读这段）

| 项 | 值 |
|---|---|
| 解释器 | `.venv\Scripts\python.exe`（uv 建，Python 3.12.12）|
| qlib | pyqlib **0.9.8 @ commit 5435523**，从 GitHub 装（PyPI 版不装）|
| 额外依赖 | **`pip-system-certs` 必须装**（见 §3 的 Watt Toolkit 坑）|
| shell | cmd.exe；`&&` / `&` 都能连写，但 `>` 重定向的目录必须**事先存在** |
| 数据下载 | 官方脚本不支持续传 → 用 `tools/fetch_data.py`（Range 续传）|

```cmd
cd /d <repo>
.venv\Scripts\python.exe <脚本>
```

**不要用系统 python、不要新建 venv、不要 pip install -U qlib**（会换成 PyPI 版并毁掉环境）。

---

## 2. 目录地图

```
                        ← 2026-11-13 起是 git 仓库（只有代码/文档，数据不进）
├── .venv\                     uv 虚拟环境（唯一解释器，**不进 git**）
├── qlib_data\
│   ├── cn_data\               旧数据（Microsoft 示例快照，日历到 2020-09-25）
│   └── cn_data_2026\          新数据（chenditc 日更版，日历到 2026-10-30）← 主力（**不进 git**）
├── data\                      抓下来的行情 / 申万行业 / 乖离率图（**不进 git**）
├── examples\                  官方示例（01_quickstart 等）
├── tools\                     数据维护 + 抓取脚本（见 §4；索引见 tools\README.md）
│   ├── tushare_common.py      公共库（token/切批/bin 读取/限频重试）
│   ├── fetch_stock_prices.py  日线 raw/qfq/hfq（腾讯双域名 or Tushare）
│   ├── fetch_sw_industry.py   申万一级行业成分（PIT）
│   ├── industry_bias_heatmap.py  行业乖离率热力图
│   ├── selftest_fetch.py      抓取链自检（39 项）
│   ├── check_tushare.py       token 体检（认证/权限/限频三层）
│   ├── archive\               一次性排障脚本（保留，不再维护）
│   └── scratch\               当次会话的临时探测脚本（**不进 git**，但不删）
├── docs\
│   ├── QLIB_USAGE.md          qlib 使用手册（11 章，踩坑全表）
│   ├── DATA_UPDATE.md         数据更新方案对比 + 执行状态
│   ├── wechat\                公众号长文（江淮策略三次失败）：article.md / img\ / 生成脚本 / preview.html
│   ├── wechat_attrib\         公众号长文（新闻归因方法 + 两标的结果）：article.md / 6 图 / HTML→PNG 脚本
│   ├── wechat_trend_combo\    公众号长文（基本面×价量混合打分）：article.md / 8 图 / 封面 / 草稿脚本
├── projects\jac_600418\       策略子项目（见 §5）
├── projects\iflytek_002230\   科大讯飞归因子项目（见 §5.7）
├── projects\trend_combo\      基本面 × 价量 混合趋势打分框架（见 §5.8）
├── qlib-src\                  qlib 上游浅克隆（自带 .git，**不进 git**）
├── DATA_STATUS.md             数据状态（自动生成，勿手改）
├── README.md                  顶层索引 + 环境说明 + 仓库结构约定
└── PLAN.md                    安装计划（已全部完成）
```

**版本控制铁律（.gitignore 已落）**：`*.bin / *.parquet / *.npz / *.png / *.jpg / *.pdf / *.xlsx /
*.zip / *.csv / *.wav / *.mp4`、`qlib_data/`、`data/`、`qlib-src/`、`mlruns/`、`.venv/`、
`tools/scratch/`、`tools/_cache/` **都不进 git**。
体积账：qlib_data 1.0 GB（9.5 万文件）、projects/trend_combo 1.19 GB、data 190 MB、
docs 里 png 29 MB —— 都能由脚本重建（`tools/` + `DATA_UPDATE.md`），不进仓库。

---

## 3. ⚠️ GitHub 走 Watt Toolkit 会导致 SSL 校验失败

本机装了 Watt Toolkit 加速，GitHub 流量被中间人劫持，报的证书是 `CN=SteamTools Certificate`，pip/git 直接 SSL 失败。

**解法**（已装，勿重复折腾）：

```cmd
.venv\Scripts\python.exe -m pip install pip-system-certs
```

症状相同但换了别的报错时，先怀疑这一条。

---

## 4. 数据：两套源 + 怎么更新

### 4.1 两套数据

| | `qlib_data\cn_data` | `qlib_data\cn_data_2026` |
|---|---|---|
| 来源 | Microsoft qlib 示例快照 | `chenditc/investment_data` release **2026-10-27** |
| 日历 | 1999-11-10 ~ 2020-09-25 | 2000-01-04 ~ **2026-10-28**（6497 个交易日）|
| 600418 行数 | ~4800 | 6105（末日收盘 9.7542）|
| 校验 | — | sha256 `126efcc80b5052729d4f84585efad5a9be5f9a5be083d93343d1caa204ac30fe`，size 569575728 |

**两源收益率完全可比**（2019-01~2020-09：旧 +53.00% vs 新 +53.02%），价格差恒定 1.39 倍（只是复权基准不同）→ **换源不需要重做历史结论**。

### 4.2 切换方式

策略侧用环境变量切，**不要改代码默认值**：

```cmd
set "JAC_PROVIDER=qlib_data\cn_data_2026"
set "JAC_DATA_END=2026-12-31"
```

### 4.3 更新脚本（`tools\`）

| 脚本 | 什么时候用 | 干什么 |
|---|---|---|
| `append_latest_bars.py` | **普通交易日** | 只追加当天一根，历史零改动；用不复权接口 + 自校准系数 |
| `update_symbol_bins.py` | **分红送股之后** | factor 变了，必须**全历史重写** |
| `write_data_status.py` | 想刷新状态文档 | 生成 `DATA_STATUS.md`，并被上面两个脚本**自动调用** |
| `verify_update.py` / `verify_production_data.py` | 更新后校验 | 重叠区间对账、停牌 NaN 一致性 |

```cmd
cd /d <repo>
.venv\Scripts\python.exe tools\append_latest_bars.py --dir qlib_data\cn_data_2026
```

**规矩**：
- **不注册定时任务**（用户明确要求），手动跑；每次更新自动备份到 `cn_data_2026\_backup\<时间戳>\`；
- 每次更新后 `DATA_STATUS.md` 会自动刷新，不要手改那个文件；
- 数据现状随时查 `DATA_STATUS.md`。

### 4.4 拉数据的坑

- 腾讯 `fqkline/get` 的 **qfq 不是封接口，是限频**（2026-11-13 重新验证）：
  连续几十个请求后整个域名会回 **HTTP 501**（`waf.tencent.com/501page.html`），
  **连不复权 `kline/kline` 一起挂**，冷却 10~20 分钟后自动恢复。
  → 请求间隔 ≥ 2.5s、撞 501 冷却 90s 再试一次、还不行就**换域名**或中止（`--resume` 续抓）；
  抓到的响应落 `tools/_cache/tencent/`（`域名|param` 做 md5 键），重跑不重复烧配额。
- **限频是按域名的**：`web.ifzq.gtimg.cn` 已经 501 的时候，
  `https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get` **同一时刻照样 200**
  （参数格式、`qfqday`/`hfqday` 字段完全一样）。`fetch_stock_prices.py` 现在两个域名轮换。
- 两个域名都**只认右边界**：给 `lo..hi` 它返回 hi 之前 640 根（会越过 lo），所以按
  **从 until 往前翻页**（每页取第一根再往前一天）直到覆盖 since。
- **腾讯的 qfq / hfq 都是「等额复权」**（`不复权价 − 累计分红`），**不是乘权**：
  600519 在 2024-01~2026-11 的 `raw − qfq` 只在 5 天跳变，恰好是 5 次分红
  （30.876 / 23.882 / 27.600 / 23.957 / 28.024 元），其余日子**完全恒定**。
  → 所以 `factor = qfq / raw` 是假的（比值随价格漂移），
  `close_hfq = close_qfq × factor` 更是把误差放大（实测把 +9.29% 的单日涨幅算成 +10.03%）。
  正确做法：用 qfq 的阶梯还原分红 → 推**乘权**因子 `F = Π 1/(1 − 分红/前收)` → `hfq = raw × F`。
- **腾讯 `hfq` 那一路自相矛盾，弃用**：非除权日 hfq 与 raw 的日收益差中位 0.1%、最大 1.6%，
  与 qfq 差最大 2.1% —— 既不是乘权也不是等额，拿来当后复权会凭空造波动。
- **本地 `qlib_data` 的 `factor.bin` 也不是乘权因子**（与 qfq/raw 比值同构，逐日微漂），
  别拿它去做乘法复权；要复权就用 `tools/fetch_stock_prices.py` 的 `derive_hfq`。
- **Tushare 真实状态（2026-11-13 实测，120 积分档）**：
  - ✅ `pro.daily` **可用**：单只 `ts_code=` 正常；`trade_date=YYYYMMDD` 一次返回全市场 ~5573 行。
  - ❌ **`ts_code="600519.SH,000001.SZ"` 逗号串会静默返回空表**（原图那种 `','.join(stock_list)`
    的写法在这档位直接失效）→ 批量必须**按交易日**抓：调用数 = 交易日数，跟股票只数无关。
  - ⚠ `pro.adj_factor` 是 **1 次/小时**→ 批量复权不可行。代码已降级：拿不到就只输出不复权价、
    复权列留 NaN，并提示用 `--source tencent` 的 `derive_hfq` 反推因子。
  - ⚠ 本地日历只到 2026-10-30，抓「最近几天」时区间会落在日历外 → 已退化为「工作日」。
  - ✅ 真值校验：Tushare 与腾讯不复权收盘价 **9 天重叠，最大差 0.000000**（自检第 9 段）。
- **`40203` 既表示「没有接口权限」也表示「频率超限」**，只看 code 会误判，
  必须连 msg 一起判（`tools/check_tushare.py` 已按措辞分流）。
- **Tushare 的日期参数只吃 `YYYYMMDD`**：传 `2024-01-02` 不报错，**直接返回空表**。
- **Tushare 的「没有接口访问权限」= 账号层面被限，不是 token 写错**（2026-11-13 实测）：
  HTTP 端点回 `code 40203`，SDK 只留一句「抱歉，您没有接口(xxx)访问权限」。
  区分办法（`tools/check_tushare.py` 已内置）：**假/随机 token 会回 `40101 您的token不对`**，
  而真 token 回 `40203` → 说明 token 在系统里**存在**，问题在账号。
  本机实测那串 token 连 `trade_cal`（0 积分接口）都拒 → 不是「积分差 120」，而是整个账号没放行，
  优先怀疑：① token 与有权限的账号不是同一个 ② 手机/邮箱未绑定导致 0 分。
  `daily`/`adj_factor` 需 **120 积分**，`index_classify`/`index_member_all` 需 2000 积分。
  → `call_with_retry` 已改成**对权限错误立刻失败**（不再白等 14 秒再抛误导信息）。
  → token 存放：`%USERPROFILE%\.tushare_token`（单行），或环境变量 `TUSHARE_TOKEN`，或 `--token`。
  → **凭据一律不进仓库**（2026-11-13 清理过一轮）：东财搜索会话 Cookie 从 `EM_SEARCH_COOKIE`
  环境变量或 `%USERPROFILE%\.em_search_cookie` 读取（`projects/*/news_attribution/fetch_news.py`
  的 `_em_cookie()`），以前是写死的；微信各平台 appid/secret 只从环境变量读
  （`docs/wechat_attrib/check_creds.py` 只看变量名和长度，不打印明文）。
  入库前跑一次密钥扫描：`tools/scratch/_secret_scan.py`（sha256 / commit hash 命中属误报）。
- **免费源可用性矩阵（2026-11-13 本机实测，别再重复试错）**：

| 数据 | 来源 | 状态 |
|---|---|---|
| 日线 raw/qfq/hfq | 腾讯 `fqkline` + `proxy.finance`（双域名） | ✅ 通，原始价与本地 bin 逐日一致 |
| 乘权复权因子 | 腾讯 qfq 阶梯推导（`derive_hfq`） | ✅ 通 |
| 申万一级行业成分（含计入日） | 申万官网 API | ✅ 通 |
| 申万一级行业**指数日线** | akshare `index_hist_sw`（上游 swsresearch `index_publish/trend`） | ✅ 通，个别行业只从 2014/2021 起（申万改版） |
| 交易日历 / 全量历史 | 本地 `qlib_data/cn_data_2026` | ✅ 通 |
| 实时快照（市值/PE/流通市值） | 东财 `push2/stock/get`（f116/f117/f162） | ✅ 通 |
| 财务数据 | 东财 `datacenter-web` / 巨潮 `cninfo` | ✅ 通 |
| **东财 K 线**（`push2his/stock/kline`） | 东财 | ❌ `RemoteDisconnected`（复权三态全挂） |
| 指数成分权重 | 中证指数官网 | ⚠ 首页 200，xls 直链 403（需 Referer） |

→ 结论：**Tushare 不是必需品**，它买的是「省事 + 字段全 + 口径统一」，不是独家数据。
- `.bin` 必须**按交易日历对齐**，停牌日填 NaN——不对齐会把停牌价格错位到别的日子；
- 成交量单位要校准（手 / 股），别默认。

**现成工具**（2026-11-13 新增，源自一篇公众号文章的 Tushare 代码，原图有 8 处硬伤已修）：

```cmd
cd /d <repo>
.venv\Scripts\python.exe tools\check_tushare.py                   :: token 体检（认证 vs 权限分开测）
.venv\Scripts\python.exe tools\fetch_stock_prices.py --source tencent --since 2024-01-01
.venv\Scripts\python.exe tools\fetch_sw_industry.py            :: 申万一级行业成分（PIT）
.venv\Scripts\python.exe tools\industry_bias_heatmap.py        :: 行业乖离率热力图（BIAS + 分位）
.venv\Scripts\python.exe tools\verify_fetched_prices.py        :: 抓回来的价 vs 本地 bin 对账
.venv\Scripts\python.exe tools\selftest_fetch.py               :: 37 项自检（默认走缓存，0.3s）
.venv\Scripts\python.exe tools\selftest_fetch.py --with-tushare  :: 额外真跑 Tushare（无权限自动跳过）
```

---

## 5. 子项目 `projects/jac_600418\`

### 5.1 策略

- 标的 600418，基准沪深300；21 个因子（**17 纯价格 + 3 纯成交量 + 1 价量交互** `px_vol_corr`）；
- 模型：Ridge（α∈{1,10,100}）+ LightGBM 候选；**实测三套重切全部选中 Ridge**；
- 规则：`score > 阈值`（= 训练集分数的 q 分位点）**且** `close > MA20` → 满仓，否则空仓；只做多、不加杠杆、不设止损；
- 时间轴：T 日收盘出信号 → T+1 日收盘成交 → 持有到 T+2 日收盘（标签 `Ref($close,-2)/Ref($close,-1)-1`）；
- 成本：买入 0.05%、卖出 0.15%、涨跌停 ±10%、最低 5 元、账户 100 万。

### 5.2 选型协议（**别改，改就是作弊**）

- 三分：训练 / 验证 / 测试，**测试集绝不参与选型或调参**；
- walk-forward：折年由 `JAC_FOLDS` 指定，每折训练窗口 = `max(TRAIN_START, 折年-9)` 的**滚动 9 年**，验证 = 折年内；
- 阈值用**训练集**分数分位点（绝对阈值会随模型尺度漂移，跨折不可比）；
- 候选池**必须保留基线**（全仓持有 / MA20 趋势 / MA60 趋势），否则选型没有"干脆别择时"的退路；
- 目标：相对沪深300 的信息比率**跨折均值**；
- 每次改完必须跑**零成本对照**，把成本影响和信号影响分开。

### 5.3 结果目录

| 目录 | 对应实验 |
|---|---|
| `results\` | 原始：训练 2008-2016 / 验证 2017-2018 / 测试 2019-2020 |
| `results_2026_frozen\` | 参数冻结、把测试期延长到 7.8 年 |
| `results_A\` `results_B\` `results_C\` | **三套重新切分**（各自重新选型），README 第 13 节 |

### 5.4 三次失败的结论（别重复踩）

1. 样本外 IC **归零**：训练集 +0.103~+0.124（t>6）→ 测试集 -0.008~-0.026（|t|<1）；
2. **换手 49 倍是杀手**：成本每年吃掉 3.45~4.64pct，累计 18%~32% 本金；
   对照：平滑 5 日时换手 25.7 倍、成本约 2pct/年 → **平滑窗口 5→1 让成本翻倍**；
3. **选型 IR 不能外推**：IR 最高的方案 B 测试期最差；
4. 全部大幅跑输买入持有（600418 期间涨 3 倍）。

### 5.5 常用命令

```cmd
cd /d projects\jac_600418
set "JAC_PROVIDER=qlib_data\cn_data_2026"
set "JAC_DATA_END=2026-12-31"
set "PYTHONWARNINGS=ignore"      :: qlib 的 RuntimeWarning 会淹没输出

:: 选型（必须先跑，产出 results_X\strategy_choice.json）
.venv\..\..\.venv\Scripts\python.exe tools\walkforward.py
:: 回测
..\..\.venv\Scripts\python.exe run_backtest.py
:: 三方案汇总
..\..\.venv\Scripts\python.exe tools\compare_splits.py
```

切分参数：`JAC_TRAIN_START/END`、`JAC_VALID_START/END`、`JAC_TEST_START/END`、`JAC_FOLDS`、`JAC_RESULTS`。

### 5.6 新闻归因子项目 `projects/jac_600418\news_attribution\`

把「涨跌到底对应什么新闻」做成可复现的归因：773 条原始事件 → 772 条有效事件 → 11 类公告 T0/T1/T5 事件研究。

| 文件 | 内容 |
|---|---|
| `REPORT.md` | 主报告（7 节） |
| `news_matches.csv` | 772 条归因结果（含证据链接） |
| `event_study.csv` | 11 类公告的 T0/T1/T5 超额与胜率 |
| `news_cache\` | 2309 条公告 + 354 条新闻 + 240 条快讯 |
| `check_report.py` | **报告数字自检**（60 项，跑完必过） |

**关键结论**：2026-04 起有事前新闻证据的事件占 94.1%（之前只有 23.4%~32.4%）——
这是"回看能找到理由"和"事前就有理由"的区别，别混为一谈。

**坑**

1. **qlib 的 `close` 是前复权价**（本项目 ÷0.4831），新浪/腾讯是不复权成交价，两者直接比会得出
   方向完全相反的结论；本模块用**实际成交价**做图和算收益。
2. **除权日会造出假事件**：qlib 前复权序列在除权日跳空，会凭空多出一条"暴跌"。
   本期只出现过 1 条（2005-12-14，qlib -6.18% vs 新浪 +7.32%），已剔除。
3. **绘图时缓存的基准数据必须先切区间**：`bench["close"].iloc[0]` 取的是**全历史第一根**，
   不是绘图区间的第一根——起点对齐就会把沪深300 甩出 y 轴范围，灰线直接消失。
4. `Circle` 画在 `transAxes` 里会被**拉成椭圆**，编号圆改用 `annotate` + `boxstyle="circle"`。
5. 文字标注框**不要压走线**：改成「上图只放编号圈 + 下图放事件卡片」的双栏结构
   （`make_fig.py`），编号圈用 `annotate` 的圆角 bbox，偏移时用 `arrowprops` 连回真实位置。

### 5.7 科大讯飞 002230 归因子项目 `projects\iflytek_002230\`

同一套流水线的**同构分支**（`projects\jac_600418\news_attribution\` 的拷贝 + 标的参数化），
覆盖 2008-05-12（IPO 首日）~ 2026-10-27，**4396 个交易日**、574 个事件。

| 文件 | 内容 |
|---|---|
| `projects\iflytek_002230\README.md` | 子项目说明 |
| `projects\iflytek_002230\news_attribution\REPORT.md` | 主报告（10 节）|
| `analysis.py` / `analysis.json` | 18 年结构分析（分年度 / 关键窗口 / 涨跌停赚钱效应）|
| `check_report.py` | 报告数字自检（**161 项**）|

**核心结论**（与 600418 的对照很有说服力）

1. 18 年年化 **16.07%** vs 沪深300 **0.27%**，年化超额 +15.8pct；但超额几乎全来自
   2009–2015（+262.7pct）和 2023（+61.4pct），**2024-09 之后只剩 +7.9pct，2026 年 -10.8pct**。
2. **"利好公告日"常是下跌日**：2022 年报当日 -9.2%、星火发布会次日 -8.6%、开发者节前跌停 -10.0%；
   业绩/财报类公告 **T0 超额 -0.551%**（n=187）。
3. **跌停比涨停可预测**：跌停次日再跌 **-2.141%**、胜率 **32.1%**（n=28）；
   涨停次日 +1.211%、胜率 56.9%，但 T+20 超额归零（+0.142%、胜率 50.0%）。
4. 有事前证据的事件 T+1 胜率仅 48.4% → **事后归因 ≠ 事前可知**（600418 同样成立）。

**新增的坑（在上面 5 条之外）**

6. **实体词必须带上下文**：「星火」「翻译机」「合肥」单独用会误匹配（星火燎原 / 行业新闻 /
   合肥本地要闻）；科大讯飞的实体词要用「星火大模型」「AI学习机」「智能办公本」这种组合词。
7. **命中正文 ≠ 关于该公司的报道**：归因会同时看标题和正文前 200 字，行业分析文章把讯飞
   当对比对象提及也会命中 → 这类要人工降级（本期有 1 条：2026-06-26）。
8. **日志轴刻度**：`ax.set_yscale("log")` 后 major tick 只在 10/100，
   区间跨不到就**整个 y 轴没有标签** → 要 `LogLocator(base=10, subs=np.arange(1,10)*0.1)`
   配 `FuncFormatter`。
9. `annotate` 的 `xy` **不能写 `("2024-10-08", 37.62)`**（str+float 混搭会报
   `ConversionError`），要用 `pd.Timestamp`。
10. **基准线出现"垂直跳变"先查数再怀疑渲染**：2024-09-24 沪深300 五个交易日 **+25%**，
    线性图上就是一根近乎垂直的线——是真实行情，不是坏点。
11. **停牌日会变成"伪事件"，而且会污染胜率分母**：qlib 的 adjclose 在停牌日是 NaN，
    002230 有 4 天（2008-08-18、2015-07-08~10）被记成"个股停、大盘动"的 L2 超额事件；
    它们的 T+1 不存在，**算胜率时必须 dropna 后再统计**，
    否则 NaN 被当成亏损，胜率被压低 0.1~1.2pct（002230 报告已按修正口径重出，
    check_report 从 161 项变 163 项）。
12. **两套实现对同一份数据算出不同数，先做 A/B 对齐**：同口径的"事件后续超额"如果
    两份脚本不一致，多半是 excess 序列的**索引是否保留 NaN 行**不同——
    保留 NaN 行会让 `iloc[i+1]` 的位置整体错位，数字看着对、实际错。
    `docs/wechat_attrib/diag_ab.py` 是现成的 A/B 对齐脚本。

### 5.8 基本面 × 价量 混合打分框架 `projects\trend_combo\`

在 `csi300_lgbm` 的 30 个价量特征之上，**外接东财 F10 基本面（PIT）**，用
「标准化 → 训练期自动定向 → 分域线性加权」合成一个趋势分。**qlib 保留**（价量 + 标签 + 回测），
基本面**不进 qlib 的 bin**（改走 parquet + 披露日 as-of 对齐），**不重训 LightGBM**。

| 文件 | 内容 |
|---|---|
| `tools/fetch_fundamental.py` | 抓东财三接口 → `data\fund_*.parquet`（637 只 / 390 秒）|
| `tools/build_panel.py` | 按 `NOTICE_DATE ≤ t` as-of 对齐 → `data\panel_merged.parquet` |
| `tools/composite.py` | winsorize → 行业中性化 → z → 限幅 → 分域分数 → `data\scores.parquet` |
| `tools/eval_ic.py` | 因子级 IC → 自动定向 → 跨域权重网格 → `results\ic_results.json` |
| `tools/score_holdings.py` | 实盘 20 只打分 → `results\holdings_score.json` |
| `tools/strategy.py` | **验证期选参 + 完整策略回测**（换手/成本/基线）→ `results\backtest.json` |
| `tools/counterfactual_oct.py` | **与实盘 20 只同口径对照**（10-30 选股 → 11-02 开盘买 → 11-05 收盘卖）→ `results\counterfactual_oct30.json` |
| `report/counterfactual_oct30.md` / `.png` | 对照实验报告（总账 / 逐日路径 / 重叠度 / 数据问题） |
| `report/trend_combo_report.html` / `.png` | 方案报告（13 张配图，含策略回测章节）|

**核心结论（实测）**

1. **方向定错，整块信号就是反的**：教科书先验方向下价量块测试期 IC = **−0.0074**，
   改成训练期 RankIC 定方向后 = **+0.0332**；45 个因子里 18 个先验方向被推翻
   （20 日动量在 5 日 horizon 上是反向的）。
2. **基本面有正 alpha 但更弱、衰减更快**：纯基本面测试期 IC +0.0093（IR +0.10）
   vs 纯价量 +0.0332（IR +0.30）；训练→测试掉 58%，价量块几乎不掉。
3. **权重**：验证期最优把基本面给到 0.4，测试期最优在 0.2~0.3 → 「选型不可外推」又复现；
   共同高台区 0.2~0.4 → **建议 价量 0.65 / 基本面 0.30 / 事件 0.05**。
4. **策略层（阶段二）**：验证期选参（K=50 / 每 40 日调仓 / 行业≤3 / 等权）→
   测试期年化 **+5.87%**、超额 **+5.34%**、IR +0.68、MDD −28.97%、换手 4.12/年、成本 1.05pct/年；
   训练 +1.47% / 验证 +1.24% / 全区间 +2.10%（三段都正）。
   但**测试期最高的 top20 月调 +7.05% 在训练期 −4.02%、验证期 −5.51% → 不可上线**。
5. **换手是胜负手**：每 5 日调仓全亏（成本 4.3~4.7pct/年），每 10 日打平，只有 ≥20 日转正。
6. **纯价量（−0.66%）/ 纯基本面（−3.33%）单独都不行，混合才行** → 基本面的作用是改排序、砍坑。
7. **超额集中在 2025**，MDD 全区间 −48% → 只适合当卫星仓。

**新增的坑**

13. `merge_asof` 的右表**不能有空值 merge key**（NOTICE_DATE 有 NaT）→ 先 dropna 再对齐。
14. `groupby().rolling().rank()` 返回 MultiIndex，赋值回原表要 `reset_index(level=0, drop=True)`。
15. **行业中性化会把没有行业标签的股票整列打成 NaN**（`z - NaN`）→ 先用 0 初始化减数矩阵，
    成分 < 5 只的行业也要跳过，否则该行业个股被清零。
16. **后台 `start /b` 起的 python 会在工具调用结束时被回收**（日志写一半就停）→
    长任务必须在**前台**跑，或用带 flag 文件的 wrapper。
17. 东财 datacenter 接口比 push2 稳：`datacenter-web.eastmoney.com/api/data/v1/get`
    （RPT_VALUEANALYSIS_DET / RPT_PUBLIC_OP_NEWPREDICT）与
    `datacenter.eastmoney.com/securities/api/data/v1/get`（RPT_F10_FINANCE_MAINFINADATA）都通，
    但 AGENTS.md §4.4 说「东财接口已不可用」——**那条只对 push2 的某些老接口成立**。
18. **策略回测里 `0 × NaN = NaN` 会剔样本**：权重网格里「某域权重=0」不等于「不看这一域」，
    那一域缺数据就把整行踢掉 → 网格数字会略高于「纯单域」变体。
    报告口径以**纯变体表**为准，两者的差要写进报告。
19. **别拿测试期最高的配置上线**：本次 top20 月调测试期 +7.05% 最高，但训练期 −4.02%、
    验证期 −5.51%。**参数只能在验证期选**，然后看三段是否都为正（本次选出的 top50/40 日配置三段全正）。
20. **面板的宇宙不是「当前沪深300」，是历史成分并集 → 会混进死票**（2026-11-05 实测）：
    637 只里有 338 只在 10-30 那行 `close` 是 NaN（本地 bin 只更新到 **10-27**），
    另有 **20 只最后一次交易在 2017~2023 年**（腾讯接口核对）。这 20 只的 `price_score`
    并列占满上限 **+0.5630** → 在全池上按「纯价量」排序，**前 20 名全是买不到的票**。
    回测没暴雷是因为仿真器过滤了「停牌不可交易」，但**排名本身已被污染**。
    → 选股前必须剔「当日无行情 + 长期无成交」的票（`tools/dbg_zombie.py` / `dbg_gap.py` 是现成诊断）。
21. **分数带缺口 = 用旧价算的分**：`close` 为 NaN 但分数非 NaN 的票，分数是用 10-27 的旧价/前值填充算的。
    对照实验里「策略原样全池」组因此混进 6 只这种票，4 天里恰好逆势 → 组间差 2.7pct，纯属运气。
22. **4 个交易日的对照不能用来换仓**：同一天同一批因子，A 组 +2.04% / B 组 −0.69%，
    差别只来自 6 只票；两个组合都跑输沪深300（+2.68%）。要决策等 11-30 调仓日 + 完整数据。
23. **本地 qlib 的更新范围只有「当前沪深300 成分 300 只」，而面板宇宙是「历史成分并集 637 只」**
    （2026-11-05 查明）：`tools/append_latest_bars.py` 一次只处理 `--symbols-file` 里的标的，
    最近一次跑（备份 `20261102_100058`）只喂了当时的 300 只成分 → 它们被追加到 10-30，
    其余 **316 只历史成分票的 bin 还停在上一次全量更新的 2026-10-27**；
    另有 **22 只早已停牌/退市**（最后交易 2017~2025，源数据里本来就没有之后的 bar）。
    后果：面板在 10-30 那天只有 299/637 只有收盘价，但**分数照样算得出来**（旧价/前值填充），
    选股混进「用旧价算的票」，全池「纯价量 top20」甚至是买不到的死票。
    → 补数据用 `python tools/append_latest_bars.py --symbols-file <宇宙名单> --until <日期>`；
    真停牌的要从宇宙里剔掉。
    **✅ 2026-11-05 已修**：分 4 块（85/85/85/83）跑完 append_latest_bars，**316 只追加成功**、
    20 只已是最新、2 只放弃；备份 `_backup\20261105_2121xx`；
    随后重跑 `build_dataset → build_panel → composite`，
    **10-30 有收盘价的从 299 只变成 615 只**（只剩 22 只真停牌），
    对照实验的「策略原样全池」与「干净池」两组从此完全相等（+3.84%），此前 2.7pct 的差异是运气。
24. **停牌股的价格被前向填充，`price_pos_250` 等因子取到极端值 → 22 只死票仍并列占满
    `price_score` 上限（+0.5694）**：`build_dataset` 的 `close.pct_change()` 默认 `fill_method='pad'`，
    停牌/退市股的价格被填成一条平线，于是「价格处于 250 日最高」这类因子恒为 1，
    z-score 后挤到上限 → 全池「纯价量 top20」首选就是这批买不到的票。
    **✅ 2026-11-05 已修**：`tools/composite.py` 里「当日无收盘价 → price_score 置 NaN」
    （没有收盘价 = 当天不可交易，本来就不该有价量分）。
    效果：price_score 最大值从「20 只并列 0.5694」变成「1 只独占 0.4342」，
    打到上限的僵尸股 20/20 → **0/20**；回测测试期年化 +5.87% → +5.84%（基本不变），
    训练 +1.47% → +1.91%、验证 +1.24% → +1.61%。
    根因（pct_change 前向填充）仍在上层，哪天绕过 composite 直接用 features.parquet 还会咬人。
25. **仓位规则「每只 1 万 + 零头补一手」在高价股上失控**：寒武纪 907 元/股 → 1 手 9.07 万，
    **单票权重冲到 39%**；90 元的票 → 补一手变 2 手 = 1.8 万 = 7%。
    **✅ 2026-11-05 已修**（`tools/counterfactual_oct.py`）：
    **等权 + 单票权重上限 10%（按实际投入计）+ 整手向下取整**，两遍执行：
    第一遍按名义预算等权买（一手超「名义预算×10%」的剔除）；
    第二遍按**实际投入**重算上限、超限的按整手裁小、裁到 0 剔除，**迭代到收敛**
    （剔除后分母变小、权重会反弹，必须反复重算）。
    坑：等权目标要**固定在名义预算**上，不能跟着缩水后的实际投入走，否则越裁越少（会缩到 8 万）。
    实盘那 20 只是旧规则建的仓、已买入不能改；**11-30 调仓起改用新规则**。

---

## 6. qlib 踩坑清单（Windows + 0.9.8 实测）
**数据层**
1. `.bin` 首元素是**起始下标**，其后才是数据；不对齐日历 = 停牌日价格错位。
2. **复权因子单独存** `factor.day.bin`——自己读 `.bin` 不读 factor 就会对不上。
3. **`cn_data_2026` 的 `close` 是前复权价，不是成交价**（2026-11 实测：与新浪原始价之比恒为 **0.4831**）。
   实际成交价 = `close ÷ 0.4831`；`adjclose ≠ close × factor`（这份数据集里 adjclose 是独立的一路）。
   **收益率不受影响**（比值恒定，`close.pct_change()` 与 `adjclose.pct_change()` 完全一致，
   与新浪前复权逐日比对 5926 天：相关 0.9978、平均绝对差 0.062pct），但**引用绝对价格时必须换算**。
4. **用原始价算日收益会凭空造出"崩盘"**：2004-10-28(-43.6%)、2005-12-14(-55.3%)、2007-07-05(-26.0%)
   是除权跳空。前复权序列能抹平前两个，但 **2005-12-14 残留 -6.18% 假跌**（停牌两日后复牌除权，
   因子 0.1528→0.3210 与价格未完全对齐）→ 做事件研究前必须与新浪前复权交叉校验（见
   `projects/jac_600418/news_attribution/validate_returns.py`）。
5. `D.features` 与 `prepare` 的**索引顺序相反**。
6. `label` **只在 `data_key="learn"` 下有效**。
7. `col_set` 必须是**元组** `[("label","LABEL0")]`，写成字符串会静默出错。
8. **Windows 下 `D.features` 没有 `__main__` 保护**，在交互式/片段里跑会**无限 fork** → 一律写进文件再跑。

**特征/模型层**
9. 特征重要度返回 `Column_N`，要 `handler.get_cols()` 映射回因子名。
10. `qlib.contrib...` 里部分算子只有名字没有文档，用前先 dump API。

**回测层**
11. **回测结束日不能取日历最后一天**（`get_step_time` 越界 → IndexError），取倒数第二天。
12. `portfolio_dict` 的 key 必须是 `"1day"`。
13. `StrategyContext` 的 kwargs **必须嵌套一层**。
14. `Exchange` 传 `codes=[单票]`，否则会用全局 `adjusted_price`。
15. report 里 `total_cost` / `total_turnover` **已经是累计值**，不能再 sum。
16. 指数回测里 `codes` 与 `bench` 的成分要自己算，不要依赖默认配置。

**无害告警**（不用管）
17. `Mean of empty slice`（`qlib/utils/index_data.py`）
18. `common_infra is not set`（`qlib.backtest.executor`）

---

## 7. 文档地图与维护约定

| 文件 | 内容 | 谁维护 |
|---|---|---|
| `README.md` | 顶层索引 + 环境事实 + 复现命令 | 改环境就改它 |
| `docs/QLIB_USAGE.md` | qlib 使用手册（12 章：五层架构 / 数据层算子表 / 特征 / 模型 / 回测 / 实验管理 / 15 条踩坑 / API 速查）| 加新坑就加进去 |
| `docs/DATA_UPDATE.md` | 三种更新方案对比 + 坑 + 执行状态 | 改方案就改它 |
| `DATA_STATUS.md` | **自动生成**，数据更新到哪天 | 不要手改 |
| `projects/jac_600418/README.md` | 策略文档（0~13 节）| 改策略就改它 |
| `docs/wechat/article.md` | 公众号长文源 + 配图 | 发了就归档，别丢 |

**约定**：公众号后台的正文不可 diff、源一丢就不可重发 → **文章源文件 + 全部配图必须和代码一起版本化**（`docs/wechat/`）。

---

## 8. 公众号发布流程

素材先行 → 委派 → 停在草稿 → 用户拍板群发。

1. **备齐素材再委派**（缺素材子 agent 会自造替代物）：正文 `docs/wechat/article.md`、配图 `docs/wechat/img/`、封面 `img/cover.png`；
2. 配图生成脚本：`docs/wechat/make_figures.py`（6 张 150dpi）、`make_cover.py`（1080×864）、`make_preview.py`（本地预览 `preview.html`）；
3. **委派「文本创作智能体」澄**（agent id `J6c4mu`）：`chat_with_agent` / `submit_to_agent`，用后台模式 + 轮询 `check_agent_task`；
4. **停在草稿，不群发**；「勾原创」接口设不了，**必须用户在编辑器手动点**；
5. 核验口径：正文纯文本与本地稿逐字比对；图片数 = `<img>` 数 = CDN 图数。

**两个接口坑**：提交时 `json=` 会把中文转成 `\uXXXX` 字面量（用 `data=json.dumps(..., ensure_ascii=False).encode("utf-8")`）；回读时微信把 `<img>` 的 `src` 换成 `data-src`，不还原会误判成"图片全挂了"。

**澄的模型可能 429**（`minimax-coding-plan` 的 Token Plan 用量上限），表现为 `chat_with_agent` 返回空 + 后台任务直接 failed。改 `workspaces\J6c4mu\agent.json` 的 `active_model` 可切（如 `deepseek:deepseek-v4-flash`）——**这是改别人的计费配置，要用户点头**。

### 8.1 一稿多发（公众号 + 知乎/CSDN/掘金/百家号/B站）

已落地在 `docs/wechat_attrib/`（2026-10-30 首次跑通，5 平台 + 公众号共 6 份草稿）：

```
docs\wechat_attrib\article.md       公众号真源（【插图 N：…】标记）
   ├─ make_source.py ─→ src\article.md    多平台真根源（front matter + ![](img/x.png)）
   │                     └─ 委派澄（multi-platform-post skill）─→ dist\<平台>\ 草稿
   └─ publish_wechat_attrib.py ─→ 公众号草稿（API，7 图 + 封面）
```

- **素材必须自己备齐再委派**：`src\article.md`（front matter 在 `front_matter.yaml`）+ `src\img\` 7 张图 + `cover.png`。
  缺素材子 agent 会自造替代物。
- **核验口径**（两边都要过）：
  - 公众号：`verify_draft_attrib.py` → `纯文本长度 local/render 一致=True`、`img = mmbiz 数`；
  - 多平台：`check_dist.py` → 5 个平台稿 **0 缺段**、h2 数一致（CSDN 会多一张封面首图，是规则如此）。
- **坑**：澄的 `publish.py` 每发一个平台就**覆盖** `dist\publish-report.md`，
  所以要么让它自己记链接，要么事后按平台回执拼。B站图片上传是坏的（adapter 层 bug），要手动补图。
- **更大的坑：千万别为了"核图"重跑 publish**。`publish.py` 每跑一次就**新建一份草稿**，
  本次把 CSDN 重发 5 次 → 多出 2 份废稿 + 撞上 `文章频繁发布，请稍后再试` 限流。
  正确做法：**第一次发就把 CLI 输出重定向到日志**，`✓ 上传` 行从日志里数。
- 实际结果与待人工收尾项见 `docs/wechat_attrib/PUBLISH.md`。

### 8.2 公众号长文：基本面×价量混合打分（`docs/wechat_trend_combo/`）

第二篇公众号长文，素材来自 `projects/trend_combo`（45 因子 + PIT 基本面 + 策略回测）。

```
docs\wechat_trend_combo\article.md          公众号真源（【插图 N：…】标记，8 图 7 表）
  ├─ make_cover.py ─→ img\cover.png         封面 1080×864（深色底 + 净值曲线）
  ├─ make_source.py ─→ src\article.md       多平台真根源（front matter + ![](img/x.png)）
  │                       └─ 委派澄（multi-platform-post）─→ dist\trend_combo\<平台>\ 草稿
  ├─ build_html.py ─→ article.html / wechat_body.html（本地预览 + 公众号全内联正文）
  └─ publish_wechat_trend_combo.py ─→ 公众号草稿（API，8 图 + 封面）
```

- **多平台那 5 个平台（知乎/CSDN/掘金/百家号/B站）由「文本创作智能体」澄用
  `multi-platform-post` skill 建草稿**，本项目只负责备齐素材 + 公众号这一路；
- **坑 16 的两个检查自己做掉**：`fix_bold.py` 把加粗里的句末标点挪到加粗外、
  并检查有没有跨行加粗（不然后面某些平台的 Markdown 解析器会把整段吃成星号）；
- 公众号草稿核验用 `verify_draft_attrib.py`（纯文本长度 local/render 必须一致）；
- 结果与人工待办见 `docs/wechat_trend_combo/PUBLISH.md`。

---

## 9. 工作约定

- **中文沟通，直接说人话**；先给结论和数字，再给过程。
- **失败要如实报**，不要粉饰、不要事后调参把它说成成功；归因错了要认（"踏空"是错的归因，"换手成本"才是）。
- **不主动删文件**：调试脚本、日志、旧的 `results_*` 目录都保留，删除要先问；破坏性/对外/不可逆操作一律先确认。
- **改结论要同步改文档**：`README.md` / `docs/` / 记忆文件三处对齐，别只改代码。
- **数字必须来自实际输出**，不要凭印象写（本次发布前审计就抓出 3 处）。
- 写脚本时用 `-u`（`python -u`）避免输出缓冲丢失；qlib 的 `RuntimeWarning` 建议 `set PYTHONWARNINGS=ignore`。
- Windows 下 `cmd` 的 `>` 重定向目录必须先 `mkdir`，否则整条命令静默失败。
- **git 只装代码和文档**（2026-11-13 起）：提交前先 `git status` 看有没有二进制混进来；
  数据/图片/模型按 `.gitignore` 过滤（`*.parquet / *.bin / *.png / *.pdf / *.zip / *.csv` 等）。
  确要提交一张图，用 `git add -f` 并说明理由，别改 `.gitignore` 放行整类文件。
- **提交信息写"为什么"不写"改了什么"**：`fix(fetch): 腾讯 qfq 是等额复权，factor 不能用 qfq/raw`
  比 `update fetch_stock_prices.py` 有用得多。

---

## 10. 命令速查

```cmd
:: 环境自检
cd /d <repo> && .venv\Scripts\python.exe -c "import qlib;print(qlib.__version__)"

:: 抓取链自检 / Tushare token 体检
.venv\Scripts\python.exe tools\selftest_fetch.py
.venv\Scripts\python.exe tools\selftest_fetch.py --with-tushare
.venv\Scripts\python.exe tools\check_tushare.py

:: 行情 / 行业 / 乖离率
.venv\Scripts\python.exe tools\fetch_stock_prices.py --source tencent --since 2024-01-01
.venv\Scripts\python.exe tools\fetch_sw_industry.py
.venv\Scripts\python.exe tools\industry_bias_heatmap.py

:: 跑官方示例
.venv\Scripts\python.exe examples\01_quickstart.py

:: 数据状态
.venv\Scripts\python.exe tools\write_data_status.py

:: 策略：选型 → 回测 → 汇总（projects\jac_600418 下）
..\..\.venv\Scripts\python.exe tools\walkforward.py
..\..\.venv\Scripts\python.exe run_backtest.py
..\..\.venv\Scripts\python.exe tools\compare_splits.py

;; 公众号：重生成配图 / 封面 / 预览
.venv\Scripts\python.exe docs\wechat\make_figures.py
.venv\Scripts\python.exe docs\wechat\make_cover.py
.venv\Scripts\python.exe docs\wechat\make_preview.py

:: 沪深300×LightGBM 组合（projects\csi300_lgbm）
cd /d projects\csi300_lgbm
..\..\.venv\Scripts\python.exe tools\rank_latest.py 20     :: 最新 top20 → results/picks_K20.json
..\..\.venv\Scripts\python.exe tools\real_price.py        :: 还原真实价 → picks_K20_price.json（日期硬编码，月末跑前要改）
..\..\.venv\Scripts\python.exe tools\pnl_monday.py        :: 算「信号日→今天」的三种口径盈亏
..\..\.venv\Scripts\python.exe tools\track_pnl.py         :: 实盘持仓每日净值追踪（幂等，手动跑，不注册定时任务）
:: 实盘台账：results\positions_A.json（冻结，勿手改）→ track_pnl.csv / track_positions_latest.csv
:: 操作手册：projects\csi300_lgbm\report\track_pnl_README.md

;; 基本面 × 价量 混合打分框架（projects\trend_combo）
cd /d projects\trend_combo
..\..\.venv\Scripts\python.exe tools\fetch_fundamental.py   :: 抓东财 F10 → data\fund_*.parquet（约 6.5 分钟）
..\..\.venv\Scripts\python.exe tools\build_panel.py         :: PIT 对齐（披露日 as-of）→ data\panel_merged.parquet
..\..\.venv\Scripts\python.exe tools\composite.py          :: 标准化 + 分域 → data\scores.parquet
..\..\.venv\Scripts\python.exe tools\eval_ic.py             :: 因子 IC → 自动定向 → 权重网格 → results\ic_results.json
..\..\.venv\Scripts\python.exe tools\score_holdings.py      :: 实盘 20 只打分 → results\holdings_score.json
..\..\.venv\Scripts\python.exe tools\strategy.py           :: 验证期选参 + 策略回测(换手/成本/基线) → results\backtest.json
..\..\.venv\Scripts\python.exe tools\make_figures.py        :: 13 张配图
..\..\.venv\Scripts\python.exe tools\build_report.py       :: 报告 HTML
..\..\.venv\Scripts\python.exe tools\render_png.py         :: HTML → PNG
```
