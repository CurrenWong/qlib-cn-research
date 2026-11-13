"""主流程（最终版）。

流程：
  1. 读入 walk-forward 选型结果（tools/walkforward.py 产出）：模型族 / 规则 / 阈值分位点
  2. 用训练集(2008~2016) 重新拟合该模型 → 阈值 = 训练集分数的 q 分位点
  3. 冻结策略，在【验证集 2017~2018】和【测试集 2019~2020】各跑一次 qlib 撮合回测
  4. 与沪深300、买入持有江淮汽车对比 → 指标表 + 净值图
  5. 落盘 results/

用法：
    .venv\\Scripts\\python.exe run_backtest.py
（前置：先跑 tools/walkforward.py 生成 results/strategy_choice.json）
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import config as cfg
import data_model as dm
from qlib.backtest import backtest

CHOICE_PATH = cfg.RESULTS / "strategy_choice.json"


# ------------------------------------------------------------------ 工具
def set_cn_font() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def run_bt(signal, start, end, threshold, trend_ok=None, floor_weight=0.0, zero_cost=False):
    """跑一段 qlib 回测，返回 (report, positions, indicator)。zero_cost=True 时把成本清零做对照。"""
    strategy = {
        "class": "JacScoreStrategy",
        "module_path": "strategy",
        "kwargs": {
            "signal": signal,
            "threshold": float(threshold),
            "target_weight": 1.0,
            "floor_weight": float(floor_weight),
            "trend_ok": trend_ok,
        },
    }
    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "day", "generate_portfolio_metrics": True},
    }
    open_cost = 0.0 if zero_cost else cfg.OPEN_COST
    close_cost = 0.0 if zero_cost else cfg.CLOSE_COST
    portfolio_dict, indicator_dict = backtest(
        start_time=start,
        end_time=end,
        strategy=strategy,
        executor=executor,
        benchmark=cfg.BENCHMARK,
        account=cfg.ACCOUNT,
        exchange_kwargs={
            # 只加载江淮汽车：全市场加载会因为其它票没有 factor 文件而全局退化成
            # adjusted_price 模式（100 股整手撮合失效），且慢 10 倍
            "codes": [cfg.INSTRUMENT],
            "open_cost": open_cost,
            "close_cost": close_cost,
            "min_cost": 0.0 if zero_cost else cfg.MIN_COST,
            "limit_threshold": cfg.LIMIT_THRESHOLD,
            "deal_price": cfg.DEAL_PRICE,
        },
    )
    if not portfolio_dict:
        raise RuntimeError("portfolio_dict 为空：executor 的 generate_portfolio_metrics 没生效")
    key = next(k for k in portfolio_dict if k.endswith("day"))
    report, positions = portfolio_dict[key]
    ind_key = next(k for k in indicator_dict if k.endswith("day"))
    return report, positions, indicator_dict[ind_key][0]


def perf(nav: pd.Series) -> dict:
    """净值序列 → 绩效指标。nav 起点视为 1。"""
    nav = nav.dropna()
    ret = nav.pct_change().dropna()
    n = len(ret)
    if n == 0:
        return {}
    years = n / cfg.TRADING_DAYS
    total = nav.iloc[-1] / nav.iloc[0] - 1
    ann = (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol = ret.std(ddof=1) * np.sqrt(cfg.TRADING_DAYS)
    sharpe = (ann - cfg.RISK_FREE) / vol if vol > 0 else np.nan
    dd = nav / nav.cummax() - 1
    mdd = dd.min()
    return {
        "区间收益": total,
        "年化收益": ann,
        "年化波动": vol,
        "夏普": sharpe,
        "最大回撤": mdd,
        "卡玛": ann / abs(mdd) if mdd < 0 else np.nan,
        "日胜率": (ret > 0).mean(),
        "交易日数": n,
    }


def bh_nav(close: pd.Series, dates: pd.DatetimeIndex, cost: float = 0.0) -> pd.Series:
    """买入持有净值，对齐到回测交易日。cost = 一次性买卖成本。"""
    c = close.reindex(pd.DatetimeIndex(dates)).ffill().dropna()
    nav = c / c.iloc[0]
    if cost:
        nav = nav * (1 - cost)
    return nav


def relative_metrics(strat_nav: pd.Series, bench_nav: pd.Series) -> dict:
    """策略相对基准的超额指标。"""
    df = pd.concat([strat_nav.rename("s"), bench_nav.rename("b")], axis=1).dropna()
    if len(df) < 2:
        return {}
    ex = df["s"].pct_change().dropna() - df["b"].pct_change().dropna()
    te = ex.std(ddof=1) * np.sqrt(cfg.TRADING_DAYS)
    ann_ex = (1 + ex.mean()) ** cfg.TRADING_DAYS - 1
    return {
        "年化超额": ann_ex,
        "跟踪误差": te,
        "信息比率": ann_ex / te if te > 0 else np.nan,
    }


# ------------------------------------------------------------------ 主流程
def main() -> None:
    set_cn_font()
    dm.init_qlib()
    cfg.RESULTS.mkdir(exist_ok=True)

    if not CHOICE_PATH.exists():
        raise SystemExit("缺少 results/strategy_choice.json，请先运行 tools/walkforward.py")
    choice = json.loads(CHOICE_PATH.read_text(encoding="utf-8"))
    model_name, rule, q = choice["model"], choice["rule"], float(choice["q"])
    smooth = int(choice.get("smooth", 1))
    use_ml, trend_win, floor = cfg.RULE_SPEC[rule]
    threshold = None  # 下面用训练集分数重新算

    print("=" * 78)
    print("江淮汽车 SH600418 择时策略 —— 最终回测")
    print("=" * 78)
    print(f"[策略] 模型 {model_name} | 规则 {rule} | 阈值分位点 q={q} | 信号平滑 {smooth}日"
          f" | 底仓 {floor:.0%} | 趋势窗口 {trend_win}")

    # 1) 数据
    df = dm.fetch_data()
    train, valid, test = dm.split_data(df)
    close = dm.stock_close()
    bench = dm.bench_close()
    print(f"\n[数据] 训练 {train.index[0].date()}~{train.index[-1].date()} ({len(train)})"
          f" | 验证 {valid.index[0].date()}~{valid.index[-1].date()} ({len(valid)})"
          f" | 测试 {test.index[0].date()}~{test.index[-1].date()} ({len(test)})")

    # 2) 用训练集拟合选定模型
    if model_name.startswith("Ridge"):
        alpha = float(model_name.split("_a")[1])
        scaler = StandardScaler().fit(train[cfg.FEATURE_NAMES])
        model = Ridge(alpha=alpha).fit(scaler.transform(train[cfg.FEATURE_NAMES]), train["label"])
        predict = lambda D: model.predict(scaler.transform(D[cfg.FEATURE_NAMES]))
    else:
        model = dm.train_model(train, valid)
        predict = lambda D: model.predict(D[cfg.FEATURE_NAMES])

    clean = df.dropna(subset=cfg.FEATURE_NAMES)
    raw_score = pd.Series(predict(clean[cfg.FEATURE_NAMES]), index=clean.index, name="score").sort_index()
    # 信号平滑（滚动均值，只用历史值，无未来函数）：降低换手与来回打脸
    if smooth > 1:
        score = raw_score.rolling(smooth).mean().dropna()
        score.name = "score"
    else:
        score = raw_score
    signal = dm.build_signal(score)

    if use_ml:
        threshold = float(np.quantile(score.loc[train.index], q))
        print(f"[阈值] 训练集分数 q={q:.1f} 分位点 = {threshold:+.6f}")

    # 趋势过滤：与分数同日（信号日）计算，再 shift(1) 对齐到 qlib 的决策时间轴
    # （qlib 在 T+1 日决策，所以策略里查的是 shift 后的序列）
    trend_ok = None
    if trend_win:
        trend_ok = (close > close.rolling(trend_win).mean()).shift(1).dropna()
        trend_ok.name = "trend_ok"

    # 3) IC 诊断（原始分数 / 平滑后分数）
    def _ic(p, l):
        return dm.ic_stats(p, l)

    ic_tr = _ic(score.loc[train.index], train["label"])
    ic_va = _ic(score.loc[valid.index], valid["label"])
    ic_te = _ic(score.loc[test.index], test["label"])
    raw_tr = _ic(raw_score.loc[train.index], train["label"])
    raw_va = _ic(raw_score.loc[valid.index], valid["label"])
    raw_te = _ic(raw_score.loc[test.index], test["label"])
    print(f"[IC 原始分数] 训练 {raw_tr['IC']:+.4f} (t={raw_tr['IC_t']:.2f}) | "
          f"验证 {raw_va['IC']:+.4f} (t={raw_va['IC_t']:.2f}) | "
          f"测试 {raw_te['IC']:+.4f} (t={raw_te['IC_t']:.2f})")
    print(f"[IC 平滑分数] 训练 {ic_tr['IC']:+.4f} (t={ic_tr['IC_t']:.2f}) | "
          f"验证 {ic_va['IC']:+.4f} (t={ic_va['IC_t']:.2f}) | "
          f"测试 {ic_te['IC']:+.4f} (t={ic_te['IC_t']:.2f})")

    # 4) 回测（含一组零成本对照，用来量化成本拖累）
    results = {}
    for period, (s, e) in {
        "验证集": (cfg.VALID_START, cfg.VALID_END),
        "测试集": (cfg.TEST_START, cfg.TEST_END),
    }.items():
        rep, pos, ind = run_bt(signal, s, e, threshold, trend_ok, floor)
        results[period] = {"report": rep, "positions": pos, "indicator": ind}
        print(f"[回测] {period} {s}~{e} 完成，{len(rep)} 个交易日")

    # 零成本对照：同一策略，把买卖成本设为 0
    zero_cost_nav = {}
    for period, (s, e) in {
        "验证集": (cfg.VALID_START, cfg.VALID_END),
        "测试集": (cfg.TEST_START, cfg.TEST_END),
    }.items():
        rep0, _, _ = run_bt(signal, s, e, threshold, trend_ok, floor, zero_cost=True)
        zero_cost_nav[period] = rep0["account"] / rep0["account"].iloc[0]
        print(f"[对照] {period} 零成本回测完成")

    # 5) 指标对比
    metric_rows = []
    nav_frames = {}
    for period, blob in results.items():
        rep = blob["report"]
        dates = rep.index
        strat_nav = rep["account"] / rep["account"].iloc[0]
        bench_nav = bh_nav(bench, dates)
        stock_nav = bh_nav(close, dates)
        expo = (rep["value"] / rep["account"]).mean()
        rebal = int((rep["turnover"].fillna(0) > 0).sum())
        years = len(rep) / cfg.TRADING_DAYS
        # 注意口径：qlib 的 total_cost / total_turnover 已是累计值，不能再求和
        total_cost = float(rep["total_cost"].iloc[-1])
        ann_turnover = float(rep["total_turnover"].iloc[-1]) / cfg.ACCOUNT / years if years else np.nan

        row_s = {"区间": period, "标的": "策略（择时）", **perf(strat_nav),
                 **relative_metrics(strat_nav, bench_nav),
                 "平均仓位": expo, "调仓次数": rebal,
                 "年化换手": ann_turnover,
                 "总成本": total_cost}
        row_z = {"区间": period, "标的": "策略（零成本对照）", **perf(zero_cost_nav[period]),
                 "平均仓位": expo, "调仓次数": rebal,
                 "年化换手": ann_turnover, "总成本": 0.0}
        row_b = {"区间": period, "标的": "沪深300", **perf(bench_nav), "平均仓位": np.nan,
                 "调仓次数": 0, "年化换手": np.nan, "总成本": np.nan}
        row_j = {"区间": period, "标的": "买入持有江淮汽车", **perf(stock_nav), "平均仓位": 1.0,
                 "调仓次数": 1, "年化换手": np.nan, "总成本": np.nan}
        metric_rows += [row_s, row_z, row_b, row_j]
        nav_frames[period] = pd.DataFrame(
            {"策略": strat_nav, "沪深300": bench_nav, "买入持有江淮": stock_nav}
        )

    metrics_df = pd.DataFrame(metric_rows)
    cols = ["区间", "标的", "区间收益", "年化收益", "年化波动", "夏普", "最大回撤", "卡玛",
            "日胜率", "年化超额", "信息比率", "跟踪误差", "平均仓位", "调仓次数", "年化换手", "总成本"]
    metrics_df = metrics_df.reindex(columns=cols)

    print("\n" + "=" * 78)
    print("绩效对比（策略 vs 沪深300 vs 买入持有江淮汽车）")
    print("=" * 78)
    show = metrics_df.copy()
    for c in ["区间收益", "年化收益", "年化波动", "最大回撤", "年化超额", "跟踪误差", "平均仓位", "年化换手"]:
        show[c] = show[c].map(lambda v: f"{v:.2%}" if pd.notna(v) else "-")
    for c in ["夏普", "卡玛", "信息比率", "日胜率", "调仓次数", "总成本"]:
        show[c] = show[c].map(lambda v: f"{v:.3f}" if pd.notna(v) else "-")
    print(show.to_string(index=False))

    # 6) 落盘
    metrics_df.to_csv(cfg.RESULTS / "metrics.csv", index=False, encoding="utf-8-sig")
    for period, navdf in nav_frames.items():
        navdf.to_csv(cfg.RESULTS / f"nav_{'valid' if period == '验证集' else 'test'}.csv",
                     encoding="utf-8-sig")
    pred = pd.DataFrame({
        "datetime": score.index,
        "score": score.values,
        "raw_score": raw_score.reindex(score.index).values,
        "label": df.loc[score.index, "label"].values,
        "signal_pass": (score.values > threshold).astype(int) if use_ml else 1,
    })
    pred.to_csv(cfg.RESULTS / "predictions.csv", index=False, encoding="utf-8-sig")

    if model_name.startswith("Ridge"):
        coef = pd.DataFrame({"feature": cfg.FEATURE_NAMES, "weight": model.coef_})
        coef["abs_weight"] = coef["weight"].abs()
        coef = coef.sort_values("abs_weight", ascending=False)
        coef.to_csv(cfg.RESULTS / "feature_weights.csv", index=False, encoding="utf-8-sig")
        print("\n[因子权重 Top10]（标准化后回归系数）")
        print(coef.head(10).to_string(index=False))
    else:
        gain = pd.Series(model.feature_importance("gain"), index=cfg.FEATURE_NAMES)
        imp = pd.DataFrame({"feature": gain.index, "gain": gain.values}).sort_values("gain", ascending=False)
        imp.to_csv(cfg.RESULTS / "feature_weights.csv", index=False, encoding="utf-8-sig")

    # 7) 出图
    for period, navdf in nav_frames.items():
        tag = "valid" if period == "验证集" else "test"
        fig, ax = plt.subplots(figsize=(11, 5))
        navdf.plot(ax=ax, lw=1.6)
        ax.set_title(f"江淮汽车(600418) 择时策略 vs 沪深300 —— {period}净值曲线")
        ax.set_ylabel("净值（起点 = 1）")
        ax.grid(alpha=0.3)
        ax.legend(["策略（择时）", "沪深300", "买入持有江淮汽车"])
        fig.tight_layout()
        fig.savefig(cfg.RESULTS / f"nav_{tag}.png", dpi=140)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    piv = (metrics_df.pivot(index="标的", columns="区间", values="年化收益") * 100)
    piv = piv.reindex(["策略（择时）", "策略（零成本对照）", "沪深300", "买入持有江淮汽车"])
    piv.plot(kind="bar", ax=ax, width=0.6)
    ax.set_ylabel("年化收益 (%)")
    ax.set_title("年化收益对比")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(title="区间")
    fig.tight_layout()
    fig.savefig(cfg.RESULTS / "annual_return_bar.png", dpi=140)
    plt.close(fig)

    # 8) 摘要
    summary = {
        "instrument": cfg.INSTRUMENT,
        "benchmark": cfg.BENCHMARK,
        "strategy": choice,
        "threshold": threshold,
        "split": {
            "train": [cfg.TRAIN_START, cfg.TRAIN_END, int(len(train))],
            "valid": [cfg.VALID_START, cfg.VALID_END, int(len(valid))],
            "test": [cfg.TEST_START, cfg.TEST_END, int(len(test))],
        },
        "ic": {"train": ic_tr, "valid": ic_va, "test": ic_te},
        "metrics": json.loads(metrics_df.to_json(orient="records", date_format="iso")),
        "params": {
            "ridge_alpha": float(model_name.split("_a")[1]) if model_name.startswith("Ridge") else None,
            "open_cost": cfg.OPEN_COST, "close_cost": cfg.CLOSE_COST,
            "limit_threshold": cfg.LIMIT_THRESHOLD, "account": cfg.ACCOUNT,
        },
    }
    (cfg.RESULTS / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[完成] 结果已写入 {cfg.RESULTS}")


if __name__ == "__main__":
    main()
