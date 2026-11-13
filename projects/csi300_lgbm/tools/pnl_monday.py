"""算「按选出的 20 只名单，周一（2026-11-02）开盘各买约 1 万元」到今天的持仓盈亏。

口径说明（两种买法都算，差别只在零头怎么处理）：
  A. ceil 口径（主口径）：每只 1 万元预算**向上取整到整手**，零头补足一手 → 每只实际投入 ≥ 1 万元
  B. floor 口径：只买得起几手就几手，余钱闲置 → 每只实际投入 ≤ 1 万元

其它事实检查：
  - 周一开盘价用腾讯**不复权** kline（与选股名单里的 real_price 同一口径）
  - 用 2026-10-30 收盘价对账，验证取数正确
  - 若某只周一开盘即涨停（开盘涨幅触及涨跌停价）→ 现实中买不进，单独标出
  - 若某只周一停牌（无 K 线）→ 标出

用法：
    D:\\Project\\qlib\\.venv\\Scripts\\python.exe tools\\pnl_monday.py
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
PICKS = PROJ / "results" / "picks_K20_price.json"
OUT = PROJ / "results" / "pnl_monday.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"   # 不复权

SIGNAL_DATE = "2026-10-30"   # 选股信号日（周五收盘）
BUY_DATE = "2026-11-02"      # 周一开盘买入
TODAY = "2026-11-03"         # 今天收盘
BUDGET = 10000.0             # 每只 1 万元
LOT = 100                    # 一手 = 100 股
BENCH = "SH000300"


def tx_symbol(code: str) -> str:
    return ("sh" if code.upper().startswith("SH") else "sz") + "".join(c for c in code if c.isdigit())


def fetch_raw(symbol: str, count: int = 40) -> pd.DataFrame:
    for attempt in range(6):
        try:
            r = requests.get(KLINE_URL, params={"param": f"{symbol},day,,,{count}"},
                             headers=UA, timeout=30)
            if r.status_code != 200 or not r.text.strip().startswith("{"):
                raise RuntimeError(f"HTTP {r.status_code} 非 JSON")
            sub = (r.json().get("data") or {}).get(symbol) or {}
            rows = sub.get("day") or []
            if not rows:
                raise RuntimeError("空返回")
            df = pd.DataFrame(rows).iloc[:, :6]
            df.columns = ["date", "open", "close", "high", "low", "volume"]
            df["date"] = pd.to_datetime(df["date"])
            for c in ["open", "close", "high", "low", "volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            return df.set_index("date").sort_index()
        except Exception as e:  # noqa: BLE001
            print(f"    第 {attempt + 1} 次失败: {type(e).__name__}: {str(e)[:80]}")
            time.sleep(3 + attempt * 2)
    return pd.DataFrame()


def limit_pct(board: str) -> float:
    return 0.20 if board in ("创业板", "科创板") else 0.10


def main():
    picks = json.loads(PICKS.read_text(encoding="utf-8"))
    rows = picks["rows"]
    print(f"名单来源: {PICKS} | as_of={picks['as_of']} | {len(rows)} 只\n")

    results = []
    for p in rows:
        sym = p["symbol"]
        df = fetch_raw(tx_symbol(sym))
        if not len(df):
            results.append({**p, "error": "取数失败"})
            continue
        rec = {k: p[k] for k in ("rank", "symbol", "name", "board", "real_price")}
        rec["prev_close"] = None
        rec["buy_open"] = None
        rec["buy_close"] = None
        rec["today_close"] = None
        for d, key in ((SIGNAL_DATE, "prev_close"), (BUY_DATE, "buy_open"), (TODAY, "today_close")):
            ts = pd.Timestamp(d)
            if ts in df.index:
                rec[key] = float(df.loc[ts, "close" if key != "buy_open" else "open"])
        if pd.Timestamp(BUY_DATE) in df.index:
            rec["buy_close"] = float(df.loc[pd.Timestamp(BUY_DATE), "close"])
        rec["bar_last"] = str(df.index[-1].date())
        rec["has_buy_bar"] = pd.Timestamp(BUY_DATE) in df.index
        results.append(rec)
        time.sleep(0.4)

    # 基准（沪深300）
    bench = fetch_raw(tx_symbol(BENCH), count=10)
    b_open = float(bench.loc[pd.Timestamp(BUY_DATE), "open"]) if pd.Timestamp(BUY_DATE) in bench.index else None
    b_close = float(bench.loc[pd.Timestamp(TODAY), "close"]) if pd.Timestamp(TODAY) in bench.index else None
    b_sig = float(bench.loc[pd.Timestamp(SIGNAL_DATE), "close"]) if pd.Timestamp(SIGNAL_DATE) in bench.index else None

    # 其它指数（看 11-03 是普跌还是只有科技跌）
    idx_ctx = {}
    for name, code in (("沪深300", "SH000300"), ("创业板指", "SZ399006"), ("科创50", "SH000688"),
                       ("中证500", "SH000905")):
        df = fetch_raw(tx_symbol(code), count=10)
        try:
            s = float(df.loc[pd.Timestamp(SIGNAL_DATE), "close"])
            o = float(df.loc[pd.Timestamp(BUY_DATE), "open"])
            c = float(df.loc[pd.Timestamp(TODAY), "close"])
            idx_ctx[name] = {"信号日收": s, "周一开": o, "今日收": c,
                             "周一开→今收%": round((c / o - 1) * 100, 2),
                             "信号日收→今收%": round((c / s - 1) * 100, 2)}
        except Exception as e:  # noqa: BLE001
            idx_ctx[name] = {"error": f"{type(e).__name__}: {str(e)[:60]}"}

    # ---- 计算 ----
    out_rows = []
    for rec in results:
        if rec.get("error") or rec["buy_open"] is None or rec["today_close"] is None:
            out_rows.append({**rec, "note": "缺数据"})
            continue
        op = rec["buy_open"]
        cl = rec["today_close"]
        lots_a = max(int(BUDGET // (op * LOT)), 0) + 1          # ceil：零头补一手
        shares_a = lots_a * LOT
        lots_b = max(int(BUDGET // (op * LOT)), 1)             # floor：至少一手，零头闲置
        shares_b = lots_b * LOT

        # C 口径：信号日（10-30）收盘即成交
        sig = rec["prev_close"]
        shares_c = shares_a
        cost_c = shares_c * sig if sig else None
        val_c = shares_c * cl if sig else None

        prev = rec["prev_close"]
        gap = (op / prev - 1) if prev else None
        lim = limit_pct(rec["board"])
        at_limit = bool(gap is not None and gap >= lim - 0.002)

        r = {
            **{k: rec.get(k) for k in ("rank", "symbol", "name", "board")},
            "prev_close": prev, "buy_open": op, "today_close": cl,
            "buy_close": rec.get("buy_close"),
            "gap_open_pct": None if gap is None else round(gap * 100, 2),
            "at_limit_up_open": at_limit,
            "A_shares": shares_a, "A_cost": round(shares_a * op, 2),
            "A_value": round(shares_a * cl, 2), "A_pnl": round(shares_a * (cl - op), 2),
            "B_shares": shares_b, "B_cost": round(shares_b * op, 2),
            "B_value": round(shares_b * cl, 2), "B_pnl": round(shares_b * (cl - op), 2),
            "C_cost": None if cost_c is None else round(cost_c, 2),
            "C_value": None if val_c is None else round(val_c, 2),
            "C_pnl": None if cost_c is None else round(val_c - cost_c, 2),
            "ret_pct": round((cl / op - 1) * 100, 2),
        }
        out_rows.append(r)

    ok = [r for r in out_rows if "ret_pct" in r]
    total_budget = BUDGET * len(ok)

    A_cost = sum(r["A_cost"] for r in ok)
    A_val = sum(r["A_value"] for r in ok)
    B_cost = sum(r["B_cost"] for r in ok)
    B_val = sum(r["B_value"] for r in ok)
    C_cost = sum(r["C_cost"] for r in ok)
    C_val = sum(r["C_value"] for r in ok)

    # 对账 1：腾讯不复权 kline 的 10-30 收盘 vs 名单里的 real_price（qlib $close/factor）
    diffs = []
    for rec, r in zip(results, out_rows):
        if rec.get("prev_close") is not None:
            diffs.append(abs(rec["prev_close"] - rec.get("real_price", 0)) / rec["prev_close"])

    # 对账 2：kline 的 11-02 收盘 / 11-03 收盘 vs 腾讯实时行情接口（昨收 / 现价）
    q = ",".join(tx_symbol(r["symbol"]) for r in ok)
    qdiffs = []
    try:
        rr = requests.get(f"https://qt.gtimg.cn/q={q}", headers=UA, timeout=30)
        txt = rr.content.decode("gbk", errors="ignore")
        for line in txt.split(";"):
            line = line.strip()
            if not line.startswith("v_"):
                continue
            f = line.split("=", 1)[1].strip('"').split("~")
            if len(f) < 40:
                continue
            code = line.split("=", 1)[0].replace("v_", "").upper()   # 如 v_sz300394 → SZ300394
            row = next((x for x in ok if x["symbol"] == code), None)
            if row is None:
                continue
            qdiffs.append((code, abs(float(f[3]) - row["today_close"]) / row["today_close"],
                           abs(float(f[4]) - row.get("buy_close", row["today_close"]))
                           / row["today_close"]))
    except Exception as e:  # noqa: BLE001
        print(f"(实时行情对账失败: {type(e).__name__} {str(e)[:60]})")

    # 交易成本（沿用项目口径 model_core.py: 买 0.05% / 卖 0.15%，每笔最低 5 元）
    COST_BUY, COST_SELL, MIN_FEE = 0.0005, 0.0015, 5.0
    fee_A = A_cost * COST_BUY + A_val * COST_SELL + 2 * len(ok) * MIN_FEE
    fee_B = B_cost * COST_BUY + B_val * COST_SELL + 2 * len(ok) * MIN_FEE

    summary = {
        "signal_date": SIGNAL_DATE, "buy_date": BUY_DATE, "today": TODAY,
        "n_stocks": len(ok),
        "A": {"cost": round(A_cost, 2), "value": round(A_val, 2), "pnl": round(A_val - A_cost, 2),
              "ret_on_invested_pct": round((A_val / A_cost - 1) * 100, 3),
              "ret_on_budget_pct": round((A_val - A_cost) / total_budget * 100, 3)},
        "B": {"cost": round(B_cost, 2), "value": round(B_val, 2), "pnl": round(B_val - B_cost, 2),
              "ret_on_invested_pct": round((B_val / B_cost - 1) * 100, 3) if B_cost else None,
              "ret_on_budget_pct": round((B_val - B_cost) / total_budget * 100, 3)},
        "C_signal_close": {"cost": round(C_cost, 2), "value": round(C_val, 2),
                            "pnl": round(C_val - C_cost, 2),
                            "ret_on_invested_pct": round((C_val / C_cost - 1) * 100, 3)},
        "total_budget": total_budget,
        "fees": {"rate_buy": COST_BUY, "rate_sell": COST_SELL, "min_fee_per_trade": MIN_FEE,
                 "A_round_trip_fee": round(fee_A, 2),
                 "A_net_pnl": round((A_val - A_cost) - fee_A, 2),
                 "A_net_ret_on_invested_pct": round(((A_val - A_cost) - fee_A) / A_cost * 100, 3),
                 "B_round_trip_fee": round(fee_B, 2),
                 "B_net_ret_on_invested_pct": round(((B_val - B_cost) - fee_B) / B_cost * 100, 3)},
        "benchmark_csi300": {
            "buy_open": b_open, "today_close": b_close,
            "ret_pct": round((b_close / b_open - 1) * 100, 3) if b_open and b_close else None},
        "reconcile_max_diff_pct": round(max(diffs) * 100, 4) if diffs else None,
        "index_context": idx_ctx,
        "dividend_note": "宁波银行 002142 除权除息日 2026-11-05（每 10 股派 4 元）——持有到 11-05 会拿 0.40 元/股现金分红，"
                         "11-05 股价相应除权下调，那不是亏损",
        "limit_up_at_open": [f"{r['name']} {r['symbol']}" for r in ok if r["at_limit_up_open"]],
    }

    print(f"{'#':>3} {'名称':<10} {'代码':<10} {'板':<6} {'10-30收':>9} {'11-02开':>9} {'11-03收':>9} "
          f"{'开盘涨幅':>8} {'A股数':>7} {'A投入':>10} {'A盈亏':>10} {'%':>7} {'%':>7}")
    for r in sorted(ok, key=lambda x: x["rank"]):
        flag = " ⚠涨停" if r["at_limit_up_open"] else ""
        print(f"{r['rank']:>3} {r['name']:<10} {r['symbol']:<10} {r['board']:<6} "
              f"{r['prev_close']:>9.2f} {r['buy_open']:>9.2f} {r['today_close']:>9.2f} "
              f"{r['gap_open_pct']:>7.2f}% {r['A_shares']:>7} {r['A_cost']:>10.0f} "
              f"{r['A_pnl']:>10.0f} {r['ret_pct']:>6.2f}% {r['A_pnl'] / r['A_cost'] * 100:>6.2f}%{flag}")

    print("\n" + "=" * 78)
    print(f"A 口径（零头补一手、每只≥1万）: 投入 {A_cost:,.0f} 元，市值 {A_val:,.0f} 元，"
          f"盈亏 {A_val - A_cost:+,.0f} 元 → 投入收益率 {(A_val / A_cost - 1) * 100:+.2f}%，"
          f"占总预算 {(A_val - A_cost) / total_budget * 100:+.2f}%")
    print(f"B 口径（零头闲置）: 投入 {B_cost:,.0f} 元，市值 {B_val:,.0f} 元，"
          f"盈亏 {B_val - B_cost:+,.0f} 元 → 投入收益率 "
          f"{(B_val / B_cost - 1) * 100:+.2f}%，占总预算 {(B_val - B_cost) / total_budget * 100:+.2f}%")
    if summary["benchmark_csi300"]["ret_pct"] is not None:
        print(f"沪深300 同期（11-02开盘→11-03收盘）: {summary['benchmark_csi300']['ret_pct']:+.2f}%")
    print(f"C 口径（信号日 10-30 收盘就买→11-03 收盘）: 投入 {C_cost:,.0f} 元，市值 {C_val:,.0f} 元，"
          f"盈亏 {C_val - C_cost:+,.0f} 元 → {(C_val / C_cost - 1) * 100:+.2f}%")
    print(f"对账1（腾讯不复权 10-30 收盘 vs 名单 real_price）最大偏差: {summary['reconcile_max_diff_pct']}%")
    print(f"交易成本（买 0.05% / 卖 0.15%，每笔最低 5 元，共 {2 * len(ok)} 笔）: "
          f"A 口径 {fee_A:,.0f} 元 → 净收益率 "
          f"{((A_val - A_cost) - fee_A) / A_cost * 100:+.2f}%")
    if qdiffs:
        print(f"对账2（kline vs 实时行情接口）11-03收盘 最大偏差: "
              f"{max(d[1] for d in qdiffs) * 100:.4f}% | 11-02收盘 最大偏差: "
              f"{max(d[2] for d in qdiffs) * 100:.4f}%")
    print("\n指数背景（信号日收盘 → 周一开盘 → 今日收盘）:")
    for name, v in idx_ctx.items():
        if "error" in v:
            print(f"  {name}: 取数失败 {v['error']}")
        else:
            print(f"  {name:<8} {v['信号日收']:>10.2f} → {v['周一开']:>10.2f} → {v['今日收']:>10.2f}"
                  f"   周一开→今收 {v['周一开→今收%']:+.2f}% | 信号日收→今收 {v['信号日收→今收%']:+.2f}%")
    if summary["limit_up_at_open"]:
        print(f"⚠ 周一开盘涨停买不进: {summary['limit_up_at_open']}")

    OUT.write_text(json.dumps({"summary": summary, "rows": out_rows}, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\n已写入: {OUT}")


if __name__ == "__main__":
    main()
