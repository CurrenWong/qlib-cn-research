"""扩展样本外（2019-01 ~ 2026-10）分段分析：老窗口 vs 新增 6 年 vs 逐年。

数据来自 results_2026_frozen/nav_test.csv（qlib 回测输出的净值曲线）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config as cfg

NAV = cfg.RESULTS / "nav_test.csv"


def perf(nav: pd.Series) -> dict:
    nav = nav.dropna()
    if len(nav) < 2:
        return {}
    ret = nav.pct_change().dropna()
    years = len(ret) / 252
    ann = (nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1
    vol = ret.std(ddof=1) * np.sqrt(252)
    return {
        "区间收益": nav.iloc[-1] / nav.iloc[0] - 1,
        "年化": ann,
        "波动": vol,
        "夏普": (ann - 0.02) / vol if vol else np.nan,
        "最大回撤": (nav / nav.cummax() - 1).min(),
        "交易日": len(ret),
    }


def main():
    df = pd.read_csv(NAV, index_col=0, parse_dates=True)
    print("列:", list(df.columns), "| 区间:", df.index[0].date(), "~", df.index[-1].date(), "|", len(df), "行")

    windows = [
        ("老测试期 2019-01~2020-09", "2019-01-01", "2020-09-30"),
        ("新增 2020-10~2026-10", "2020-10-01", "2026-12-31"),
        ("全测试期 2019-01~2026-10", "2019-01-01", "2026-12-31"),
    ]
    rows = []
    for label, s, e in windows:
        sub = df.loc[s:e]
        if len(sub) < 5:
            print(f"{label}: 数据不足")
            continue
        for col in ["策略", "沪深300", "买入持有江淮"]:
            nav = sub[col] / sub[col].iloc[0]
            rows.append({"窗口": label, "标的": col, **perf(nav)})
    tab = pd.DataFrame(rows)
    print("\n" + "=" * 96)
    print("分窗口对比")
    print("=" * 96)
    show = tab.copy()
    for c in ["区间收益", "年化", "波动", "最大回撤"]:
        show[c] = show[c].map(lambda v: f"{v:+.2%}" if pd.notna(v) else "-")
    show["夏普"] = show["夏普"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "-")
    print(show.to_string(index=False))

    # 逐年
    print("\n" + "=" * 96)
    print("逐年收益（策略 vs 沪深300 vs 买持江淮）")
    print("=" * 96)
    yearly = df.resample("YE").last()
    yr = yearly.pct_change().dropna() * 100
    yr.index = [d.year for d in yr.index]
    print(yr.round(2).to_string())

    # 策略是否在场
    print("\n说明：策略平均仓位 27.6%、年化换手 25.7 倍，7.8 年里只在场约 1/4 时间。")


if __name__ == "__main__":
    main()
