"""共享核心：数据装载 / 横截面归一化 / 指标 / 组合仿真。

设计约束（见 PLAN.md）：
- 归一化只用**当日时点成分股**做横截面排名 → 不含未来信息，也不含幸存者偏差；
- 组合仿真：信号在 T 日收盘产生 → T+1 日收盘成交 → 持有到下次调仓；
  买入 0.05%、卖出 0.15%、单笔最低 5 元、涨停买不进、停牌不可交易。
"""

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

FEATURES = [
    "mom_1", "mom_5", "mom_10", "mom_20", "mom_60", "mom_120", "mom_5_ex", "mom_20_ex",
    "rev_3", "rev_10", "vol_20", "vol_60", "vol_ratio", "hl_range_20",
    "ma_dist_5", "ma_dist_20", "ma_slope_20", "ma_dist_60", "ma_slope_60", "ma_dist_120",
    "ma_cross_5_20", "rsi_14", "price_pos_250", "dd_60",
    "vol_ratio_5_20", "vol_z_20", "liq_change", "beta_60", "alpha_20", "rel_str_60",
]
AUX = ["close", "open", "high", "low", "volume", "ret_1", "label_fwd5", "label_fwd1"]

TRAIN_START = "2016-01-01"
VALID_START = "2020-01-01"
VALID_END = "2022-12-31"
TEST_START = "2023-01-01"


# ---------------------------------------------------------------- 数据装载
def load_all():
    """返回 dict：宽矩阵、成员掩码、归一化特征、长表索引、指数序列。"""
    df = pd.read_parquet(DATA / "features.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index(["datetime", "symbol"]).sort_index()
    wide = df.unstack("symbol")
    dates = pd.DatetimeIndex(wide.index)
    symbols = list(wide.columns.get_level_values(1).unique())
    mats = {name: wide[name].reindex(columns=symbols).astype(np.float64).to_numpy()
            for name in FEATURES + AUX}

    mask = membership_matrix(dates, symbols)
    # 成分文件截止日之后没有新成分记录 → 前向填充（指数成分不会因为数据截止而清空）
    for i in range(1, len(dates)):
        if not mask[i].any():
            mask[i] = mask[i - 1]
    norm = {f: cs_normalize(mats[f], mask) for f in FEATURES}

    # 长表：每个交易日的时点成分股各一行
    counts = mask.sum(axis=1)
    rows_date = np.repeat(np.arange(len(dates)), counts)
    rows_sym = np.concatenate([np.where(mask[t])[0] for t in range(len(dates))])

    n = len(rows_date)
    X = np.full((n, len(FEATURES)), np.nan, dtype=np.float32)
    for i, f in enumerate(FEATURES):
        X[:, i] = norm[f][rows_date, rows_sym]

    out = {
        "dates": dates, "symbols": symbols, "mats": mats, "norm": norm, "mask": mask,
        "rows_date": rows_date, "rows_sym": rows_sym, "X": X,
        "y": mats["label_fwd5"][rows_date, rows_sym],
        "y1": mats["label_fwd1"][rows_date, rows_sym],
        "close": mats["close"], "ret": mats["ret_1"], "volume": mats["volume"],
    }
    idx = pd.read_parquet(DATA / "index_close.parquet")["close"]
    idx.index = pd.to_datetime(idx.index)
    out["index"] = idx.reindex(dates)
    return out


def membership_matrix(dates, symbols):
    """(T×N) bool：date 当日该股是否在沪深300成分内（时点成分，来源 csi300.txt）。"""
    mem = pd.read_csv(DATA / "membership.csv", parse_dates=["start", "end"])
    mask = np.zeros((len(dates), len(symbols)), dtype=bool)
    pos = {s: i for i, s in enumerate(symbols)}
    for sym, grp in mem.groupby("symbol"):
        j = pos.get(sym)
        if j is None:
            continue
        for _, r in grp.iterrows():
            i0 = dates.searchsorted(r["start"])
            i1 = dates.searchsorted(r["end"], side="right")
            if i1 > i0:
                mask[i0:i1, j] = True
    return mask


def cs_normalize(mat, mask):
    """横截面排名归一到 [-1,1]；只在当日成分股内部排名。"""
    x = np.where(mask, mat, np.nan)
    df = pd.DataFrame(x)
    rank = df.rank(axis=1, pct=True).to_numpy()
    cnt = mask.sum(axis=1, keepdims=True).astype(float)
    r = rank * cnt
    denom = np.maximum(cnt - 1, 1)
    out = (r - 1) / denom * 2 - 1
    return np.where(mask, out, np.nan)


# ---------------------------------------------------------------- 指标
def daily_ic(pred, y, rows_date):
    """按日算 Spearman IC（秩相关），返回 (Series, n_days)。"""
    df = pd.DataFrame({"d": rows_date, "p": pred, "y": y}).dropna()
    if df.empty:
        return pd.Series(dtype=float), 0
    df["pr"] = df.groupby("d")["p"].rank()
    df["yr"] = df.groupby("d")["y"].rank()
    ics, days = [], []
    for d, g in df.groupby("d"):
        if len(g) < 10:
            continue
        a, b = g["pr"].to_numpy(), g["yr"].to_numpy()
        if np.std(a) == 0 or np.std(b) == 0:
            continue
        ics.append(np.corrcoef(a, b)[0, 1])
        days.append(d)
    return pd.Series(ics, index=days), len(ics)


def ic_stats(ic_series):
    ic = ic_series.dropna()
    if len(ic) == 0:
        return {"n": 0}
    n = len(ic)
    mean = float(ic.mean())
    sd = float(ic.std(ddof=1)) if n > 1 else 0.0
    return {
        "n": n, "ic_mean": mean, "ic_std": sd,
        "icir": mean / sd if sd > 0 else 0.0,
        "t_stat": mean / sd * np.sqrt(n) if sd > 0 else 0.0,
        "ic_positive_ratio": float((ic > 0).mean()),
    }


def perf_stats(nav, bench_nav=None, periods_per_year=244):
    """nav: pd.Series（日期→净值），bench_nav: 可选基准净值（同索引）。"""
    nav = nav.dropna()
    if len(nav) < 2:
        return {}
    r = nav.pct_change().dropna()
    total = nav.iloc[-1] / nav.iloc[0]
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    ann = total ** (1 / years) - 1 if years > 0 else 0.0
    vol = float(r.std(ddof=1) * np.sqrt(periods_per_year)) if len(r) > 1 else 0.0
    dd = nav / nav.cummax() - 1
    mdd = float(dd.min())
    sharpe = ann / vol if vol > 0 else 0.0
    out = {
        "start": str(nav.index[0].date()), "end": str(nav.index[-1].date()),
        "total_return": float(total - 1), "ann_return": float(ann),
        "ann_vol": vol, "sharpe": float(sharpe), "max_drawdown": mdd,
        "calmar": float(ann / abs(mdd)) if mdd < 0 else 0.0,
        "win_days": float((r > 0).mean()),
        "years": float(years),
    }
    if bench_nav is not None:
        b = bench_nav.reindex(nav.index).ffill().bfill()
        b = b / b.iloc[0]
        rb = b.pct_change().dropna()
        if len(rb) > 1:
            # 逐日对齐后算超额
            rr = nav.pct_change().reindex(rb.index).fillna(0.0)
            ex = rr - rb
            ex_nav = (1 + ex).cumprod()
            ex_years = (ex_nav.index[-1] - ex_nav.index[0]).days / 365.25
            ex_total = float(ex_nav.iloc[-1] - 1)
            # 注意：ex_total 是收益率，年化要用**净值因子** ex_nav，不是 ex_total
            ex_ann = float(ex_nav.iloc[-1]) ** (1 / ex_years) - 1 if ex_years > 0 else 0.0
            ex_vol = float(ex.std(ddof=1) * np.sqrt(periods_per_year)) if len(ex) > 1 else 0.0
            out.update({
                "bench_total": float(b.iloc[-1] - 1),
                "bench_ann": float((b.iloc[-1]) ** (1 / years) - 1) if years > 0 else 0.0,
                "excess_total": ex_total, "excess_ann": ex_ann,
                "excess_vol": ex_vol,
                "ir": float(ex_ann / ex_vol) if ex_vol > 0 else 0.0,
                "excess_win_days": float((ex > 0).mean()),
                "excess_mdd": float((ex_nav / ex_nav.cummax() - 1).min()),
            })
    return out


# ---------------------------------------------------------------- 组合仿真
class Simulator:
    """日频组合仿真器。

    select_fn(signal_date_idx) -> list[symbol_idx]   信号日收盘产生的目标持仓
    成交：信号日 +1 的收盘；持有到下一次调仓日收盘。
    """

    def __init__(self, ctx, select_fn, freq=5, cost_buy=0.0005, cost_sell=0.0015,
                 min_fee=5.0, account=1e6, start=None, end=None):
        self.ctx = ctx
        self.select_fn = select_fn
        self.freq = freq
        self.cost_buy = cost_buy
        self.cost_sell = cost_sell
        self.min_fee = min_fee
        self.account = account
        self.dates = ctx["dates"]
        self.sym_pos = {s: i for i, s in enumerate(ctx["symbols"])}
        i0 = 0 if start is None else self.dates.searchsorted(pd.Timestamp(start))
        i1 = len(self.dates) - 1 if end is None else min(
            self.dates.searchsorted(pd.Timestamp(end)), len(self.dates) - 1)
        self.i0, self.i1 = i0, i1
        close = ctx["close"]
        self.price = pd.DataFrame(close).ffill().to_numpy()     # 停牌沿用最后价
        self.ret = pd.DataFrame(self.price).pct_change().fillna(0.0).to_numpy()
        self.exec_days = set(range(i0 + 1, i1 + 1, freq))        # 成交日
        self.held = {}                                          # symbol_idx -> weight
        self.log = []

    def run(self):
        nav = self.account
        navs = {}
        weights = np.zeros(len(self.ctx["symbols"]))
        for d in range(self.i0, self.i1 + 1):
            r = self.ret[d]
            port_ret = float(np.dot(weights, r))
            nav *= (1.0 + port_ret)
            navs[d] = nav
            # 权重自然漂移 = 买入并持有（不是每日再平衡：那样会白送"再平衡收益"却不计成本）
            weights = weights * (1.0 + r)
            if d in self.exec_days:
                picks = list(self.select_fn(d - 1))
                w_new, cost, traded = self._rebalance(d, picks, weights, nav)
                nav -= cost
                weights = w_new
                self.log.append({"date": str(self.dates[d].date()), "n_picks": len(picks),
                                 "cost": cost, "nav": nav, "traded": traded})
        s = pd.Series(navs)
        s.index = self.dates[self.i0:self.i1 + 1]
        return s, pd.DataFrame(self.log)

    def _rebalance(self, d, picks, weights, nav):
        price = self.price[d]
        ret1 = self.ret[d]
        tradeable = np.isfinite(price) & (self.ctx["volume"][d] > 0)
        limit_up = ret1 >= 0.098            # 收盘涨停：买不进
        target = {}
        for s in picks:
            if not tradeable[s] or limit_up[s]:
                continue                      # 买不进就不买
            target[s] = 1.0 / max(len(picks), 1)
        # 当前持仓里不能交易的（停牌）保留原权重
        keep = {s: w for s, w in zip(*self._held_arrays(weights)) if not tradeable[s]}
        keep_sum = sum(keep.values())
        free = max(1.0 - keep_sum, 0.0)
        held = {s: w for s, w in zip(*self._held_arrays(weights))}
        new_w = np.zeros(len(weights))
        # 卖出：持有但不在目标里，且可交易
        sell_amt = 0.0
        for s, w in held.items():
            if s in target:
                continue
            if not tradeable[s]:
                new_w[s] = w
                continue
            sell_amt += w
        buy_names = [s for s in target if s not in held]
        buy_amt = sum(target[s] for s in buy_names)
        n_trades = len(buy_names) + sum(1 for s, w in held.items()
                                       if s not in target and tradeable[s])
        cost = (buy_amt * nav * self.cost_buy + sell_amt * nav * self.cost_sell
                + n_trades * self.min_fee)
        # 重新分配权重：保留不可交易的，其余按目标归一
        fixed = sum(w for s, w in held.items() if not tradeable[s])
        scale = free / max(sum(target.values()), 1e-12)
        for s, w in target.items():
            new_w[s] = w * scale
        for s, w in held.items():
            if not tradeable[s]:
                new_w[s] = w
        return new_w, float(cost), int(n_trades)

    @staticmethod
    def _held_arrays(weights):
        idx = np.where(weights > 0)[0]
        return idx, weights[idx]


def bench_nav(ctx, start, end):
    idx = ctx["index"].dropna()
    s = idx[(idx.index >= pd.Timestamp(start)) & (idx.index <= pd.Timestamp(end))]
    return s / s.iloc[0]
