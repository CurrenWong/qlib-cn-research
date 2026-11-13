"""缓冲带调仓（buffer rule）：持仓只跌出 top-M 才换掉，用来压换手/成本。

原方案每月换掉全部 30 只（等权全换 = 100% 换手/月），成本每年约 2.1 个点。
缓冲带规则：现有持仓只要还在 top-M（M = mult × N）就留着，空出的名额用 top-N 里的新名字补。
M 越大越"懒"，换手越低，但对信号衰减更不敏感——用验证期/测试期一起看代价。

输出：results/wide_buffer.json
"""

import json

import numpy as np
import pandas as pd

import backtest as bt
import model_core as mc

VALID = (mc.VALID_START, mc.VALID_END)
TEST = (mc.TEST_START, "2026-10-30")


def log(*a):
    print(*a, flush=True)


def make_sel(lut, n_hold, mult):
    """n_hold 只持仓，缓冲区 n_hold*mult；返回带状态的 select_fn。"""
    n_zone = int(round(n_hold * mult))
    state = {"last": []}

    def sel(i):
        ranked = [s for s, _ in lut.get(i, [])]
        if not ranked:
            return list(state["last"])
        pos = {s: k for k, s in enumerate(ranked)}
        zone = set(ranked[:n_zone])
        keep = sorted((s for s in state["last"] if s in zone), key=lambda s: pos[s])
        keep_set = set(keep)
        add = [s for s in ranked[:n_hold] if s not in keep_set]
        picks = (keep + add)[:n_hold]
        state["last"] = picks
        return picks

    return sel


def run(ctx, oos, n_hold, mult, freq, period):
    start, end = period
    lut = bt.build_pred_lookup(ctx, oos)
    sim = mc.Simulator(ctx, make_sel(lut, n_hold, mult), freq=freq, start=start, end=end)
    nav, lg = sim.run()
    b = mc.bench_nav(ctx, start, end)
    st = mc.perf_stats(nav, b)
    st["cost_total"] = float(lg["cost"].sum())
    st["rebalances"] = int(len(lg))
    st["avg_traded"] = float(lg["traded"].mean()) if len(lg) else 0.0
    st["replace_ratio"] = st["avg_traded"] / n_hold if n_hold else 0.0
    return st


def main():
    ctx = mc.load_all()
    oos = pd.read_parquet(mc.RESULTS / "oos_preds.parquet")
    rows = []
    for n_hold in (20, 30):
        for mult in (1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0):
            for freq in (20,):
                r = {"n_hold": n_hold, "mult": mult, "freq": freq}
                for period, label in ((VALID, "valid"), (TEST, "test")):
                    st = run(ctx, oos, n_hold, mult, freq, period)
                    r[label] = st
                rows.append(r)
                v, t = r["valid"], r["test"]
                log(f"N={n_hold:3d} 缓冲×{mult:3.1f} f={freq} | "
                    f"验证 年化 {v['ann_return']*100:6.2f}% IR {v['ir']:5.2f} "
                    f"换 {v['replace_ratio']*100:5.1f}% 成本 {v['cost_total']/1e4:5.1f}万 | "
                    f"测试 年化 {t['ann_return']*100:6.2f}% IR {t['ir']:5.2f} "
                    f"MDD {t['max_drawdown']*100:6.2f}% 换 {t['replace_ratio']*100:5.1f}% "
                    f"成本 {t['cost_total']/1e4:5.1f}万")

    (mc.RESULTS / "wide_buffer_hi.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    log("已写出 results/wide_buffer.json")


if __name__ == "__main__":
    main()
