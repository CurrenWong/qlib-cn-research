# 公众号长文（新闻归因方法 + 两个标的结果）

把 `projects/jac_600418/news_attribution`（江淮）和 `projects/iflytek_002230/news_attribution`
（科大讯飞）的方法与结果，整理成一篇公众号文章。

> 正文：[`article.md`](article.md) ｜ 预览：[`article.html`](article.html) ｜ 分页截图：`shots\`

## 文件

| 文件 | 内容 |
|---|---|
| `article.md` | 正文（9 节，7 张插图）|
| `article.html` | 本地预览（720px 桌面版样式，headless Chrome 截图用）|
| `wechat_body.html` | 公众号可用的全内联样式正文（`data-src` 形式，符合微信 API 约定）|
| `compare.py` / `comparison.json` | 两个标的的**同口径**对比表（涨跌停效应、证据率、类别事件研究、全历史）|
| `make_figures.py` / `img\` | 7 张配图 + 封面（fig6_jac_events 是江淮的 8 事件走势图）|
| `build_html.py` | markdown → HTML（复用 `docs/wechat/wechat_html.py` 的样式逻辑）|
| `html2png.py` | HTML → PNG（headless Chrome + PIL 裁白 + 分页）|
| `check_article.py` | 文章数字自检（**159 项**，含"正文不得出现代码路径/复现字样"的反向检查）|
| `shots\` | `article_full.png`（整篇长图）+ `article_p1..p6.png`（分页）|

## 发布（一稿多发）

```
article.md（公众号真源，带【插图 N：…】标记）
   │ make_source.py
   ├─→ src\article.md   多平台真根源（front matter + 标准 markdown 图片）+ src\img\
   │      │ 委派「文本创作智能体」澄，用其 multi-platform-post skill
   │      └─→ dist\<平台>\ + dist\publish-report.md   知乎/CSDN/掘金/百家号/B站 **草稿箱**
   └─→ publish_wechat_attrib.py   公众号 **草稿箱**（API 直传，7 图 + 封面）
```

| 文件 | 作用 |
|---|---|
| `front_matter.yaml` | 多平台的 title / summary / tags / cover / platform_notes（改这里，不要改正文）|
| `make_source.py` | 生成 `src\article.md`：加 front matter、`【插图】`→`![](img/x.png)`、去掉重复 H1、拷图 |
| `publish_wechat_attrib.py` | 公众号草稿（stable_token → uploadimg → thumb → draft/add）|
| `verify_draft_attrib.py` | 只读核验草稿：位置/结构/纯文本逐字比对，回读存 `draft_render.html` |
| `check_dist.py` | 核对 5 个平台稿有没有被适配器改坏（段/图/h2 计数）|

**规矩**（沿用 `AGENTS.md` §8）：素材先行 → 委派 → **停在草稿，用户拍板群发**。
"勾原创"接口设不了，必须在编辑器手动点。

**核验口径**：公众号侧 `纯文本长度 local/render 一致=True` + `img = mmbiz 数 = 7`；
多平台侧 `check_dist.py` 必须 0 缺段。

## 复现

```cmd
cd /d D:\Project\qlib\docs\wechat_attrib
set "PYTHONWARNINGS=ignore"

:: 1) 两标的对撞表
..\..\.venv\Scripts\python.exe compare.py
:: 2) 配图（6 张 + 封面）
..\..\.venv\Scripts\python.exe make_figures.py
:: 3) markdown → HTML
..\..\.venv\Scripts\python.exe build_html.py
:: 4) HTML → PNG（整篇 + 分页）
..\..\.venv\Scripts\python.exe html2png.py
:: 5) 文章数字自检（125 项必须全过）
..\..\.venv\Scripts\python.exe check_article.py
```

## 踩过的坑

1. **`.wrap` 宽度要带 `box-sizing:border-box`**，否则 414px 宽度 + padding 会让内容溢出、
   右边被裁掉一截（第一版就是这么废掉的）。
2. **headless Chrome 截图的高度**：用 `--window-size=720,26000` 一次截到底，
   再用 PIL 按**页面背景色**（不是白色！）从下往上找内容底边并裁掉——
   直接找"非白像素"会把 body 的灰底当成内容，多出十几页空白。
3. **`--force-device-scale-factor=2`** 出的是 2 倍图（1440px 宽），手机上看更清楚。
4. **直引号要转中文引号**：`fix_quotes.py` 按出现顺序成对替换 `"` → `“”`；
   跑完要用 `check_quotes.py` 确认每行都配对（第一版有落单引号）。
5. **`wechat_html.py` 的表格是 `table-layout:auto`**，长内容会撑破容器；
   预览页要覆盖成 `table-layout:fixed` + `word-break:break-word`。
