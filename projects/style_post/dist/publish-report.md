# 发布回执：策略收益 × 行业乖离率归因（2026-11-21）

> 标题：两周亏 8.18%：我把 31 个行业的乖离率算了一遍，问题不在选股（34 字，五平台同一份）
> 状态：**6 个平台全部停在草稿箱，没有任何一份被公开发布**
> 真源：`src/article.md`（front matter 来自 `front_matter.yaml`）
> 逐个实发，日志：`dist/publish-<平台>.log`；**publish 每个平台只跑了 1 次**（核图从日志数，没有重跑）
> 本文件是**事后按各平台回执拼的**——`publish.py` 每发一个平台就覆盖一次 `dist/publish-report.md`，
> 最后只剩 bilibili 一段（坑：别指望它留全量回执）。

## 汇总

| # | 平台 | 草稿 | 链接 | 图 | 缺段 | 封面 |
|---|---|---|---|---|---|---|
| 1 | 知乎 | ✓ | https://zhuanlan.zhihu.com/p/2107418038874252958/edit | **7/7** | 0 | 手填 |
| 2 | CSDN | ✓ | https://editor.csdn.net/md?articleId=171141543 | **6/8** ⚠️ | 0 | 自动取首图 |
| 3 | 掘金 | ✓ | https://juejin.cn/editor/drafts/7710328862060363826 | **7/7** | 0 | 手填（适配器写死空串）|
| 4 | 百家号 | ✓ | https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=1882432603247893541 | **7/7** | 0 | 手填 |
| 5 | B站专栏 | ✓ | https://member.bilibili.com/platform/upload/text/edit?aid=375814 | **7/7** | 0 | 手填（无封面字段）|
| — | 微信公众号 | ✓ | `media_id 633r9_pjAyxR8atzJ8UNcieRQw-k9MVl-HORx7w5ZC_Vj_MQO5R9x3aImGNjWLMQ` | 7+封面 | — | 已上传 |

**⚠️ CSDN 有 2 张图没传上去**：`bias_percentile.png`、`rotate.png`，报错
`Failed to execute 'json' on 'Response': Unexpected end of JSON input`（CSDN `media/uploadimg` 的老毛病）。
草稿已存在，但正文里这两张是坏的 → **发布前需在 CSDN 编辑器里手动补这 2 张图**。
**不要为了补图重跑 publish**（会新建第二份草稿 + 撞「文章频繁发布」限流）。

## 校验

**本项目自己跑的三个校验（全部通过）**

```
check_article.py   数字自检 117 项，0 失败      ← 正文每个数都从源文件复算
check_dist.py      5 个平台：图 7/8/7/7/7 缺失 0 · h2 9 · 表格行 46 · 代码块 0 · 问题 0 处
check_numbers.py   数字序列：真源 391 个，5 个平台逐个连续匹配 ✓（只有导语/版权块多出前后缀）
verify_draft.py    公众号回读：round-trip 1.0000 · 7/7 mmbiz 图 · 6 表 · 9 h2 · 图注 7/7 · 关键句 5/5
```

**核图**（从 `dist/publish-*.log` 数 `✓ 上传` / `✗ 失败`）：

```
zhihu      ✓ 上传 7   ✗ 失败 0
csdn       ✓ 上传 6   ✗ 失败 2   ← bias_percentile.png / rotate.png
juejin     ✓ 上传 7   ✗ 失败 0
baijiahao  ✓ 上传 7   ✗ 失败 0
bilibili   ✓ 上传 7   ✗ 失败 0
```

**结构一致性**：五平台 h2 = 9、表格行 = 46、代码块 = 0，与真源一致；
每平台只在正文首部加了 `platform_notes` 导语、尾部加了 `footer_note` 版权块，属预期差异。

**数字一致性**：真源 391 个数字，五平台**逐个逐序完全一致**——正文里没有一个数被改过
（正文里每个数（-8.18% / -6.89pct / 58.6% / -43.8% / -32.9% / 95 / 256,525 / 235,555 / 7.92% 等）都过了 `check_article.py` 复算）。

## 还要人工做的（按平台）

1. **知乎** `p=2107418038874252958`
   - 话题标签 ≤5：量化 / 数据分析 / qlib / A股 / 投资——**话题必须真实存在**，`qlib` 搜不到就换「量化交易」；
   - 摘要、封面（`img/cover.png`）、专栏（技术）。
2. **CSDN** `articleId=171141543`
   - **补 2 张图**（`bias_percentile.png`、`rotate.png`）；
   - 摘要填「两周亏 8.18%：风格暴露的账单」（17/20 字，已在适配里填好也别删）；
   - 标签 ≤5、专栏**必须选账号下真实存在的**（否则拒稿）；
   - 发布后回查是否真过机审。
3. **掘金** `drafts/7710328862060363826`
   - 封面手填（适配器 `cover_image:""` 写死）、标签、分类专栏。
4. **百家号** `article_id=1882432603247893541`
   - 标签（≤5）、摘要、封面、分类（技术）；标题 34/40 字；
   - 发布前看一眼正文尾部版权块有没有被编辑器吃掉。
5. **B站专栏** `aid=375814`
   - **封面必须手动传**（适配器 body 里没有封面字段）；
   - 正文 7 张图这次**自动上传成功（7/7）**；
   - 分区 `tid` 写死 `4`，按「科技 → 计算机技术」核对。
6. **微信公众号** `media_id 633r9_pjAyxR8...cLWMQ`
   - 正文 7 图 + 封面已上传，round-trip 1.0000；
   - **「勾原创」接口设不了，必须在编辑器手动点**；
   - 标题、摘要、封面已填好，确认无误再群发。
7. **六个平台共同**：确认无误后由 Curren 自己点发布；本流程只到草稿箱。

## 本次踩坑记录

- **CSDN `media/uploadimg` 又是 2 张失败**（上一期是 5/5 全过，这期 6/8）——同一个接口时好时坏，
  报错形态是 `Unexpected end of JSON input`；**不重跑**（会产生废稿 + 限流），改由人工补图。
- **`publish-report.md` 被逐平台覆盖**：发完 5 个平台后，文件里只剩最后一个平台（bilibili）的回执。
  → **事后按日志拼**（本文件就是这么来的）。
- **核图的正确姿势**：把 `publish.py` 的 stdout 重定向到 `dist/publish-<平台>.log`
  （`set PYTHONIOENCODING=utf-8` 防 cp936 把 ✓ 写崩），事后从日志数行，一次发布即可拿到图数。
- **正文加粗里的句末标点要挪到加粗外**（本期 14 处，`fix_bold.py`），改前后数字序列 400 个一致。
- **`front_matter.summary` 压到 20 字以内**（本期「两周亏 8.18%：风格暴露的账单」），
  CSDN 摘要硬上限 20 字，写长了只能截成带省略号的残句。
- **公众号草稿改了正文就要删旧稿**（`draft/delete`）：同名两份草稿会让人不知道该发哪份。
