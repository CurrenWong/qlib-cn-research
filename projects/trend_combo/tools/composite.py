"""标准化 + 分域合成：把价量和基本面因子变成 [-1,1] 的可比分数，再加权成趋势总分。

标准化四步（顺序不能换）：
  1. 截面 winsorize(1%, 99%)      —— 去极值
  2. 行业中性化                     —— 减掉同行业均值，剥离行业 beta
  3. 截面 z-score                   —— 同日可比
  4. clip(z/3, -1, 1)              —— 限幅，保留极端信息但不让单因子主导

方向：FUND_DIRECTION 里写死（先验），eval 会用训练期 IC 符号复核。
分域：域内等权（比 IC 加权抗噪），跨域用 w_price / w_fund / w_event。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\composite.py
产出：data\\scores.parquet（长表，含各域分数与总分）
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from build_panel import (DATA, FUND_DIRECTION, FUND_GROUPS, PRICE_GROUPS,
                         RESULTS, EVENT_FIELDS)

HERE = Path(__file__).resolve().parent

# 价格因子的先验方向（先验 +1/-1；eval 里复核）
PRICE_DIRECTION = {
    "mom_20": 1, "mom_60": 1, "mom_120": 1, "ma_slope_20": 1, "ma_slope_60": 1,
    "ma_dist_20": 1, "ma_dist_60": 1, "ma_cross_5_20": 1, "price_pos_250": 1,
    "rel_str_60": 1,
    "rev_3": -1, "rev_10": -1, "mom_5_ex": -1, "mom_20_ex": -1, "dd_60": 1,
    "vol_20": -1, "vol_60": -1, "hl_range_20": -1, "beta_60": 0, "alpha_20": 1,
    "vol_ratio": 1, "vol_ratio_5_20": 1, "vol_z_20": 1, "liq_change": 1,
}


def winsorize_z(mat: np.ndarray) -> np.ndarray:
    """按行（每个交易日）做 winsorize + z-score + 限幅。mat: (T, N)"""
    out = np.full(mat.shape, np.nan, dtype=np.float32)
    with np.errstate(all="ignore"):
        q1 = np.nanpercentile(mat, 1, axis=1, keepdims=True)
        q99 = np.nanpercentile(mat, 99, axis=1, keepdims=True)
    bad = ~np.isfinite(q1) | ~np.isfinite(q99) | (q99 - q1 <= 0)
    q1 = np.where(bad, np.nan, q1)
    q99 = np.where(bad, np.nan, q99)
    w = np.clip(mat, q1, q99)
    mu = np.nanmean(w, axis=1, keepdims=True)
    sd = np.nanstd(w, axis=1, keepdims=True)
    sd = np.where(sd <= 0, np.nan, sd)
    z = (w - mu) / sd
    return np.clip(z / 3.0, -1, 1).astype(np.float32)


def neutralize_industry(zmat: np.ndarray, board_wide: pd.DataFrame) -> np.ndarray:
    """行业中性化：减去「同行业同日的均值」再标准化。board_wide: index=date, columns=symbol"""
    df = pd.DataFrame(zmat, index=board_wide.index, columns=board_wide.columns)
    board = board_wide.reindex(index=df.index, columns=df.columns)
    # 每个 symbol 归属的行业（取该 symbol 出现最多的行业）
    sym2board = {}
    for sym in df.columns:
        col = board[sym].dropna()
        if len(col):
            sym2board[sym] = col.value_counts().index[0]
    labels = pd.Series(sym2board)
    if labels.empty:
        return zmat
    grouped = df.T.groupby(labels).mean().T          # (date × industry)
    # 没有行业标签的股票保持原始 z（减 0），成分太少的行业也不中性化
    ind_mean = np.zeros_like(zmat, dtype=np.float32)
    for ind in grouped.columns:
        cols = [c for c in df.columns if sym2board.get(c) == ind]
        if len(cols) < 5:            # 成分太少的行业不做中性化，否则该股被清零
            continue
        ind_mean[:, [df.columns.get_loc(c) for c in cols]] = grouped[ind].values[:, None]
    resid = zmat - ind_mean
    return winsorize_z(resid)


def main():
    print("① 读面板 …")
    panel = pd.read_parquet(DATA / "panel_merged.parquet")
    panel["datetime"] = pd.to_datetime(panel["datetime"])
    print(f"   {panel.shape}")

    dates = np.sort(panel["datetime"].unique())
    symbols = np.sort(panel["symbol"].unique())
    d_idx = {d: i for i, d in enumerate(dates)}
    s_idx = {s: i for i, s in enumerate(symbols)}
    T, N = len(dates), len(symbols)
    print(f"   {T} 个交易日 × {N} 只股票")

    rowi = panel["datetime"].map(d_idx).to_numpy()
    coli = panel["symbol"].map(s_idx).to_numpy()

    def to_mat(col):
        m = np.full((T, N), np.nan, dtype=np.float64)
        m[rowi, coli] = panel[col].to_numpy(dtype=np.float64)
        return m

    def to_mat_obj(col):
        m = np.full((T, N), None, dtype=object)
        m[rowi, coli] = panel[col].to_numpy(dtype=object)
        return m

    # 行业矩阵（来自估值接口的 BOARD_NAME）
    board_wide = pd.DataFrame(to_mat_obj("board_name"), index=dates, columns=symbols)

    price_cols = [c for g in PRICE_GROUPS.values() for c in g]
    fund_cols = [c for g in FUND_GROUPS.values() for c in g]
    event_cols = list(EVENT_FIELDS)

    print("② 标准化（winsorize → 行业中性化 → z → 限幅）…")
    zs = {}
    for c in price_cols + fund_cols + event_cols:
        if c not in panel.columns:
            print(f"   ⚠️ 缺列 {c}")
            continue
        m = to_mat(c)
        z = winsorize_z(m)
        z = neutralize_industry(z, board_wide)
        zs[c] = z.astype(np.float32)     # 原始标准化值（不含方向），方向在打分层决定

    # 组装长表
    def mat_to_series(name):
        m = zs[name]
        return pd.Series(m[rowi, coli], index=panel.index, name=name)

    for c in zs:
        panel["z_" + c] = mat_to_series(c)

    # 方向表（先验）：价量用 PRICE_DIRECTION，基本面/事件用 FUND_DIRECTION
    prior = {**PRICE_DIRECTION, **FUND_DIRECTION}

    def dom_score(cols, directions=None):
        dirs = directions if directions is not None else prior
        use = [c for c in cols if "z_" + c in panel.columns]
        if not use:
            return pd.Series(np.nan, index=panel.index)
        mats = []
        for c in use:
            v = panel["z_" + c] * dirs.get(c, 1)
            mats.append(v)
        return pd.concat(mats, axis=1).mean(axis=1)

    # 分域分数（先验方向版本；eval 会用训练期 IC 重新定向）
    panel["price_score"] = dom_score([c for g in PRICE_GROUPS.values() for c in g])

    # 【2026-11-05 修复】没有当日收盘价的票，价量分一律置 NaN。
    # 根因：build_dataset.py 的 close.pct_change() 默认 fill_method='pad'，
    #       停牌/退市股的价格被前向填充成一条平线 → price_pos_250 等因子恒取极端值，
    #       z-score 后挤到截面上限，导致「买不到的死票」霸占纯价量排名（20 只并列在上限）。
    # 语义上更重要的理由：没有收盘价 = 当天不可交易，就不该有价量分。
    if "close" in panel.columns:
        no_px = panel["close"].isna()
        n_no_px = int(no_px.sum())
        panel.loc[no_px, "price_score"] = np.nan
        n_names = int(panel.loc[no_px, "symbol"].nunique())
        print(f"   无当日收盘价 → price_score 置 NaN：{n_no_px} 行 / {n_names} 只票")
    else:
        print("   ⚠️ 面板没有 close 列，跳过「无价股置 NaN」保护")

    for g, cols in FUND_GROUPS.items():
        panel[f"fund_{g}"] = dom_score(cols)
    fund_all = [c for g in FUND_GROUPS.values() for c in g]
    panel["fund_score"] = dom_score(fund_all)
    panel["event_score"] = dom_score(event_cols)

    panel.to_parquet(DATA / "scores.parquet", index=False)
    print(f"   写出 scores.parquet {panel.shape}")

    summary = {
        "price_factors": price_cols,
        "fund_factors": fund_cols,
        "event_factors": event_cols,
        "n_dates": int(T), "n_symbols": int(N),
        "sample": panel.dropna(subset=["price_score"]).tail(3)[
            ["datetime", "symbol", "price_score", "fund_score", "event_score"]
        ].to_dict("records"),
    }
    (RESULTS / "score_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("   写出 score_summary.json")


if __name__ == "__main__":
    main()
