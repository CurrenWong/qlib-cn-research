# wechat_trend_combo —— 公众号长文：基本面 × 高频价量 混合打分

素材来自 `projects/trend_combo`（45 因子 + 东财 PIT 基本面 + 换手成本回测），
按本仓库公众号流程改写成适合手机阅读的长文，并一稿多发到 5 个平台草稿箱。

## 文件

| 文件 | 作用 |
|---|---|
| `article.md` | **公众号正文真源**（【插图 N：img/x.png｜图注：…】标记，8 图 7 表，约 5800 字） |
| `front_matter.yaml` | 多平台头部参数（title / summary / tags / cover / keywords / platform_notes） |
| `img/` | 8 张配图 + `cover.png`（1080×864） |
| `make_cover.py` | 生成封面（深色底 + 测试期净值曲线） |
| `make_source.py` | `article.md` → `src/article.md`（带 front matter，图片转标准 markdown） |
| `build_html.py` | `article.md` → `article.html`（本地预览）+ `wechat_body.html`（公众号全内联正文） |
| `html2png.py` | `article.html` → `shots/article_p*.png`（本地排版检查） |
| `fix_bold.py` | 修掉「加粗里带句末标点」「跨行加粗」两个坑（多平台 Markdown 解析器会整段失效） |
| `publish_wechat_trend_combo.py` | 推进**公众号草稿箱**（只建草稿，不群发） |
| `verify_draft_attrib.py` | 只读核验公众号草稿（位置 / 结构计数 / 纯文本逐字比对） |
| `check_dist.py` | 比对真根源与各平台适配稿（是否缺段） |
| `src/` | 生成物：多平台真根源 + 图片 |
| `dist/trend_combo/` | 生成物：各平台适配稿 + 草稿回执 |
| `shots/` | 生成物：本地排版预览长图 |

## 复现

```cmd
cd /d docs\wechat_trend_combo
..\..\.venv\Scripts\python.exe make_cover.py        :: 封面
..\..\.venv\Scripts\python.exe make_source.py       :: → src\article.md + src\img\
..\..\.venv\Scripts\python.exe fix_bold.py          :: 修加粗里的句末标点 / 查跨行加粗
..\..\.venv\Scripts\python.exe build_html.py        :: → article.html + wechat_body.html
..\..\.venv\Scripts\python.exe html2png.py          :: → shots\article_p*.png（排版检查）

:: 公众号草稿（需要 WECHAT_APP_ID / WECHAT_APP_SECRET 环境变量）
..\..\.venv\Scripts\python.exe publish_wechat_trend_combo.py > publish_wechat.log 2>&1
..\..\.venv\Scripts\python.exe verify_draft_attrib.py
```

多平台（知乎 / CSDN / 掘金 / 百家号 / B站）由「文本创作智能体」澄用
`multi-platform-post` skill 建草稿，见 `PUBLISH.md`。

## 纪律

- **只建草稿，不群发** —— 群发由用户拍板；
- 公众号正文只改 `article.md`，`src/article.md` 与各平台稿都是它的派生物；
- **别为了核图重跑 publish**（每跑一次就多一份草稿，还会撞「文章频繁发布」限流），
  第一次就把 CLI 输出重定向到日志，`✓ 上传` 行从日志里数。
