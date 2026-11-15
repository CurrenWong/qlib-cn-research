# 行业乖离率长文（公众号 + 多平台）

把 `tools/industry_bias_heatmap.py` 的三张图（截面 / 时间 / 分位）和仓库里三个策略的
真实结局，写成一篇对外文章。

> 正文：[`article.md`](article.md)（公众号真源，带【插图】标记）
> 多平台源：[`src/article.md`](src/article.md)（front matter + 标准 markdown 图片）

## 文件

| 文件 | 作用 |
|---|---|
| `article.md` | 公众号真源（4 张插图用 `【插图 N：路径｜图注】` 标记）|
| `front_matter.yaml` | 多平台头部参数 + 各平台副标题提示 |
| `make_source.py` | `article.md` → `src/article.md` + `src/img/` |
| `make_cover.py` | 生成封面 1080×864（背景是把 `bias_snapshot.csv` 的 31×4 直接重画成无标签色带）|
| `check_article.py [path]` | **数字自检 46 项**：从数据/结果文件重新读数，核对正文里的每个数（可传任意分发包路径）|
| `check_dist.py` | 核验 5 个分发包：图片引用能否解析、h2/表格/代码块是否齐 |
| `publish_wechat.py` | 公众号草稿箱（API 直传，4 图 + 封面）|
| `verify_draft.py` | 把草稿拉回来核对：round-trip 纯文本一致 + 图/表/h2 + 图注与关键句齐全 |
| `_diff_draft.py` | 调试用：打印回传正文与本地 HTML 的逐字差异（查 round-trip 不齐时用）|
| `img/` | 4 张正文图 + cover.png |
| `dist/` | 各平台草稿源（由文本创作智能体生成）|

## 复现

```cmd
cd projects\bias_post
..\..\.venv\Scripts\python.exe make_cover.py       # 封面
..\..\.venv\Scripts\python.exe check_article.py     # 数字自检，必须 0 失败
..\..\.venv\Scripts\python.exe make_source.py       # 多平台真源
..\..\.venv\Scripts\python.exe publish_wechat.py    # 公众号草稿（只建草稿，不群发）
```

## 数字口径

| 数字 | 出处 |
|---|---|
| 31 行业 BIAS6/20/60/120 | `data/sw_industry/bias/bias_snapshot.csv`（`industry_bias_heatmap.py` 产出）|
| 9-30 → 11-11 区间涨跌、分位 | `data/sw_industry/index_daily/*.parquet` 现算（`check_article.py` 复算）|
| 沪深300 −6.47% | 腾讯 kline（sh000300，4357.62 → 4075.71），缓存见 `data/sw_industry/_hs300_period.txt` |
| LightGBM 验证期/测试期 | `projects/csi300_lgbm/results/backtest.json` |
| 多因子混合各组合 | `projects/trend_combo/results/backtest.json` |
| 实盘 20 只两天 −4.43% | `projects/csi300_lgbm/report/pnl_20261103.md` + `results/pnl_monday.json` |

## 一个纠正

早前记忆里写「9-30→11-11 沪深300 −8.2%」，这次用腾讯日线重算为 **−6.47%**（4357.62 → 4075.71），
以本文的 −6.47% 为准。旧数字作废。

## 发布状态

全部停在草稿箱，没有任何一份被公开发布（发布动作留给 Curren）。

| 平台 | 草稿链接 | 图 | 校验 |
|---|---|---|---|
| 微信公众号 | `media_id 633r9_pjAyxR8atzJ8UNcmRgHYNjeT5U5vG-KwACDUms6vlsLdshHv4wwnYL-ODT` | 4 + 封面 | `verify_draft.py` round-trip **1.0000**、4/4 mmbiz、4 表格、8 h2、图注 4/4、关键句 5/5 |
| 知乎 | https://zhuanlan.zhihu.com/p/2105336979625863058/edit | 4/4 | `check.py --strict` 通过；数字复核 45/45 |
| CSDN | https://editor.csdn.net/md?articleId=170816974 | 5/5（多一张自动插入的封面首图）| 同上 |
| 掘金 | https://juejin.cn/editor/drafts/7708141298792267803 | 4/4 | 同上 |
| 百家号 | https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=1881912333098448508 | 4/4 | 同上 |
| B站专栏 | https://member.bilibili.com/platform/upload/text/edit?aid=374964 | 4/4 | 同上 |

`check_dist.py`：5 个包 图片引用全解析、h2 全为 8、表格行 26、代码块 1，问题 0 处。

**需要人工补的**：知乎/百家号/掘金的标签、摘要、封面、专栏；B站封面必须手传（无接口）；
CSDN 摘要用 20 字版、专栏要选账号下真实存在的分类。详见 `dist/publish-report.md`。
