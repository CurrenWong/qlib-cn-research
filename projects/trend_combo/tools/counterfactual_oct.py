"""用基本面加权策略（trend_combo 混合分）在 2026-10-30 收盘选股，
与「11-02 开盘实盘建仓的 20 只 LGBM 组合」做同口径对照：同样买 11-02 开盘、
卖 11-05 收盘、同一套交易成本与红利税，看收益差多少。

口径说明（交易成本与红利税与 pnl_monday.py / track_pnl.py 完全一致）：
  买入 0.05% / 卖出 0.15% / 每笔最低 5 元；红利税按持有期差别化（≤1 个月 20%）

【2026-11-05 修复】仓位规则从「每只 1 万 + 零头补一手」改成
  **等权 + 单票权重上限 10% + 整手向下取整**，分两遍执行：
  - 旧规则在高价股上会失控：寒武纪 907 元/股 → 1 手就是 9.07 万，权重冲到 39%；
  - 第一遍：目标金额 = 总预算 / 只数，手数向下取整到 100 股整数倍；
    一手就超过「名义预算 × 10%」的票直接跳过；
  - 第二遍：按**实际投入**重新等权（目标 = 实际投入 / 只数），
    并把单票买入成本超过「实际投入 × 10%」的按整手裁掉，裁到 0 则剔除该票。
    这样权重上限才是真的按实际分母约束住的（第一遍用名义预算算会失真）。
  总预算固定 20 万（与实盘 25.7 万同量级），K 越大单票目标越小。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\counterfactual_oct.py
产出：results\\counterfactual_oct30.json、report\\counterfactual_oct30.md
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
RESULTS = PROJ / "results"
REPORT = PROJ / "report"
LGBM = Path(_ROOT + r"/projects/csi300_lgbm")

SIGNAL_DATE = pd.Timestamp("2026-10-30")
ENTRY = pd.Timestamp("2026-11-02")
EXIT = pd.Timestamp("2026-11-05")
TOTAL_CAPITAL = 200_000.0   # 组合总预算（与实盘 25.7 万同量级）
MAX_WEIGHT = 0.10            # 单票权重硬上限（按实际投入计；第二遍执行）
LOT = 100
COST_BUY, COST_SELL, MIN_FEE = 0.0005, 0.0015, 5.0
BENCH = "SH000300"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
QUOTE_URL = "https://qt.gtimg.cn/q="
DIV_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
           "sortColumns=EX_DIVIDEND_DATE&sortTypes=-1&pageSize=30&pageNumber=1&"
           "reportName=RPT_SHAREBONUS_DET&columns=ALL&filter="
           "(SECURITY_CODE%3D%22{code}%22)")


def tx_symbol(code: str) -> str:
    return ("sh" if code.upper().startswith("SH") else "sz") + "".join(c for c in code if c.isdigit())


def fetch_raw(symbol: str, count: int = 12) -> pd.DataFrame:
    """腾讯 kline（不复权）。index=date, 列 open/close/high/low/volume。"""
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
            print(f"    {symbol} 第 {attempt + 1} 次失败: {type(e).__name__}: {str(e)[:70]}")
            time.sleep(2 + attempt * 2)
    return pd.DataFrame()


def fetch_names(symbols: list[str]) -> dict:
    """批量取中文名（腾讯实时行情接口，一次最多 40 只）。

    返回 {"SH600000": "浦发银行"}；键是本项目的 symbol 格式。
    """
    out = {}
    tx = [tx_symbol(s) for s in symbols]
    for i in range(0, len(tx), 40):
        chunk = tx[i:i + 40]
        try:
            r = requests.get(QUOTE_URL + ",".join(chunk), headers=UA, timeout=30)
            txt = r.content.decode("gbk", errors="replace")
            for line in txt.split(";"):
                if "=" not in line:
                    continue
                head, payload = line.split("=", 1)
                code = head.strip()
                if code.startswith("v_"):
                    code = code[2:]
                parts = payload.strip('" \n').split("~")
                if len(parts) > 1 and parts[1]:
                    key = ("SH" if code.startswith("sh") else "SZ") + "".join(
                        ch for ch in code if ch.isdigit())
                    out[key] = parts[1]
        except Exception as e:  # noqa: BLE001
            print(f"  名称接口失败: {type(e).__name__}: {str(e)[:60]}")
        time.sleep(0.3)
    return out


def fetch_dividends(symbol: str) -> list[dict]:
    code = "".join(c for c in symbol if c.isdigit())
    out = []
    try:
        r = requests.get(DIV_URL.format(code=code), headers=UA, timeout=25)
        recs = (r.json().get("result") or {}).get("data") or []
        for x in recs:
            raw = x.get("EX_DIVIDEND_DATE")
            if not raw:
                continue
            ex = str(raw)[:10]
            if not ex or ex.lower().startswith("none"):
                continue
            try:
                per10 = float(x.get("PRETAX_BONUS_RMB") or 0)
            except (TypeError, ValueError):
                per10 = 0.0
            if per10:
                out.append({"ex_date": ex, "per_share": per10 / 10.0})
    except Exception as e:  # noqa: BLE001
        print(f"    {symbol} 分红接口失败: {type(e).__name__}: {str(e)[:60]}")
    return out


def div_tax_rate(hold_days: int) -> float:
    if hold_days <= 30:
        return 0.20
    if hold_days <= 365:
        return 0.10
    return 0.0


def _f(x, width=8):
    """格式化百分比，None 安全。"""
    if x is None:
        return " " * (width - 1) + "n/a"
    return f"{x:+{width}.2f}%"


def select(day: pd.DataFrame, col: str, K: int, ind_cap=None,
           require_px: bool = True) -> list[str]:
    """按分数列取 top-K；ind_cap=每行业最多几只。

    require_px=True  → 只用「10-30 当天有收盘价」的票（干净池）
        背景：本地 qlib 面板里 637 只中有 338 只的价格只更新到 10-27（数据缺口），
        另 20 只是 2017~2023 年就停止交易的死票；这些票的「10-30 分数」是拿旧价算的。
    require_px=False → 策略原样（全池，谁分高谁进），复现脚本今天真正会输出的名单。
    """
    d = day[day[col].notna()]
    if require_px:
        d = d[d["close"].notna()]
    d = d.sort_values(col, ascending=False)
    picked, cnt = [], {}
    for sym, b in zip(d["symbol"], d["board_name"]):
        b = b if isinstance(b, str) and b else "未知"
        if ind_cap and cnt.get(b, 0) >= ind_cap:
            continue
        picked.append(sym)
        cnt[b] = cnt.get(b, 0) + 1
        if len(picked) >= K:
            break
    return picked


def evaluate(picks, px, names, divs, label):
    """按 A 口径算一个组合：买 11-02 开盘、卖 11-05 收盘、分红计现金、扣双边成本。"""
    rows, skipped = [], []
    total_cost = total_val = total_div = 0.0
    plan = []                          # 第一遍算出的买入计划
    target = TOTAL_CAPITAL / max(len(picks), 1)   # 等权目标金额
    cap_amt = TOTAL_CAPITAL * MAX_WEIGHT          # 第一遍的绝对上限（名义预算的比例）
    path = {}   # 日期 → (市值, 累计分红)
    for d in [pd.Timestamp("2026-11-02"), pd.Timestamp("2026-11-03"),
              pd.Timestamp("2026-11-04"), pd.Timestamp("2026-11-05")]:
        path[d] = [0.0, 0.0]
    for sym in picks:
        df = px.get(sym)
        if df is None or not len(df):
            skipped.append({"symbol": sym, "reason": "无行情"})
            continue
        if ENTRY not in df.index:
            skipped.append({"symbol": sym, "reason": f"11-02 停牌/无数据"})
            continue
        op = float(df.loc[ENTRY, "open"])
        if not (op > 0):
            skipped.append({"symbol": sym, "reason": "开盘价异常"})
            continue
        lots = int(min(target, cap_amt) // (op * LOT))
        if lots < 1:
            if op * LOT > cap_amt:
                skipped.append({"symbol": sym,
                                "reason": f"一手 {op * LOT:,.0f} 元 > 单票上限 {cap_amt:,.0f} 元"})
                continue
            lots = 1          # 至少 1 手（金额没超上限但目标不够买整手）
        shares = lots * LOT
        cost = shares * op
        plan.append({"symbol": sym, "op": op, "lots": lots,
                     "shares": lots * LOT, "cost": cost})

    # ---- 第二遍：施加单票硬上限（占「实际投入」的比例）----
    # 注意：等权目标 target 固定在名义预算上，不随裁剪缩小（否则会越裁越少）；
    # 迭代只做两件事：把超限的票按整手裁小、裁到 0 就剔掉，剔除后分母变小、
    # 权重会反弹，所以要反复到收敛为止。
    for _ in range(8):
        if not plan:
            break
        t1 = sum(p["cost"] for p in plan)
        cap2 = t1 * MAX_WEIGHT
        changed = False
        new_plan = []
        for p in plan:
            if p["cost"] > cap2:
                l2 = int(cap2 // (p["op"] * LOT))
                if l2 < 1:
                    if p["op"] * LOT > cap2:
                        skipped.append({"symbol": p["symbol"],
                                        "reason": f"一手 {p['op'] * LOT:,.0f} 元 > 单票上限 {cap2:,.0f} 元"})
                        changed = True
                        continue
                    l2 = 1
                if l2 != p["lots"]:
                    changed = True
                p["lots"] = l2
                p["shares"] = l2 * LOT
                p["cost"] = l2 * LOT * p["op"]
            new_plan.append(p)
        plan = new_plan
        if not changed:
            break

    for p in plan:
        sym, op, shares = p["symbol"], p["op"], p["shares"]
        cost = p["cost"]
        df = px.get(sym)
        close = float(df.loc[EXIT, "close"]) if EXIT in df.index else None
        if close is None:
            skipped.append({"symbol": sym, "reason": "11-05 无收盘价"})
            continue
        val = shares * close
        # 分红：除权日在 (建仓日, 卖出日] 之间
        div_net = 0.0
        for dv in divs.get(sym, []):
            ex = pd.Timestamp(dv["ex_date"])
            if ENTRY < ex <= EXIT:
                hold = (ex - ENTRY).days
                net = dv["per_share"] * shares * (1 - div_tax_rate(hold))
                div_net += net
                path[ex] = path.get(ex, [0.0, 0.0])
                path[ex][1] += net
        total_cost += cost
        total_val += val
        total_div += div_net
        for d in path:
            if d in df.index:
                path[d][0] += shares * float(df.loc[d, "close"])
        prev = float(df.loc[SIGNAL_DATE, "close"]) if SIGNAL_DATE in df.index else None
        gap = (op / prev - 1) * 100 if prev else None
        rows.append({"symbol": sym, "name": names.get(sym, sym), "shares": shares,
                     "buy_open": round(op, 3), "sell_close": round(close, 3),
                     "cost": round(cost, 2), "value": round(val, 2),
                     "pnl": round(val - cost, 2), "ret_pct": round((close / op - 1) * 100, 2),
                     "div_net": round(div_net, 2), "gap_open_pct": None if gap is None else round(gap, 2)})
    fee = total_cost * COST_BUY + total_val * COST_SELL + 2 * len(rows) * MIN_FEE
    gross = total_val + total_div - total_cost
    net = gross - fee
    # 每只的实际权重（按买入成本 / 组合总投入），用来验证「单票上限」真的生效
    for r in rows:
        r["weight_pct"] = round(r["cost"] / total_cost * 100, 2) if total_cost else None
    max_w = max((r["weight_pct"] for r in rows), default=None)
    day_path = []
    for d in sorted(path):
        mv, dv = path[d]
        # 分红在除权日当天计入现金
        day_path.append({"date": str(d.date()), "mv": round(mv, 2), "div": round(dv, 2),
                         "total": round(mv + dv, 2),
                         "ret_pct": round((mv + dv) / total_cost * 100, 3) if total_cost else None})
    return {
        "label": label, "n": len(rows), "n_skipped": len(skipped), "skipped": skipped,
        "total_cost": round(total_cost, 2), "market_value": round(total_val, 2),
        "target_per_name": round(target, 2), "cap_amount": round(cap_amt, 2),
        "max_weight_pct": max_w,
        "cash_div": round(total_div, 2), "fee": round(fee, 2),
        "pnl_gross": round(gross, 2), "pnl_net": round(net, 2),
        "ret_gross_pct": round(gross / total_cost * 100, 3) if total_cost else None,
        "ret_net_pct": round(net / total_cost * 100, 3) if total_cost else None,
        "day_path": day_path, "rows": sorted(rows, key=lambda r: r["ret_pct"], reverse=True),
    }


def main():
    REPORT.mkdir(exist_ok=True)
    # ---------- 1. 10-30 截面 ----------
    sc = pd.read_parquet(PROJ / "data" / "scores.parquet",
                         columns=["datetime", "symbol", "price_score", "fund_score",
                                  "event_score", "board_name", "close"])
    sc["datetime"] = pd.to_datetime(sc["datetime"])
    day = sc[sc["datetime"] == SIGNAL_DATE].copy()
    day["symbol"] = day["symbol"].astype(str)
    print(f"截面 {SIGNAL_DATE.date()}：{len(day)} 只")

    w = json.loads((RESULTS / "backtest.json").read_text(encoding="utf-8"))["weights"]
    wp, wf, we = w["recommended"]["price"], w["recommended"]["fund"], w["recommended"]["event"]
    vwp, vwf, vwe = (w["valid_selected"]["price"], w["valid_selected"]["fund"],
                     w["valid_selected"]["event"])
    day["mix_rec"] = wp * day["price_score"] + wf * day["fund_score"] + we * day["event_score"]
    day["mix_valid"] = vwp * day["price_score"] + vwf * day["fund_score"] + vwe * day["event_score"]

    variants = [
        ("A 混合分(推荐 0.65/0.30/0.05) top20（策略原样全池）",
         select(day, "mix_rec", 20, require_px=False), None),
        ("B 混合分(推荐权重) top20（干净池）", select(day, "mix_rec", 20), None),
        ("C 混合分(推荐权重) top20 + 行业≤3（干净池）", select(day, "mix_rec", 20, 3), 3),
        ("D 混合分(验证期权重 0.5/0.4/0.1) top20（干净池）", select(day, "mix_valid", 20), None),
        ("E 纯价量分 top20（干净池）", select(day, "price_score", 20), None),
        ("F 纯基本面分 top20（干净池）", select(day, "fund_score", 20), None),
        ("G 混合分(推荐权重) top50 + 行业≤3（策略正式参数，干净池）",
         select(day, "mix_rec", 50, 3), 3),
    ]
    n_px = int(day["close"].notna().sum())
    print(f"10-30 面板有收盘价 {n_px} 只 / 共 {len(day)} 只；"
          f"其余 {len(day) - n_px} 只价格只更新到 10-27 或早已停牌退市")

    # ---------- 2. 取价 + 分红 ----------
    all_syms = sorted({s for _, p, _ in variants for s in p})
    print(f"需要行情 {len(all_syms)} 只")
    px, divs = {}, {}
    for i, s in enumerate(all_syms, 1):
        df = fetch_raw(tx_symbol(s), count=12)
        if len(df):
            px[s] = df
        time.sleep(0.25)
        if i % 20 == 0:
            print(f"   行情 {i}/{len(all_syms)}")
    for s in all_syms:
        divs[s] = fetch_dividends(s)
        time.sleep(0.2)

    names = fetch_names(all_syms)
    bench = fetch_raw(tx_symbol(BENCH), count=12)
    b_open = float(bench.loc[ENTRY, "open"]) if ENTRY in bench.index else None
    b_close = float(bench.loc[EXIT, "close"]) if EXIT in bench.index else None
    bench_ret = (b_close / b_open - 1) * 100 if b_open and b_close else None

    # ---------- 3. 逐变体评估 ----------
    results = []
    stale_syms = set(day.loc[day["close"].isna(), "symbol"])
    for label, picks, cap in variants:
        r = evaluate(picks, px, names, divs, label)
        r["picks"] = picks
        r["n_stale_score"] = sum(1 for s in picks if s in stale_syms)
        results.append(r)
        print(f"{label:<44} n={r['n']:>2} 毛 {_f(r['ret_gross_pct'])}  净 {_f(r['ret_net_pct'])}"
              f"  投入 {r['total_cost']:,.0f}  分数带缺口 {r['n_stale_score']}")

    # ---------- 4. 实盘 20 只对照 ----------
    book = json.loads((LGBM / "results" / "positions_A.json").read_text(encoding="utf-8"))
    live_syms = [p["symbol"] for p in book["positions"]]
    live_rows = []
    live_cost = live_val = live_div = 0.0
    live_path = {d: [0.0, 0.0] for d in [pd.Timestamp("2026-11-02"), pd.Timestamp("2026-11-03"),
                                          pd.Timestamp("2026-11-04"), pd.Timestamp("2026-11-05")]}
    for p in book["positions"]:
        sym = p["symbol"]
        df_l = px.get(sym)
        if df_l is None or not len(df_l):
            df_l = fetch_raw(tx_symbol(sym), count=12)
            time.sleep(0.2)
        if df_l is None or not len(df_l) or EXIT not in df_l.index:
            continue
        close = float(df_l.loc[EXIT, "close"])
        sh = p["shares"]
        live_cost += sh * p["entry_price"]
        live_val += sh * close
        for dv in fetch_dividends(sym):
            ex = pd.Timestamp(dv["ex_date"])
            if ENTRY < ex <= EXIT:
                hold = (ex - ENTRY).days
                net = dv["per_share"] * sh * (1 - div_tax_rate(hold))
                live_div += net
                if ex in live_path:
                    live_path[ex][1] += net
        for d in live_path:
            if d in df_l.index:
                live_path[d][0] += sh * float(df_l.loc[d, "close"])
        live_rows.append({"symbol": sym, "name": p["name"], "shares": sh,
                          "entry": p["entry_price"], "close": close})
    live_fee = live_cost * COST_BUY + live_val * COST_SELL + 2 * len(live_rows) * MIN_FEE
    live_gross = live_val + live_div - live_cost
    live = {"label": "实盘 20 只（csi300_lgbm LightGBM 选股）", "n": len(live_rows),
            "total_cost": round(live_cost, 2), "market_value": round(live_val, 2),
            "cash_div": round(live_div, 2), "fee": round(live_fee, 2),
            "pnl_gross": round(live_gross, 2), "pnl_net": round(live_gross - live_fee, 2),
            "ret_gross_pct": round(live_gross / live_cost * 100, 3),
            "ret_net_pct": round((live_gross - live_fee) / live_cost * 100, 3),
            "day_path": [{"date": str(d.date()), "mv": round(mv, 2), "div": round(dv, 2),
                          "total": round(mv + dv, 2),
                          "ret_pct": round((mv + dv) / live_cost * 100, 3)}
                         for d, (mv, dv) in sorted(live_path.items())],
            "rows": sorted(live_rows, key=lambda r: r["close"] / r["entry"] - 1, reverse=True)}

    # ---------- 5. 重叠度 ----------
    live_set = set(live_syms)
    overlap = {}
    for r in results:
        s = set(r["picks"])
        inter = sorted(s & live_set)
        overlap[r["label"]] = {"n_overlap": len(inter), "overlap": inter,
                               "n_only_variant": len(s - live_set),
                               "n_only_live": len(live_set - s)}
    # 实盘 20 只在那天的「混合分排名」（做个参照：被基本面加权排在第几）
    rank_map = {s: i + 1 for i, s in enumerate(day.sort_values("mix_rec", ascending=False)["symbol"])}
    live_ranks = sorted([(rank_map.get(s, 999), s) for s in live_syms])

    out = {
        "signal_date": str(SIGNAL_DATE.date()), "entry": str(ENTRY.date()), "exit": str(EXIT.date()),
        "weights": {"recommended": {"price": wp, "fund": wf, "event": we},
                    "valid_selected": {"price": vwp, "fund": vwf, "event": we}},
        "cost_model": {"buy": COST_BUY, "sell": COST_SELL, "min_fee": MIN_FEE,
                       "total_capital": TOTAL_CAPITAL, "max_weight": MAX_WEIGHT,
                       "rule": "等权目标 + 单票上限 5% + 整手向下取整（至少 1 手）",
                       "lot": LOT},
        "benchmark": {"code": BENCH, "open": b_open, "close": b_close,
                      "ret_pct": round(bench_ret, 3) if bench_ret else None},
        "variants": results, "live": live, "overlap": overlap,
        "live_mix_rank": [{"rank": r, "symbol": s} for r, s in live_ranks],
    }
    (RESULTS / "counterfactual_oct30.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 6. 打印 ----------
    print("\n" + "=" * 100)
    print(f"对照：基本面加权策略（{SIGNAL_DATE.date()} 选股）vs 实盘 20 只"
          f"（买 {ENTRY.date()} 开盘 → 卖 {EXIT.date()} 收盘）")
    print("=" * 100)
    print(f"{'组合':<46}{'只数':>5}{'投入(元)':>12}{'市值':>12}{'分红':>8}"
          f"{'费用':>8}{'净收益':>11}{'净收益率':>10}")
    for r in results + [live]:
        print(f"{r['label']:<46}{r['n']:>5}{r['total_cost']:>12,.0f}{r['market_value']:>12,.0f}"
              f"{r['cash_div']:>8,.0f}{r['fee']:>8,.0f}{r['pnl_net']:>11,.0f}"
              f"{r['ret_net_pct']:>9.2f}%")
    print(f"{'沪深300（同期）':<46}{'':>5}{'':>12}{'':>12}{'':>8}{'':>8}{'':>11}"
          f"{bench_ret:>9.2f}%")
    print("\n重叠度（与实盘 20 只）：")
    for k, v in overlap.items():
        print(f"  {k:<44} 重合 {v['n_overlap']:>2} 只  仅策略 {v['n_only_variant']:>2}  仅实盘 {v['n_only_live']:>2}")
    print(f"\n实盘 20 只在混合分里的排名（1=最好，637=最差）：")
    print("  " + "  ".join(f"{r}:{s}" for r, s in live_ranks[:20]))
    print(f"\n已写出 {RESULTS / 'counterfactual_oct30.json'}")


if __name__ == "__main__":
    main()
