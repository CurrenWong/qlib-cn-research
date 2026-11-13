"""取数 + 特征工程：qlib 面板 → 31 个价量特征 + 前瞻标签。

设计（见 PLAN.md）：
- 股票池用**时点成分股**（csi300.txt 的 start/end 区间），不用当前 300 只回溯，避免幸存者偏差；
- cn_data 只有价量，没有基本面 → 特征全部无量纲、跨股票可比；
- 标签：未来 5 日收益（对齐周度调仓）+ 未来 1 日收益（对照）。

输出：
  data/panel.parquet      原始面板（close/open/high/low/volume，date × symbol）
  data/features.parquet   特征 + 标签（date × symbol，长表）
  data/membership.csv     时点成分区间
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\Project\qlib")
DATA = ROOT / "qlib_data" / "cn_data_2026"
HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)

START = "2014-01-01"          # 多取两年做特征预热（250 日窗口）
BACKTEST_START = "2016-01-01"
LAST = "2026-10-30"
INDEX = "SH000300"

FIELDS = ["$close", "$open", "$high", "$low", "$volume"]


def log(*a):
    print(*a, flush=True)


def load_membership():
    rows = [l.split("\t") for l in
            (DATA / "instruments" / "csi300.txt").read_text().splitlines() if l.strip()]
    mem = pd.DataFrame(rows, columns=["symbol", "start", "end"])
    mem["start"] = pd.to_datetime(mem["start"])
    mem["end"] = pd.to_datetime(mem["end"])
    # 只保留与回测区间有交集的区间（前后年份的成分不影响回测，但要留着做池子全集）
    mem = mem[(mem["end"] >= BACKTEST_START) & (mem["start"] <= LAST)].copy()
    mem.to_csv(OUT / "membership.csv", index=False)
    syms = sorted(mem["symbol"].unique())
    log(f"成分区间 {len(mem)} 条，{BACKTEST_START}~{LAST} 内出现过的股票 {len(syms)} 只")
    return mem, syms


def fetch_panel(symbols):
    import qlib
    from qlib.data import D
    qlib.init(provider_uri=str(DATA), region="cn")
    t0 = time.time()
    df = D.features(symbols, FIELDS, start_time=START, end_time=LAST, freq="day")
    log(f"D.features 取数 {time.time()-t0:.0f}s，shape={df.shape}")
    # 列是 MultiIndex (field, instrument)，行是 (instrument, datetime)
    frames = {}
    for f in FIELDS:
        sub = df[f].unstack(level=0)  # index=datetime, columns=instrument
        frames[f] = sub
    panel = pd.DataFrame({f: frames[f].stack(future_stack=True) for f in FIELDS})
    panel.index.names = ["datetime", "symbol"]
    panel = panel.sort_index()
    log(f"面板 {panel.shape}，日期 {panel.index.get_level_values(0).min().date()} ~ "
        f"{panel.index.get_level_values(0).max().date()}")
    return panel


def index_close():
    import qlib
    from qlib.data import D
    s = D.features([INDEX], ["$close"], start_time=START, end_time=LAST, freq="day")["$close"]
    s = s.unstack(level=0).iloc[:, 0]
    s.index = pd.to_datetime(s.index)
    return s


def build_features(panel, idx_close):
    """返回 (MultiIndex, {列名: 2D 数组 float32})，列顺序即长表列顺序。"""
    close = panel["$close"].unstack(level=1).sort_index().astype(float)
    open_ = panel["$open"].unstack(level=1).sort_index().astype(float)
    high = panel["$high"].unstack(level=1).sort_index().astype(float)
    low = panel["$low"].unstack(level=1).sort_index().astype(float)
    volume = panel["$volume"].unstack(level=1).sort_index().astype(float)

    ret = close.pct_change()
    idx_ret = idx_close.pct_change().reindex(close.index)
    idx_ret = idx_ret.fillna(0.0)

    F = {}
    # --- 动量 ---
    for n in (1, 5, 10, 20, 60, 120):
        F[f"mom_{n}"] = close / close.shift(n) - 1
    F["mom_5_ex"] = close.shift(1) / close.shift(6) - 1
    F["mom_20_ex"] = close.shift(1) / close.shift(21) - 1
    # --- 反转 ---
    F["rev_3"] = -(close / close.shift(3) - 1)
    F["rev_10"] = -(close / close.shift(10) - 1)
    # --- 波动 ---
    F["vol_20"] = ret.rolling(20).std()
    F["vol_60"] = ret.rolling(60).std()
    F["vol_ratio"] = F["vol_20"] / F["vol_60"] - 1
    F["hl_range_20"] = ((high - low) / close).rolling(20).mean()
    # --- 均线 ---
    for n in (5, 20, 60, 120):
        ma = close.rolling(n).mean()
        F[f"ma_dist_{n}"] = close / ma - 1
        if n in (20, 60):
            F[f"ma_slope_{n}"] = ma / ma.shift(n) - 1
    F["ma_cross_5_20"] = close.rolling(5).mean() / close.rolling(20).mean() - 1
    # --- 摆动指标 ---
    up = ret.clip(lower=0)
    dn = (-ret).clip(lower=0)
    rs = up.rolling(14).mean() / dn.rolling(14).mean()
    F["rsi_14"] = 100 - 100 / (1 + rs)
    hi250 = close.rolling(250).max()
    lo250 = close.rolling(250).min()
    F["price_pos_250"] = (close - lo250) / (hi250 - lo250)
    F["dd_60"] = close / close.rolling(60).max() - 1
    # --- 量 ---
    F["vol_ratio_5_20"] = volume.rolling(5).mean() / volume.rolling(20).mean() - 1
    vstd = volume.rolling(20).std()
    F["vol_z_20"] = (volume - volume.rolling(20).mean()) / vstd
    # --- 流动性（自身历史归一，跨股票可比） ---
    amihud = (ret.abs() / volume.replace(0, np.nan))
    a20 = amihud.rolling(20).mean()
    a250 = amihud.rolling(250).mean()
    F["liq_change"] = np.log(a20) - np.log(a250)
    # --- 市场 ---
    cov60 = ret.rolling(60).cov(idx_ret)
    var60 = idx_ret.rolling(60).var()
    beta = cov60.div(var60, axis=0)
    F["beta_60"] = beta
    # 注意：index 序列要转 numpy 按列广播（pandas 的 DataFrame*Series 是按列对齐，会炸）
    idx_mom20 = (idx_close / idx_close.shift(20) - 1).values[:, None]
    idx_mom60 = (idx_close / idx_close.shift(60) - 1).values[:, None]
    F["alpha_20"] = (close / close.shift(20) - 1).values - beta.values * idx_mom20
    F["rel_str_60"] = (close / close.shift(60) - 1).values - idx_mom60

    feats = {k: np.asarray(v, dtype=np.float32) for k, v in F.items()}
    feats = {k: np.nan_to_num(v, nan=np.nan, posinf=np.nan, neginf=np.nan)
             for k, v in feats.items()}

    # --- 标签 ---
    feats["label_fwd5"] = (close.shift(-5) / close - 1).values.astype(np.float32)
    feats["label_fwd1"] = (close.shift(-1) / close - 1).values.astype(np.float32)

    # --- 辅助列 ---
    feats["close"] = close.values.astype(np.float32)
    feats["open"] = open_.values.astype(np.float32)
    feats["high"] = high.values.astype(np.float32)
    feats["low"] = low.values.astype(np.float32)
    feats["volume"] = volume.values.astype(np.float32)
    feats["ret_1"] = ret.values.astype(np.float32)

    mi = pd.MultiIndex.from_product([close.index, close.columns],
                                    names=["datetime", "symbol"])
    # 不丢最后 5 天（标签未知但特征已知）——回测和"最新推荐"都要用到
    out = pd.DataFrame({k: v.reshape(-1) for k, v in feats.items()}, index=mi)
    out.index = out.index.set_names(["datetime", "symbol"])
    return out.reset_index()


def main():
    mem, syms = load_membership()
    pfile = OUT / "panel.parquet"
    cal = (DATA / "calendars" / "day.txt").read_text().split()
    last_cal = cal[-1]
    stale = True
    if pfile.exists():
        panel = pd.read_parquet(pfile)
        got = str(pd.to_datetime(panel.index.get_level_values(0)).max().date())
        # 日期齐 ≠ 数据齐：末日要有足够多的非空值才算新鲜
        wide_close = panel["$close"].unstack(level=1)
        n_last = int(wide_close.iloc[-1].notna().sum())
        ref = int(wide_close.iloc[-10:].notna().sum(axis=1).max())
        stale = (got < last_cal) or (n_last < 0.5 * max(ref, 1))
        log(f"已有 panel 末日 {got}，末日非空 {n_last} / 近10日峰值 {ref}，"
            f"数据末日 {last_cal} → {'过期，重新取数' if stale else '可用'}")
        if not stale:
            idx = pd.read_parquet(OUT / "index_close.parquet")["close"]
    if stale:
        panel = fetch_panel(syms)
        idx = index_close()
        panel.to_parquet(pfile)
        idx.to_frame("close").to_parquet(OUT / "index_close.parquet")

    log("开始特征工程 …")
    t0 = time.time()
    df = build_features(panel, idx)
    log(f"特征工程 {time.time()-t0:.0f}s，行数 {len(df)}")
    df.to_parquet(OUT / "features.parquet")

    feat_cols = [c for c in df.columns if c not in
                 ("datetime", "symbol", "label_fwd5", "label_fwd1",
                  "close", "open", "high", "low", "volume", "ret_1")]
    log(f"特征 {len(feat_cols)} 个: {feat_cols}")
    log("缺失率(前8):")
    miss = df[feat_cols].isna().mean().sort_values(ascending=False)
    log(miss.head(8).to_string())
    log(f"日期范围 {df['datetime'].min().date()} ~ {df['datetime'].max().date()}，"
        f"股票数 {df['symbol'].nunique()}")


if __name__ == "__main__":
    main()
