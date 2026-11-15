"""生成公众号封面（1080×864）。

背景不是装饰图，是把 bias_snapshot.csv 的 31×4 乖离率直接重画成一条无标签色带，
裁掉所有数字——远看是色块，近看是真的数据。
"""

from pathlib import Path

import matplotlib

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent
SNAP = Path(_ROOT + r"/data/sw_industry/bias/bias_snapshot.csv")
OUT = HERE / "img" / "cover.png"

df = pd.read_csv(SNAP, index_col=0, encoding="utf-8-sig")
mat = df[["6", "20", "60", "120"]].to_numpy(dtype=float)[::-1]  # 原表按 BIAS20 降序

fig = plt.figure(figsize=(10.8, 8.64), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color="#0E1622"))

# 色带：31 行 × 4 列，直接来自真实数据
norm = TwoSlopeNorm(vcenter=0.0, vmin=-33.0, vmax=8.0)
strip = fig.add_axes([0.0, 0.0, 1.0, 0.30])
strip.imshow(mat, cmap="RdYlBu_r", norm=norm, aspect="auto", interpolation="nearest")
strip.set_xticks([])
strip.set_yticks([])
for s in strip.spines.values():
    s.set_visible(False)
# 一条细的分隔线，代替之前的渐变过渡
ax.plot([0, 1], [0.305, 0.305], color="#2C3E50", lw=1.2, zorder=5)

ax.add_patch(Rectangle((0.075, 0.885), 0.06, 0.007, color="#E67E22", zorder=5))

ax.text(0.075, 0.845, "31 个行业，一张乖离率热力图", fontsize=37, color="#FFFFFF",
        fontweight="bold", va="top", zorder=6)
ax.text(0.075, 0.745, "传媒最拥挤，通信最疼", fontsize=37, color="#FFFFFF",
        fontweight="bold", va="top", zorder=6)

ax.text(0.075, 0.625, "6 周里 26 个行业下跌，头尾差 37 个百分点", fontsize=18,
        color="#E67E22", va="top", zorder=6)
ax.text(0.075, 0.565, "外加三个跑过的策略：验证期 IR 1.22，测试期 -0.07", fontsize=18,
        color="#BDC3C7", va="top", zorder=6)

ax.text(0.075, 0.345, "qlib ｜ 申万一级行业 ｜ 乖离率 BIAS", fontsize=14,
        color="#C8D0D8", va="bottom", zorder=6)
ax.text(0.925, 0.345, "2026.11 · 数据截至 11-11", fontsize=14, color="#C8D0D8",
        va="bottom", ha="right", zorder=6)

fig.savefig(OUT, facecolor="#0E1622")
plt.close(fig)
print("cover ok:", OUT, OUT.stat().st_size, "bytes")
