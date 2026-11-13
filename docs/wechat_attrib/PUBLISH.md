# 发布记录：新闻归因文章（2026-10-30）

> 标题：财报出来就跌？两家公司、1347 次大波动，我用同一套方法去找「新闻解释了谁」
> 多平台标题（30 字）：财报出来就跌？我把两家公司的 1347 次大波动都归因了一遍
> 状态：**全部停在草稿箱，没有任何一份被发布**

## 汇总

| # | 平台 | 草稿 | 链接 | 图 | 谁做的 |
|---|---|---|---|---|---|
| 1 | 微信公众号 | ✓ | 后台草稿箱第 1 条，`media_id` 见 `wechat_draft_id.txt` | 7/7 | 本 agent（`publish_wechat_attrib.py`）|
| 2 | 知乎 | ✓ | https://zhuanlan.zhihu.com/p/2099431927824508831/edit | 7/7 | 澄（multi-platform-post）|
| 3 | CSDN | ✓（留第一份）| https://editor.csdn.net/md?articleId=169536164 | **7/8** | 澄 |
| 4 | 百家号 | ✓ | https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=1880436109466605481 | 7/7 | 澄 |
| 5 | 掘金 | ✓ | https://juejin.cn/editor/drafts/7701991107366928393 | 7/7 | 澄 |
| 6 | B站专栏 | ✓（半成品）| https://member.bilibili.com/platform/upload/text/edit?aid=373162 | **0/7** | 澄 |

公众号侧核验：`verify_draft_attrib.py` → 7 `<img>` = 7 `mmbiz.qpic.cn`、7 表格、9 个 h2、
**纯文本 5391 字与本地稿逐字一致**。

多平台侧核验：`check_dist.py` → 5 个平台稿 **0 缺段**、9 个 h2、7 图（CSDN 8 张是它自动插的封面首图）。

## 要人工收尾的（按优先级）

1. **CSDN**：保留 `169536164`，**删掉多出来的 `169536250`、`169536691`**；
   在保留的那份里补 `img/fig2_evidence.png`（源文件 `dist\csdn\img\fig2_evidence.png`）。
2. **B站专栏**：7 张图全部手动插入（`dist\bilibili\img\`），适配器的 `upcover` 接口坏了（坑 15）。
3. 各平台补**标签 / 摘要 / 分类专栏 / 封面**（见 `dist\<平台>\checklist.md`）。
4. 公众号后台手动勾「原创」。
5. 全部确认后自己点发布。

## 本次踩到的两个新坑

1. **「核图」不能靠重跑 publish**：`publish.py` 每跑一次就**新建一份草稿**。
   本次为了数 `✓ 上传` 行把 CSDN 重发了 5 次 → 多出 2 份废稿，还撞上平台限流
   `文章频繁发布，请稍后再试`。正确做法：**第一次发的时候就把 CLI 输出重定向到日志**，
   核图从日志里数，不要重跑。
2. **CSDN 的 `media/uploadimg` 会随机挂**（`Unexpected end of JSON input` = 接口返回空），
   一次 8 张图里挂 1~4 张是常态。有一次 8 张全传成功却被限流拒绝建文 →
   说明图片链路没问题，是**建文接口在限流**，此时不要再重试。

---

## 2026-11-01 修订：加粗写法 + 免责声明（B站 草稿原地更新）

- **真源 `article.md` 已改**：17 处 `**xxx。**` → `**xxx**。`、1 处跨行加粗合并成一行、
  新增 `**把它当研究起点，不是买入清单**。`（句号在加粗外）。
- **`make_source.py` 补了封面拷贝**（front_matter 的 `cover: img/cover.png` 不在【插图】标记里，
  以前不拷 → adapt 找不到封面 → dist 里没有 cover.png）。
- 重新 `make_source.py` → `adapt.py`（5 平台）→ `check.py --strict` 全绿（唯一剩的是知乎标题关键词的旧警告）。
- **B站 草稿 aid=373414 原地更新**（`draft/addupdate` 带 `aid`），没新建草稿；
  `✓ 7 张图 / 残留 ** = 0 / 免责声明在`。
- 另四个平台的草稿（知乎 2099431927824508831 / CSDN 169536164 / 百家号 1880436109466605481 /
  掘金 7701991107366928393）**还是旧正文**（含那处坏加粗），要重推的话每平台会各多一份草稿。
- 公众号草箱里的那份也是旧正文；重推要先 `build_html.py` + `html2png.py` 重建再
  `publish_wechat_attrib.py`。
