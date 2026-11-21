"""生成公众号封面（1080×864）。封面里不放装饰图：

- 中间：组合 vs 沪深300 的净值曲线（真实数据，projects\\csi300_lgbm\\results\\track_pnl.csv）
- 下方：31 个申万一级行业的 BIAS120 色条（真实数据，data\\sw_industry\\bias\\bias_snapshot.csv）
远看是图，近看全是数据。
"""

import os
from pathlib import Path

import matplotlib

_ROOT = os.environ.get("QLIB_ROOT") or str(Path(__file__).resolve().parents[2])

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent
TRK = Path(_ROOT) / "projects" / "csi300_lgbm" / "results" / "track_pnl.csv"
SNAP = Path(_ROOT) / "data" / "sw_industry" / "bias" / "bias_snapshot.csv"
OUT = HERE / "img" / "cover.png"

trk = pd.read_csv(TRK)
trk["date"] = pd.to_datetime(trk["date"])
snap = pd.read_csv(SNAP, index_col=0, encoding="utf-8-sig")
bias120 = snap["120"].astype(float).sort_values()

fig = plt.figure(figsize=(10.8, 8.64), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color="#0E1622"))

# ---------- 标题 ----------
ax.add_patch(Rectangle((0.075, 0.905), 0.06, 0.007, color="#E67E22", zorder=5))
ax.text(0.075, 0.865, "两周亏 8.18%", fontsize=40, color="#FFFFFF", fontweight="bold",
        va="top", zorder=6)
ax.text(0.075, 0.775, "问题不在选股，在风格", fontsize=40, color="#FFFFFF", fontweight="bold",
        va="top", zorder=6)
ax.text(0.075, 0.690, "58.6% 的仓位，压在最超卖的两个行业上", fontsize=19,
        color="#E67E22", va="top", zorder=6)

# ---------- 净值曲线 ----------
curve = fig.add_axes([0.075, 0.395, 0.85, 0.255])
curve.set_facecolor("#0E1622")
for s in curve.spines.values():
    s.set_visible(False)
curve.set_yticks([])
curve.set_xticks([])
x = np.arange(len(trk))
curve.plot(x, trk["bench_ret_from_open_pct"], color="#95A5A6", lw=2.2, ls="--",
           label="沪深300")
curve.plot(x, trk["ret_pct"], color="#E67E22", lw=3.0, label="组合")
curve.axhline(0, color="#2C3E50", lw=1)
curve.text(0.005, 0.06, "沪深300", color="#95A5A6", fontsize=11, transform=curve.transAxes)
curve.text(0.005, 0.86, "组合", color="#E67E22", fontsize=12, transform=curve.transAxes)
curve.text(len(x) - 0.4, trk["ret_pct"].iloc[-1] - 1.2, "-8.18%",
           color="#E67E22", fontsize=15, fontweight="bold", ha="right")
curve.set_ylim(min(trk["ret_pct"].min(), trk["bench_ret_from_open_pct"].min()) - 1.5,
               max(trk["ret_pct"].max(), trk["bench_ret_from_open_pct"].max()) + 1.5)

# ---------- 31 个行业的 BIAS120 色条 ----------
strip = fig.add_axes([0.075, 0.235, 0.85, 0.075])
strip.set_facecolor("#0E1622")
vals = bias120.values
cmap = plt.get_cmap("RdYlBu_r")
norm = plt.Normalize(vmin=float(vals.min()), vmax=float(vals.max()))
strip.bar(np.arange(len(vals)), 1.0, color=cmap(norm(vals)), width=0.86)
strip.set_xlim(-0.6, len(vals) - 0.4)
strip.set_ylim(0, 1)
strip.set_xticks([])
strip.set_yticks([])
for s in strip.spines.values():
    s.set_visible(False)
strip.text(-0.5, 1.45, "31 个申万一级行业 BIAS120（红＝在 120 日均线上方，蓝＝在下方）",
           color="#C8D0D8", fontsize=12, va="bottom")
strip.text(len(vals) - 0.5, 1.45, "通信 -43.8%   电子 -32.9%   银行 +11.9%",
           color="#E67E22", fontsize=12, va="bottom", ha="right")

ax.plot([0.075, 0.925], [0.205, 0.205], color="#2C3E50", lw=1.2, zorder=5)

ax.text(0.075, 0.135, "qlib ｜ 申万一级行业 ｜ 乖离率 BIAS ｜ 风格归因", fontsize=14,
        color="#C8D0D8", va="bottom", zorder=6)
ax.text(0.925, 0.135, "2026.11 · 数据截至 11-20", fontsize=14, color="#C8D0D8",
        va="bottom", ha="right", zorder=6)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, facecolor="#0E1622")
plt.close(fig)
print("cover ok:", OUT, OUT.stat().st_size, "bytes")
