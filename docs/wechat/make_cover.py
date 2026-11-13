"""生成公众号封面（1080×864）。"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(r"D:\Project\qlib")
OUT = ROOT / "docs" / "wechat" / "img"
OUT.mkdir(parents=True, exist_ok=True)

fig = plt.figure(figsize=(10.8, 8.64), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), 1, 1, color="#111A26"))

# 背景：策略净值形状的暗线（取自方案 A）
try:
    nav = pd.read_csv(ROOT / "projects/jac_600418/results_A/nav_test.csv",
                      index_col=0, parse_dates=True)["策略"]
    y = nav.values
    x = np.linspace(0.06, 0.94, len(y))
    ymin, ymax = y.min(), y.max()
    yy = 0.10 + (y - ymin) / (ymax - ymin) * 0.22
    ax.plot(x, yy, color="#C0392B", lw=2.0, alpha=0.55)
    ax.fill_between(x, 0.10, yy, color="#C0392B", alpha=0.07)
except Exception:  # noqa: BLE001
    pass

ax.add_patch(plt.Rectangle((0.08, 0.735), 0.055, 0.006, color="#E67E22"))

ax.text(0.08, 0.685, "19 年数据，三套切分", fontsize=40, color="#FFFFFF",
        fontweight="bold", va="top")
ax.text(0.08, 0.575, "一个择时策略的三次死亡", fontsize=40, color="#FFFFFF",
        fontweight="bold", va="top")

ax.text(0.08, 0.455, "样本内 IC +0.12，样本外全灭", fontsize=19, color="#E67E22", va="top")
ax.text(0.08, 0.395, "凶手不是模型，是每年 49 倍的换手率", fontsize=19,
        color="#BDC3C7", va="top")

ax.text(0.08, 0.075, "qlib ｜ 单票择时 ｜ 江淮汽车 600418", fontsize=14, color="#7F8C8D", va="bottom")
ax.text(0.92, 0.075, "2026.10", fontsize=14, color="#7F8C8D", va="bottom", ha="right")

fig.savefig(OUT / "cover.png", facecolor="#111A26")
plt.close(fig)
print("cover ok:", OUT / "cover.png", f"{(OUT / 'cover.png').stat().st_size / 1024:.0f} KB")
