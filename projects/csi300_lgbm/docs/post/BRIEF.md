# 派发给「文本创作智能体（澄）」的任务书

## 一句话

把《沪深300 × LightGBM 选股复盘》一篇文章，发到知乎 / CSDN / 掘金 / 百家号 / B站 专栏的**草稿箱**，外加微信公众号草稿。**只建草稿，不公开发布。**

## 素材位置（已全部备齐，不要改写内容）

| 项 | 路径 |
|---|---|
| 正文（真根源，带 front matter） | `D:\Project\qlib\projects\csi300_lgbm\docs\post\article.md` |
| 正文配图（10 张） | `D:\Project\qlib\projects\csi300_lgbm\docs\post\img\` |
| 封面 | `D:\Project\qlib\projects\csi300_lgbm\docs\post\cover.png`（1080×864） |

正文里的图片引用写的是 `img/xxx.png` 相对路径，和 `article.md` 同级——`adapt.py` 会自动拷贝，不用手动 xcopy。

## 文章内容摘要（供你判断，不要重写）

- 标题：沪深300 × LightGBM 选股复盘：验证期 +20.86%，测试期 -2.13%，然后我把组合改了
- 10 个正文章节 + 附录（配置对照 / 特征重要性 / 复现命令）
- 10 张图、9 张表（含 115 行表格）、1 个 bash 代码块
- 语气：直接、克制、靠数据说话。**不要改写成营销腔**，保留原有的粗体强调和"纪律提示"这类自我批评段落。

## 硬性要求

1. **只建草稿**。不要点发布、不要群发、不要定时发送。勾「原创」也留给用户自己勾。
2. **表格必须是真表格**，不能变截图。
3. **10 张图都要在位**。发完按 `✓ 上传` 的条数核对，数量对不上就记录下来（已知 B站 图片上传当前是坏的，失败就跳过并在回执里写明）。
4. **正文别改**：数字、结论、风险提示都是实测出来的；有疑问在回执里提，别自己删改。

## 执行顺序（照 skill 的七步走）

```
① python scripts/preflight.py --platforms zhihu,csdn,juejin,baijiahao,bilibili
② python scripts/adapt.py --src <上面的 article.md 绝对路径> --out <你的工作区 dist 目录> \
      --platforms zhihu,csdn,juejin,baijiahao,bilibili
③ python scripts/check.py --dist <dist 目录> --strict
④ python scripts/publish.py --dist <dist 目录> --platforms zhihu --dry-run
⑤ 逐个平台实发（一次一个）：zhihu → csdn → baijiahao → juejin → bilibili
⑥ 核图：数 "✓ 上传" 条数，和 check.py 报的"图片引用"条数对齐
⑦ 重建完整回执（模板见 references/publish-report-template.md）
```

公众号另外走 `wechat-image-post`：竖版长图 + 公众号草稿箱，同样**只建草稿**。

## 回报清单（发完必须给全）

1. 每个平台：草稿链接 + 标题 + 实际图片数 + 有没有缺图
2. 每个平台还要手填的字段（标签 / 分类专栏 / 摘要 / 封面）
3. 有没有内容被截断、表格错位、图片没传上去——直接说，别自己删改内容
4. 公众号：草稿 media_id / 草稿箱位置 / 用了几张竖版长图

如果中途某一步卡住（桥接掉了、平台掉登录、扩展连不上），**停下来报**，不要绕路硬发。
