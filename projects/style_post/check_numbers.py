"""核对 5 个分发包里的数字是否与真源一致（正文数字不能被改）。

做法：抽 `[-+]?\\d+(\\.\\d+)?` 序列；真源去掉 front matter 后的序列，
必须作为**连续子序列**出现在分发包里（平台导语在头部、版权块在尾部，允许多出前后缀）。
"""
import re
from pathlib import Path

HERE = Path(r"projects\style_post")
NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")
PLATFORMS = ["zhihu", "csdn", "juejin", "baijiahao", "bilibili"]


def body(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        text = parts[2] if len(parts) > 2 else text
    return text


src_nums = NUM.findall(body((HERE / "src" / "article.md").read_text(encoding="utf-8")))
print(f"真源 src/article.md 数字 {len(src_nums)} 个")

bad = 0
for p in PLATFORMS:
    f = HERE / "dist" / p / "article.md"
    if not f.exists():
        print(f"{p:10} 缺文件")
        bad += 1
        continue
    nums = NUM.findall(body(f.read_text(encoding="utf-8")))
    # 找 src 序列在 nums 中的连续位置
    hit = -1
    for i in range(0, len(nums) - len(src_nums) + 1):
        if nums[i:i + len(src_nums)] == src_nums:
            hit = i
            break
    if hit < 0:
        print(f"{p:10} ✗ 数字序列对不上（包内 {len(nums)} 个）")
        # 找第一处不一致
        for i in range(min(len(nums), len(src_nums))):
            if nums[i] != src_nums[i]:
                print(f"           首个差异 #{i}: 包 {nums[i]} vs 源 {src_nums[i]}")
                break
        bad += 1
    else:
        print(f"{p:10} ✓ 数字一致（前置 {hit} 个 / 后置 {len(nums)-hit-len(src_nums)} 个）")
print("结论:", "全部一致 ✅" if bad == 0 else f"{bad} 个平台不一致 ❌")
