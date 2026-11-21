# 策略收益归因长文（公众号 + 多平台）

把「实盘组合两周亏 8.18%、跑输沪深300 6.89 个点」这件事，用申万一级行业的**乖离率（BIAS）**
拆成「不是选股模型坏了，是风格暴露」，写成一篇对外文章。

> 正文：[`article.md`](article.md)（公众号真源，带【插图】标记）
> 多平台源：[`src/article.md`](src/article.md)（front matter + 标准 markdown 图片）

## 这篇文章讲什么

- **事实**：2026-11-02 开盘建仓 20 只（沪深300 × LightGBM），成本 256,525 元；
  11-20 收盘 235,555 元，**-8.18%**，同期沪深300 -1.28%，**超额 -6.89pct**，8 盈 12 亏。
- **归因**：电子 39.5%（BIAS120 -32.9%）+ 通信 19.1%（-43.8%）= **58.6% 权重压在最超卖的两个行业**；
  银行 23.0%（+11.9%、分位 95，最热）5 只全赚。
- **转折**：传媒 11-11 时 BIAS20 +7.66%、唯一四周期全正、分位 93（最拥挤），
  11-20 变成 -11.54%、四周期全负、分位 1 —— **9 天从最拥挤翻到最超卖**。
- **结论**：选股模型要配风险模型；给组合加「行业权重上限 + BIAS120 风格约束」。

## 文件

| 文件 | 作用 |
|---|---|
| `article.md` | 公众号真源（7 张插图用 `【插图 N：路径｜图注：…】` 标记，9 个 h2、6 张表）|
| `front_matter.yaml` | 多平台头部参数 + 各平台导语（`summary` ≤ 20 字，CSDN 硬上限）|
| `make_source.py` | `article.md` → `src/article.md` + `src/img/`（沿用 bias_post 的单向生成）|
| `make_cover.py` | 封面 1080×864：净值曲线 + 31 行业 BIAS120 色条（都是真实数据）|
| `fix_bold.py` | 把加粗里的句末标点挪到加粗外（14 处），改前后数字序列必须一致 |
| `check_article.py` | **数字自检 117 项**：从源文件重新读数，核对正文每个数 |
| `check_dist.py` | 核验 5 个分发包（图片引用 / h2 / 表格 / 代码块）|
| `publish_wechat.py` | 公众号草稿箱（API 直传，7 图 + 封面）|
| `verify_draft.py` | 回读草稿核对：round-trip 纯文本一致 + 图/表/h2/图注/关键句 |
| `_delete_old_draft.py` | 删掉被取代的旧草稿（正文改过就删，避免同名两份）|
| `img/` | 7 张正文图 + cover.png |
| `dist/` | 各平台草稿源 + `publish-report.md`（由文本创作智能体生成）|

## 复现

```cmd
cd projects\style_post
..\..\.venv\Scripts\python.exe make_cover.py       # 封面
..\..\.venv\Scripts\python.exe check_article.py     # 数字自检，必须 0 失败
..\..\.venv\Scripts\python.exe make_source.py       # 多平台真源
..\..\.venv\Scripts\python.exe publish_wechat.py    # 公众号草稿（只建草稿，不群发）
..\..\.venv\Scripts\python.exe verify_draft.py      # 回读核对
```

数据侧（先跑，报告和文章都依赖它）：

```cmd
cd /d <repo>
.venv\Scripts\python.exe projects\csi300_lgbm\tools\track_pnl.py
.venv\Scripts\python.exe tools\industry_bias_heatmap.py --refresh
.venv\Scripts\python.exe projects\csi300_lgbm\tools\build_update_report.py
.venv\Scripts\python.exe projects\csi300_lgbm\tools\render_update_png.py
```

## 数字口径

| 数字 | 出处 |
|---|---|
| 组合净值 / 收益率 / 超额 | `projects/csi300_lgbm/results/track_pnl.csv`（腾讯不复权日线 + 东财分红表）|
| 20 只持仓明细、权重 | `projects/csi300_lgbm/results/track_positions_latest.csv` |
| 行业归属（申万一级）| `data/sw_industry/map.parquet`（官方 PIT 成分）|
| BIAS6/20/60/120 截面 | `data/sw_industry/bias/bias_snapshot.csv` |
| BIAS 分位、传媒 11-11 的历史值 | `data/sw_industry/index_daily/*.parquet` 现算（`check_article.py` 复算）|

## 交叉校验

11-20 收盘价用**东财 push2** 独立复核 6 只（天孚 102.18 / 芯原 76.90 / 东山 67.60 /
中信 9.66 / 蓝思 22.98 / 沪深300 3954.57），与腾讯**逐位一致**；
行业涨跌用成分股验证（传媒 11-05→11-20：芒果超媒 -17.2%、完美世界 -22.6%、光线传媒 -19.7%）。

## 发布状态

见 [`dist/publish-report.md`](dist/publish-report.md)。**全部停在草稿箱，没有任何一份被公开发布**
（发布动作留给 Curren）。
