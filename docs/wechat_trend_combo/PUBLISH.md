# 发布记录 · 方向定错了，信号就是反的（基本面 + 高频价量混合打分）

日期：2026-11-05　状态：**6 份草稿全部建好（公众号 + 5 平台），未公开发布** —— 群发由用户拍板。

- 标题：**方向定错了，信号就是反的：基本面 + 高频价量的混合打分**（28 字）
- 真根源：`docs\wechat_trend_combo\src\article.md`（正文一字未改）
- 素材来源：`projects/trend_combo`（45 因子 + 东财 PIT 基本面 + 换手成本回测）
- 图：8 张正文图 + 1 张封面（1080×864）

## 汇总

| 平台 | 草稿链接 | 图片 | 封面 | 谁建的 |
|---|---|---|---|---|
| **微信公众号** | 草稿箱第 1 条（media_id `633r9_pjAyxR8UN…`） | 8/8 | ✓ 已传 | 本项目 `publish_wechat_trend_combo.py` |
| 知乎 | https://zhuanlan.zhihu.com/p/2101591930593452990/edit | 8/8 | ✗ 需手填 | 澄（multi-platform-post） |
| CSDN | https://editor.csdn.net/md?articleId=170117605 | 9/9（8 正文 + 首图当封面） | ✓ 自动 | 澄 |
| 百家号 | https://baijiahao.baidu.com/builder/rc/edit?type=news&article_id=1880976096627170155 | 8/8 | ✗ 需手填 | 澄 |
| 掘金 | https://juejin.cn/editor/drafts/7704389851176894474 | 8/8 | ✓ CLI 已传 | 澄 |
| B站专栏 | https://member.bilibili.com/platform/upload/text/edit?aid=373819 | 8/8 | ✗ 需手填 | 澄 |

合计 **41 张图全部上传成功，0 张失败**；5 个平台与 `check.py` 报的「图片引用」条数逐个对账一致。

## 公众号这一路的核验（`verify_draft_attrib.py`）

```
草稿总数 235，位置：第 1 条（按更新时间倒序）
title 无 \u 转义；content 无 \uXXXX
img 标签 8 / mmbiz.qpic.cn 8 / data-src 8 / table 7 / h2 橙色竖线 8 / strong 56
纯文本长度 local/render : 4086 / 4086  一致=True
```

## 还要人工做的

**公众号**：草稿箱里逐项确认（封面已传、正文 8 图已传），加「原创」需在编辑器手动点，
**群发按钮别点**，等用户拍板。

**知乎**：① 话题必须搜到真实存在的话题再选（搜不到换同义词）；
② 摘要栏填「基本面×价量混合打分：IC、换手与诚实的回测」；
③ 封面手动设 `dist\trend_combo\zhihu\cover.png`；
④ 分类选「互联网」或留默认（没有「技术」这个分类）；
⑤ 适配器提示**标题前 30 字没带 keywords**，要吃搜索流量可在编辑器改成含「qlib」的版本（未自动改）。

**CSDN**：① 标签 5 个 `量化,股票,qlib,因子合成,投资分析`；② 摘要贴 20 字版「基本面×价量混合打分：IC、换手与诚实…」
（超 20 字报 45004）；③ 分类/专栏必须选账号下真实存在的专栏；④ 发布后回查机审。

**百家号**：① 标签同上；② 摘要填完整版；③ 分类选「科技」或「财经」；④ 封面手动设 `dist\trend_combo\baijiahao\cover.png`。

**掘金**：① 标签同上；② 摘要填完整版；③ 分类选真实专栏；④ 封面 CLI 已传，打开确认不空白；
⑤ 正文 42 行表格在编辑器里扫一眼渲染。

**B站专栏**：① 标签同上；② 摘要填完整版；③ 分类选对应分类；④ 封面手动设 `dist\trend_combo\bilibili\cover.png`。

**跨平台统一**：源 front matter 写了 6 个标签，5 个平台上限都是 5 个 → **「Python」被截掉**；
要留 Python 就手动替掉一个（例如把「股票」换成「Python」），五个平台都要改。
标签/分类/摘要/封面这四项适配器一律不传，草稿里现在是空的，只能在平台编辑器手填。

## 复现与坑

```cmd
cd /d D:\Project\qlib\docs\wechat_trend_combo
..\..\.venv\Scripts\python.exe make_cover.py && ..\..\.venv\Scripts\python.exe make_source.py
..\..\.venv\Scripts\python.exe fix_bold.py            :: 加粗里的句末标点 / 跨行加粗（本次修掉 12 处）
..\..\.venv\Scripts\python.exe build_html.py && ..\..\.venv\Scripts\python.exe html2png.py
..\..\.venv\Scripts\python.exe publish_wechat_trend_combo.py > publish_wechat.log 2>&1
..\..\.venv\Scripts\python.exe verify_draft_attrib.py
..\..\.venv\Scripts\python.exe check_dist_trend.py    :: 各平台稿 vs 真根源（本次 5 平台缺段均为 0）
```

- **别为了核图重跑 publish**：每跑一次就多一份草稿，还会撞「文章频繁发布，请稍后再试」限流；
  第一次就把 CLI 输出重定向到日志（`publish-<platform>.log`），`✓ 上传` 行从日志里数。
- **加粗里的句末标点会让部分平台的 Markdown 解析器整段失效** → 本项目用 `fix_bold.py` 先修掉
  （本次 12 处），`check.py --strict` 也复查这一项。
- **CSDN 的封面自动取正文首图**，所以它上传 9 张、其余平台 8 张，这是正常差异，不是漏图。
