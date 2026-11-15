"""事件表收益的交叉校验：qlib（前复权） vs 新浪前复权。

发现过 2005-12-14 这类"停牌+除权复牌"导致的复权残差，会把假跌当成事件。
本脚本对全部交易日逐日比对，标出 |差异| 超过阈值的日子。

产出：validation.csv（逐事件校验）、news_cache/sina_qfq.csv（缓存，避免重复请求）
"""

from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

HERE = Path(__file__).resolve().parent
QLIB = Path(_ROOT + r"/qlib_data/cn_data_2026")
CACHE = HERE / "news_cache" / "sina_qfq.csv"


def cal():
    return [x.strip() for x in (QLIB / "calendars" / "day.txt").read_text().splitlines() if x.strip()]


def load_qlib(sym, field):
    arr = np.fromfile(QLIB / "features" / sym / f"{field}.day.bin", dtype=np.float32)
    c = cal()
    start = int(arr[0])
    return pd.Series(arr[1:], index=c[start : start + len(arr) - 1], dtype="float64")


def get_sina():
    if CACHE.exists():
        df = pd.read_csv(CACHE, dtype={"date": str})
        df["date"] = df["date"].str[:10]
        return df.set_index("date")
    import akshare as ak

    print("拉取新浪前复权全历史 ...")
    d = ak.stock_zh_a_daily(symbol="sh600418", adjust="qfq").copy()
    d["date"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
    d.to_csv(CACHE, index=False, encoding="utf-8-sig")
    return d.set_index("date")


def main():
    sina = get_sina()
    qlib = load_qlib("sh600418", "adjclose")
    common = [d for d in qlib.index if d in sina.index]

    q = qlib.reindex(common).pct_change() * 100
    s = sina["close"].reindex(common).pct_change() * 100
    diff = (q - s)

    print(f"共同交易日 {len(common)} 天（{common[0]} ~ {common[-1]}）")
    print(f"日收益相关系数: {pd.concat([q, s], axis=1).corr().iloc[0,1]:.6f}")
    print(f"平均绝对差: {diff.abs().mean():.4f} pct | 中位 {diff.abs().median():.4f} pct | 最大 {diff.abs().max():.4f} pct")

    print("\n=== 差异 > 2pct 的全部交易日 ===")
    big = diff[diff.abs() > 2].dropna().sort_values()
    for d, v in big.items():
        qv = q[d]
        sv = s[d]
        print(f"  {d}  qlib {qv:+7.2f}%  新浪qfq {sv:+7.2f}%  差 {v:+7.2f}pct")

    # 事件表逐条校验
    ev = pd.read_csv(HERE / "events.csv")
    ev["date"] = ev["date"].astype(str)
    ev["qlib_ret%"] = ev["date"].map(q)
    ev["sina_qfq_ret%"] = ev["date"].map(s)
    ev["diff_pct"] = (ev["qlib_ret%"] - ev["sina_qfq_ret%"]).abs()
    ev["data_flag"] = np.where(ev["diff_pct"] > 2, "复权残差-疑似假事件", "")
    ev.to_csv(HERE / "validation.csv", index=False, encoding="utf-8-sig")

    flagged = ev[ev["data_flag"] != ""]
    print(f"\n=== 事件表标记 {len(flagged)} 条疑似数据假象 ===")
    if len(flagged):
        print(flagged[["date", "tier", "ret", "qlib_ret%", "sina_qfq_ret%", "diff_pct"]].to_string(index=False))

    # 事件表与新浪 qfq 的整体一致性
    ok = ev.dropna(subset=["qlib_ret%", "sina_qfq_ret%"])
    print(f"\n事件表 {len(ok)} 条可校验：平均绝对差 {ok['diff_pct'].mean():.4f} pct，"
          f"最大 {ok['diff_pct'].max():.4f} pct")
    print(f"已写入 validation.csv")


if __name__ == "__main__":
    main()
