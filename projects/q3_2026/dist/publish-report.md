# 发布回执 · 讯飞 & 江淮 2026 三季报解读

标题：一份赚 2190 万，一份亏 11.41 亿——两份三季报翻到同一页（34 字，未截断）

> 数据来源：2026-10-31 实际 CLI 输出（`dist/logs/*.log`）。CLI 在「平台级」一律报
> `同步完成: 1 成功`，但**图片是逐张上传的，挂了不影响平台级判定**——所以图片单独列，
> 数字均从日志里数 `✓ 上传` / `✗ 失败`。
> **全部停在草稿箱，未点发布、未群发。** 除 CSDN 的这一次授权重试外，每个平台只调过一次 publish。

## 汇总

| 平台 | 草稿 | 图片（实际） | 封面 |
|---|---|---|---|
| 知乎 | ✓ | **6/6** | 需手动设（适配器不传） |
| CSDN（旧稿） | ✓ 169651341 | **5/7**（正文图 4/6 + cover.png；缺 fig1、fig3） | 自动取正文首图（已插 cover.png） |
| CSDN（新稿·重试） | ✓ 169651359 | **6/7**（正文图 5/6 + cover.png；缺 fig5） | 自动取正文首图（已插 cover.png） |
| 百家号 | ✓ | **6/6** | 需手动设（适配器 publish() 不传 cover） |
| 掘金 | ✓ | **6/6** | 已走 CLI `--cover`（cover.png） |
| B站专栏 | ✓ | **0/6（全挂）** | 需手动设（适配器不传 cover） |

**CSDN 两稿都不是 7/7**：旧稿缺 fig1+fig3，新稿缺 fig5。两稿都保留，由用户决定删哪张。

## 明细

### ✓ 知乎（zhihu）
- 草稿：https://zhuanlan.zhihu.com/p/2099945296721600670/edit
- 图片：6/6 全部 `✓ 上传`，0 失败
- 日志：`dist/logs/zhihu.log`

### ⚠ CSDN 旧稿（csdn，首次）
- 草稿：https://editor.csdn.net/md?articleId=169651341
- 图片：5 成功 / 2 失败（CLI 发现 7 张本地图 = 6 正文图 + adapt 自动插入的 cover.png）
- 失败文件（需在 CSDN 编辑器里手动补）：
  - `img/fig1_six_lines.png` — `Failed to execute 'json' on 'Response': Unexpected end of JSON input`
  - `img/fig3_rd_vs_nonop.png` — `Failed to execute 'json' on 'Response': Unexpected end of JSON input`
- 日志：`dist/logs/csdn.log`

### ⚠ CSDN 新稿（csdn，授权重试一次）
- 草稿：https://editor.csdn.net/md?articleId=169651359
- 图片：**6 成功 / 1 失败**（7 张本地图）
  - ✓ cover.png、✓ fig1_six_lines.png、✓ fig2_iflytek_bridge.png、✓ fig3_rd_vs_nonop.png、✓ fig4_jac_margin.png、✓ fig6_price.png
  - ✗ `img/fig5_jac_cash.png` — `Failed to execute 'json' on 'Response': Unexpected end of JSON input`
- 上次缺的两张（fig1、fig3）这次补上了，但 fig5 这次掉了。同一报错、随机命中不同图，
  是 `media/uploadimg` 接口返回空的瞬时问题。
- 按授权**只试了这一次，已停手，不再重试**。旧稿未删除。
- 本地待补图在 `dist/csdn/img/`
- 日志：`dist/logs/csdn_retry.log`

### ✓ 百家号（baijiahao）
- 草稿：https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=1880564429009290298
- 图片：6/6 全部 `✓ 上传`，0 失败
- 日志：`dist/logs/baijiahao.log`

### ✓ 掘金（juejin）
- 草稿：https://juejin.cn/editor/drafts/7702592474154090546
- 图片：6/6 全部 `✓ 上传`，0 失败
- 封面：CLI 已带 `--cover .../dist/juejin/cover.png`
- 日志：`dist/logs/juejin.log`

### ⚠ B站专栏（bilibili）
- 草稿：https://member.bilibili.com/platform/upload/text/edit?aid=373327
- 图片：**0/6，全部失败**（已知坏接口 `x/article/creative/article/upcover`，返回 HTML）
  - `img/fig1_six_lines.png` — `Unexpected token '<', "<!DOCTYPE "... is not valid JSON`
  - `img/fig2_iflytek_bridge.png` — 同上
  - `img/fig3_rd_vs_nonop.png` — 同上
  - `img/fig4_jac_margin.png` — 同上
  - `img/fig5_jac_cash.png` — 同上
  - `img/fig6_price.png` — 同上
- 按约束**只试了一次**，没有重跑。注意：适配器在图片上传失败后会把非 hdslb/bilibili
  域名的 `<img>` 整段剥掉，所以这版草稿正文里**一张图都没有**，需要手动插 6 张。
- 本地图在 `dist/bilibili/img/`
- 日志：`dist/logs/bilibili.log`

## 还要人工做的

| 平台 | 要做的 |
|---|---|
| 知乎 | 选**真实存在**的话题（财报解读 / 数据分析 / 股票 / 量化 / 科大讯飞）；设封面 `dist/zhihu/cover.png`；填摘要、分类专栏 |
| CSDN（新稿 169651359） | 补 `img/fig5_jac_cash.png`（`dist/csdn/img/`）；填标签（≤5）、摘要（≤20 字）、分类专栏；发完回查是否真过机审；**旧稿 169651341 自行决定是否删除** |
| 百家号 | 设封面（适配器不传）；填标签（≤5）、摘要、分类专栏 |
| 掘金 | 填标签（≤5）、摘要、分类专栏 |
| B站专栏 | 手动插入 6 张正文图（`dist/bilibili/img/`，按 fig1→fig6 顺序）；设封面；填标签（≤5）、摘要、分类专栏 |

字段清单见各平台 `dist/<平台>/checklist.md`。适配器把 tags / categories / cover
写死成空串，wechatsync CLI 也只从 front matter 取 `title`，所以这几项**只能人工填**。

## 日志路径

| 平台 | 日志 |
|---|---|
| 知乎 | `D:\Project\qlib\projects\q3_2026\dist\logs\zhihu.log` |
| CSDN（首次） | `D:\Project\qlib\projects\q3_2026\dist\logs\csdn.log` |
| CSDN（重试） | `D:\Project\qlib\projects\q3_2026\dist\logs\csdn_retry.log` |
| 百家号 | `D:\Project\qlib\projects\q3_2026\dist\logs\baijiahao.log` |
| 掘金 | `D:\Project\qlib\projects\q3_2026\dist\logs\juejin.log` |
| B站 | `D:\Project\qlib\projects\q3_2026\dist\logs\bilibili.log` |
| 预演 | `D:\Project\qlib\projects\q3_2026\dist\logs\dry-run.log` |
