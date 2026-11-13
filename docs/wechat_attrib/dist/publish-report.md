# 发布回执 · 财报出来就跌？我把两家公司的 1347 次大波动都归因了一遍

标题：财报出来就跌？我把两家公司的 1347 次大波动都归因了一遍（30 字，五平台均未截断）

> 数据来源：2026-10-30 实际 CLI 输出。CLI 在「平台级」一律报
> `同步完成: 1 成功`，但**图片是逐张上传的，挂了不影响平台级判定**——所以下面单独列图片。
> 全部停在**草稿箱**，未发布、未群发。

## 汇总

| 平台 | 草稿 | 草稿链接 | 图片 | 封面 | 需人工手填 |
|---|---|---|---|---|---|
| 知乎 | ✓ | https://zhuanlan.zhihu.com/p/2099431927824508831/edit | 7/7 | 需手动设 | 话题标签（5 个）、摘要、封面、分类/专栏 |
| CSDN | ✓（3 份，建议留第 1 份） | https://editor.csdn.net/md?articleId=169536164 | 7/8（缺 `img/fig2_evidence.png`） | 自动取首图（cover.png 已插正文首） | 标签（≤5）、摘要（≤20 字）、分类专栏（必须是账号下真实专栏） |
| 百家号 | ✓ | https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=1880436109466605481 | 7/7 | 走 CLI | 标签（≤5）、摘要、分类 |
| 掘金 | ✓ | https://juejin.cn/editor/drafts/7701991107366928393 | 7/7 | 走 CLI（已传绝对路径 cover.png） | 标签（≤5）、摘要、分类 |
| B站专栏 | ✓ | ~~aid=373162~~ → **aid=373414**（11-01 重推，7/7 图） | **7/7（11-01 修复后）** | 走 CLI | 标签（≤5）、分区、封面 |

## 明细

### ✓ 知乎 — 7/7

https://zhuanlan.zhihu.com/p/2099431927824508831/edit

```
✓ 上传: img/fig0_pipeline.png  ✓ fig2_evidence  ✓ fig5_goodnews  ✓ fig6_jac_events
✓ 上传: img/fig3_categories.png ✓ fig4_limit    ✓ fig1_panorama
图片上传完成: 7 成功, 0 失败
```
`check.py` 报「图片引用 7 处」，一致。

> 适配警告（1 条，非阻断）：标题前 30 字没带关键词
> `['新闻归因','qlib','涨停','利好出尽','科大讯飞','江淮汽车']`——知乎搜索命中会弱一点，
> 但按"不许另起标题"的约束**未改标题**，仅记录。

### ⚠ CSDN — 7/8（第一份草稿）

- 第 1 份（**建议保留这份**）：https://editor.csdn.net/md?articleId=169536164 — 7/8，缺 `img/fig2_evidence.png`
  ```
  ✗ 失败: img/fig2_evidence.png - Failed to execute 'json' on 'Response': Unexpected end of JSON input
  ```
- 第 2 份（多出来的，建议删除）：https://editor.csdn.net/md?articleId=169536250 — 5/8，缺 `img/fig0_pipeline.png`、`img/fig5_goodnews.png`、`img/fig1_panorama.png`
- 第 3 份（多出来的，建议删除）：https://editor.csdn.net/md?articleId=169536691 — 4/8，缺 `cover.png`、`img/fig0_pipeline.png`、`img/fig5_goodnews.png`、`img/fig3_categories.png`

CSDN 的 `media/uploadimg` 本次每轮随机挂掉 1~4 张（`Unexpected end of JSON input` = 接口返回空，瞬时失败），
且两次撞到平台级限流 `文章频繁发布，请稍后再试`（那两次被判 0 成功，未生成草稿）。
共试 5 次，**没有一次拿到 8/8**，已停手，不再刷草稿。
其中一次 8 张图全传成功但被限流拒绝建文，说明图片链路本身没坏，是建文接口在限流。

### ✓ 百家号 — 7/7

https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=1880436109466605481

```
图片上传完成: 7 成功, 0 失败
```

### ✓ 掘金 — 7/7

https://juejin.cn/editor/drafts/7701991107366928393

封面走 `--cover D:\Project\qlib\docs\wechat_attrib\dist\juejin\cover.png`（绝对路径），CLI 显示 `封面: (本地图片)`。

### ⚠ B站专栏 — 0/7（已知故障，未修复）

https://member.bilibili.com/platform/upload/text/edit?aid=373162

```
✗ 失败: img/fig0_pipeline.png - Unexpected token '<', "<!DOCTYPE "... is not valid JSON
✗ 失败: img/fig2_evidence.png - Unexpected token '<', "<!DOCTYPE "... is not valid JSON
✗ 失败: img/fig5_goodnews.png - Unexpected token '<', "<!DOCTYPE "... is not valid JSON
✗ 失败: img/fig6_jac_events.png - Unexpected token '<', "<!DOCTYPE "... is not valid JSON
✗ 失败: img/fig3_categories.png - Unexpected token '<', "<!DOCTYPE "... is not valid JSON
✗ 失败: img/fig4_limit.png - Unexpected token '<', "<!DOCTYPE "... is not valid JSON
✗ 失败: img/fig1_panorama.png - Unexpected token '<', "<!DOCTYPE "... is not valid JSON
图片上传完成: 0 成功, 7 失败
```
即 skill 坑 15：`upcover` 接口返回 HTML（被重定向到登录/风控页）。**重试无效**，需改 adapter 重构建扩展。
B站草稿里的 7 张图位置是空的，要人工在编辑器里插 `dist\bilibili\img\` 下的 7 张图。

## 还要人工做的

| 平台 | 要做的 |
|---|---|
| 知乎 | 选**真实存在**的话题 5 个（量化/股票/数据分析/qlib/投资分析 里有的可能搜不到）；设封面 `dist\zhihu\cover.png`；摘要「江淮与讯飞1347次大波动的归因实验」 |
| CSDN | **留 articleId=169536164 这份**，删掉 169536250、169536691 两份；在保留的那份里补 `img/fig2_evidence.png`（源文件 `dist\csdn\img\fig2_evidence.png`）；填摘要（≤20 字）、标签 ≤5、分类专栏选账号下真实专栏；发完回查机审 |
| 百家号 | 填标签 ≤5、摘要、分类 |
| 掘金 | 填标签 ≤5、摘要、分类（封面已随 CLI 传） |
| B站专栏 | **7 张图全要手动插**（`dist\bilibili\img\`）；填分区、标签 ≤5、封面 |

全部停在**草稿**，没有人点发布。

---

## 2026-11-01 重推 B站（图片上传修复后）

原来的 B站 草稿 `aid=373162` 是 10-30 推的，**7 张图全挂**（那时 `uploadImage` 没套 header 规则，
`upcover` 返 412+HTML）。11-01 修好适配器后重推：

- 新草稿：https://member.bilibili.com/platform/upload/text/edit?aid=373414
- 图片：**7/7 全传**（`✓ 上传` 七条：fig0/fig2/fig5/fig6/fig3/fig4/fig1）
- 编辑器回读：iframe 内 `biliimg` 图片 **7 张**（去重后仍 7），正文 5,727 字符
- 旧草稿 `aid=373162`（0 图）**尚未删除**，确认新稿后可在 B站 草稿箱删掉

复现命令：

```bash
python skills/multi-platform-post/scripts/publish.py \
  --dist D:/Project/qlib/docs/wechat_attrib/dist --platforms bilibili
```

仍需人工：标签（量化/股票/数据分析/qlib/投资分析，≤5）、分区（技术）、封面。

---

## 2026-11-01 原地更新 B站 草稿 aid=373414（加粗修复 + 免责声明）

没有新建草稿：`POST api.bilibili.com/x/article/creative/draft/addupdate` **带 `aid`** 即原地更新
（返回 `{"code":0,"data":{"aid":373414}}`，草稿列表数量不变）。

改了两处：

1. **加粗写法修正**（详见 skill 的坑 16）：17 处 `**xxx。**` → `**xxx**。`，
   1 处**跨行加粗**合并成一行 —— CLI 的 `markdownToHtml` 用 `/\*\*(.+?)\*\*/g`，
   圆点不跨行，跨行的加粗匹配不上，`**` 会原样发给平台，那一段在编辑器里就是一堆星号。
2. **加免责声明**：`**把它当研究起点，不是买入清单**。`（句号在加粗外）

核验（服务端 `draft/view?aid=373414` 回读）：

| 项 | 更新前 | 更新后 |
|---|---|---|
| 正文长度 | 9,418 | 9,457 |
| 残留 `**` | 2（那处跨行加粗） | **0** |
| biliimg 图 | 7 | 7 |
| 管道表格残留 | 0 | 0 |
| 免责声明 | 无 | 有 |

⚠️ 手工更新正文时**必须用 marked 转 HTML**（扩展端 `core/src/lib/turndown.ts`
的 `markdownToHtml = marked.parse(md, {async:false})`），
不能用 CLI 那套手写正则 —— 正则版会把 Markdown 表格的 `|---|` 原样塞进正文。
⚠️ B站 存稿时会把 `<table>` 压平成散行（新旧一致，7 个表格在 B站 都成不了表），
想在 B站 保留表格只能进编辑器手动插表格。
