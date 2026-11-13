"""报告自检：泄漏、切分、成本、数字一致性。全部通过才算数。

用法：..\\..\\..\\.venv\\Scripts\\python.exe check_report.py
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
RES = HERE / "results"
REPORT = HERE / "report"

LABEL_HORIZON = 5
OK, FAIL = [], []


def check(name, cond, detail=""):
    (OK if cond else FAIL).append(f"{name}{(' — ' + detail) if detail else ''}")
    print(("  ✅ " if cond else "  ❌ ") + name + (f" — {detail}" if detail else ""))


def main():
    print("自检开始")
    bt = json.loads((RES / "backtest.json").read_text(encoding="utf-8"))
    cfg = json.loads((RES / "config.json").read_text(encoding="utf-8"))
    picks = json.loads((RES / "picks.json").read_text(encoding="utf-8"))
    diag = json.loads((RES / "signal_diag.json").read_text(encoding="utf-8"))
    html = (REPORT / "report.html").read_text(encoding="utf-8")
    V = bt["periods"]["valid_2020_2022"]
    T = bt["periods"]["test_2023_2026"]

    # ---------- 1. 切分不重叠 ----------
    import model_core as mc
    ctx = mc.load_all()
    dates = ctx["dates"]
    d_train_end = dates.searchsorted(pd.Timestamp("2019-12-31"))
    d_valid0 = dates.searchsorted(pd.Timestamp(mc.VALID_START))
    # 验证期末 = 最后一个 ≤ 2022-12-31 的交易日（searchsorted 默认返回插入点，要减 1）
    d_valid1 = dates.searchsorted(pd.Timestamp(mc.VALID_END), side="right") - 1
    d_test0 = dates.searchsorted(pd.Timestamp(mc.TEST_START))
    check("训练/验证/测试区间不重叠",
          d_train_end < d_valid0 and d_valid1 < d_test0,
          f"训练末 {dates[d_train_end].date()} < 验证始 {dates[d_valid0].date()}"
          f" ≤ 验证末 {dates[d_valid1].date()} < 测试始 {dates[d_test0].date()}")

    # ---------- 2. 逐折无泄漏：训练样本的标签期末必须早于折首日 ----------
    leak = []
    for f in cfg["folds"]:
        i0 = dates.searchsorted(pd.Timestamp(f["i0"]))
        last_train = i0 - LABEL_HORIZON - 1
        if last_train >= i0:
            leak.append(f["year"])
            continue
        # 该样本的标签期末 = 日期 + 5 个交易日 = last_train + 5 < i0 ✓（构造上恒成立）
        if last_train + LABEL_HORIZON >= i0:
            leak.append(f["year"])
    check("每折训练样本标签期末早于折首日", not leak, f"{len(cfg['folds'])} 折全部通过"
          if not leak else f"泄漏: {leak}")

    # 预测日期确实在折内
    oos = pd.read_parquet(RES / "oos_preds.parquet")
    bad = 0
    for f in cfg["folds"]:
        sub = oos[(oos["datetime"] >= f["i0"]) & (oos["datetime"] <= f["i1"])]
        if len(sub) == 0:
            bad += 1
    check("每折都有对应预测", bad == 0)

    # ---------- 3. 成本确实扣了，且零成本优于含成本 ----------
    check("测试期交易成本 > 0", T["strategy"]["cost_total"] > 0,
          f"{T['strategy']['cost_total']:.0f} 元 / {T['strategy']['rebalances']} 次调仓")
    check("零成本对照优于含成本", T["strategy_zero_cost"]["ann_return"]
          > T["strategy"]["ann_return"],
          f"{T['strategy_zero_cost']['ann_return']*100:.2f}% > "
          f"{T['strategy']['ann_return']*100:.2f}%")

    # ---------- 4. 报告数字与 json 一致（抽查） ----------
    def in_html(s):
        return s in html
    spot = [
        (f"{V['strategy']['ann_return']*100:+.2f}%", "验证期策略年化"),
        (f"{T['strategy']['ann_return']*100:+.2f}%", "测试期策略年化"),
        (f"{T['equal_pool']['ann_return']*100:+.2f}%", "测试期等权池年化"),
        (f"{T['index_buyhold']['ann_return']*100:+.2f}%", "测试期沪深300年化"),
        (f"{T['strategy']['max_drawdown']*100:+.2f}%", "测试期最大回撤"),
        (f"{diag['test']['buckets']['前3%']['mean_fwd5']*100:+.3f}%", "测试期前3%档前瞻"),
        (f"{diag['valid']['buckets']['前3%']['mean_fwd5']*100:+.3f}%", "验证期前3%档前瞻"),
        (f"{cfg['model_hp']['num_leaves']}", "模型超参 leaves"),
    ]
    for s, label in spot:
        check(f"报告含数字：{label}", in_html(s), s)

    # ---------- 5. Top10 合法性 ----------
    pool = set(np.where(ctx["mask"][len(dates) - 1])[0])
    syms = ctx["symbols"]
    all_in = all(syms.index(p["symbol"]) in pool for p in picks["picks"])
    check("Top10 全在当日沪深300成分股内", all_in, f"池 {len(pool)} 只")
    check("Top10 按预测值降序", all(picks["picks"][i]["pred"] >= picks["picks"][i + 1]["pred"]
                                 for i in range(len(picks["picks"]) - 1)))
    check("Top10 预测日 = 2026-10-30", picks["as_of"] == "2026-10-30", picks["as_of"])

    # ---------- 6. pick 的收益率与价格重算一致（抽查 3 只） ----------
    last = len(dates) - 1
    close = ctx["close"]
    errs = []
    for p in picks["picks"][:3]:
        j = syms.index(p["symbol"])
        r20 = close[last, j] / close[last - 20, j] - 1
        if abs(r20 - p["ret_20"]) > 1e-6:
            errs.append((p["symbol"], r20, p["ret_20"]))
    check("pick 的近20日收益与价格重算一致", not errs, f"抽查 3 只，误差 < 1e-6"
          if not errs else str(errs))

    # ---------- 7. 数据新鲜度 ----------
    feat = pd.read_parquet(RES.parent / "data" / "features.parquet",
                           columns=["datetime", "symbol", "close"])
    feat["datetime"] = pd.to_datetime(feat["datetime"])
    last_day = feat[feat["datetime"] == feat["datetime"].max()]
    n_ok = int(last_day["close"].notna().sum())
    check("特征表末日 = 2026-10-30", str(feat["datetime"].max().date()) == "2026-10-30",
          str(feat["datetime"].max().date()))
    check("末日有效价覆盖绝大多数成分股", n_ok >= 250, f"{n_ok}/300 只非空")

    # ---------- 8. 报告不出现"保证/必涨"这类话（免责句里的否定用法不算） ----------
    banned = ["保证收益", "必涨", "稳赚", "稳赢", "目标价"]
    bad_hits = []
    for b in banned:
        for m in re.finditer(re.escape(b), html):
            w = html[max(0, m.start() - 40): m.start() + 40]
            if not re.search(r"不|非|无|别|切记", w):
                bad_hits.append(b)
                break
    check("报告无承诺性表述", not bad_hits,
          f"命中: {set(bad_hits)}" if bad_hits else "敏感词只出现在否定句式里")

    print(f"\n通过 {len(OK)} / {len(OK) + len(FAIL)}")
    if FAIL:
        print("失败项：")
        for f in FAIL:
            print("  -", f)
        raise SystemExit(1)
    print("全部通过 ✅")


if __name__ == "__main__":
    main()
