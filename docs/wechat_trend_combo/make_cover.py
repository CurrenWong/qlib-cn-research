"""生成公众号封面（1080×864）：深色底 + 策略净值曲线 + 两行大标题。"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent
OUT = HERE / "img"
OUT.mkdir(exist_ok=True)
NAV = Path(r"D:\Project\qlib\projects\trend_combo\results\nav_curves.parquet")

fig = plt.figure(figsize=(10.8, 8.64), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), 1, 1, color="#111A26"))

# 背景：测试期净值曲线（策略 vs 沪深300）
try:
    nav = pd.read_parquet(NAV)
    for col, c, lw in [("策略(验证期选参) top50", "#E67E22", 2.2),
                        ("沪深300买入持有", "#5D6D7E", 1.3)]:
        if col in nav.columns:
            s = nav[col].dropna()
            s = s / s.iloc[0]
            y = s.values
            x = np.linspace(0.06, 0.94, len(y))
            lo, hi = y.min(), y.max()
            yy = 0.30 + (y - lo) / (hi - lo) * 0.26
            ax.plot(x, yy, color=c, lw=lw, alpha=0.9)
            if col.startswith("策略"):
                ax.fill_between(x, 0.30, yy, color=c, alpha=0.07)
except Exception as e:  # noqa: BLE001
    print("nav 读取失败，跳过背景曲线:", e)

ax.add_patch(plt.Rectangle((0.08, 0.735), 0.055, 0.006, color="#E67E22"))

ax.text(0.08, 0.690, "方向定错了，信号就是反的", fontsize=37, color="#FFFFFF",
        fontweight="bold", va="top")
ax.text(0.08, 0.588, "45 个因子 + 基本面，混出来的趋势分", fontsize=31,
        color="#FFFFFF", fontweight="bold", va="top")

ax.text(0.08, 0.487, "先验方向 IC −0.0074   →   自动定向 +0.0332", fontsize=19,
        color="#E67E22", va="top")
ax.text(0.08, 0.428, "测试期年化 +5.87%，但全区间只有 +2.10%", fontsize=19,
        color="#BDC3C7", va="top")

ax.text(0.08, 0.075, "qlib ｜ 沪深300 时点成分 ｜ 637 只", fontsize=14,
        color="#7F8C8D", va="bottom")
ax.text(0.92, 0.075, "2026.11", fontsize=14, color="#7F8C8D", va="bottom", ha="right")

fig.savefig(OUT / "cover.png", facecolor="#111A26")
plt.close(fig)
print("cover ok:", OUT / "cover.png", f"{(OUT / 'cover.png').stat().st_size / 1024:.0f} KB")
