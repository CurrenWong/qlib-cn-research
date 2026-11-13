"""A 口径持仓的每日净值追踪（2026-11-02 开盘买入起，连续追踪一个月）。

用法（手动跑，按用户偏好不注册定时任务）：
    D:\\Project\\qlib\\.venv\\Scripts\\python.exe tools\\track_pnl.py

行为：
  1. 读冻结的持仓台账 results/positions_A.json（不存在则从 results/pnl_monday.json 自动生成）
  2. 拉腾讯**不复权**日线（20 只 + 沪深300），沪深300 的 bar 日期当交易日历
  3. 逐交易日算：持仓市值 / 累计现金分红 / 总资产 / 收益率 / 对沪深300 超额
  4. 追加或覆盖写 results/track_pnl.csv（每交易日一行）+ results/track_positions_latest.csv（当日逐只明细）
  5. 打印今日快照 + 整段序列 + 涨跌幅贡献排序

分红处理（别把除权当亏损）：
  用东财 RPT_SHAREBONUS_DET 取除权除息日 + 每 10 股派息（税前）。
  除权日股价会相应下调，所以把现金分红单独计入「现金」，总资产 = 市值 + 现金。
  红利税按持有期差别化：≤1 个月 20%、1 个月~1 年 10%、>1 年 0%（A 股规则）。
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
RESULTS = PROJ / "results"
POSITIONS = RESULTS / "positions_A.json"
PNL_JSON = RESULTS / "pnl_monday.json"
TRACK_CSV = RESULTS / "track_pnl.csv"
POS_CSV = RESULTS / "track_positions_latest.csv"
DAILY_LOG = PROJ / "report" / "track_daily_log.md"

ENTRY_DATE = "2026-11-02"
BENCH = "SH000300"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}
KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
DIV_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get?"
           "sortColumns=EX_DIVIDEND_DATE&sortTypes=-1&pageSize=30&pageNumber=1&"
           "reportName=RPT_SHAREBONUS_DET&columns=ALL&filter="
           "(SECURITY_CODE%3D%22{code}%22)")


def tx_symbol(code: str) -> str:
    return ("sh" if code.upper().startswith("SH") else "sz") + "".join(c for c in code if c.isdigit())


def fetch_raw(symbol: str, count: int = 60) -> pd.DataFrame:
    """腾讯 kline（不复权）。返回 index=date, 列 open/close/high/low/volume。"""
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


def fetch_dividends(symbol: str) -> list[dict]:
    """取该票 2026 年的分红记录：除权除息日 + 每 10 股派息（税前）。"""
    code = "".join(c for c in symbol if c.isdigit())
    out = []
    try:
        r = requests.get(DIV_URL.format(code=code), headers={"User-Agent": UA["User-Agent"]}, timeout=25)
        js = r.json()
        recs = (js.get("result") or {}).get("data") or []
        for x in recs:
            ex = str(x.get("EX_DIVIDEND_DATE", ""))[:10]
            if not ex or not ex.startswith("2026"):
                continue
            try:
                per10 = float(x.get("PRETAX_BONUS_RMB") or 0)
            except (TypeError, ValueError):
                per10 = 0.0
            out.append({"ex_date": ex, "per_share": per10 / 10.0,
                        "raw_per10": x.get("PRETAX_BONUS_RMB")})
    except Exception as e:  # noqa: BLE001
        print(f"    {symbol} 分红接口失败: {type(e).__name__}: {str(e)[:60]}")
    return out


def div_tax_rate(hold_days: int) -> float:
    """A 股红利税差别化：≤1 个月 20%，1 个月~1 年 10%，>1 年 免税。"""
    if hold_days <= 30:
        return 0.20
    if hold_days <= 365:
        return 0.10
    return 0.0


def bootstrap_positions() -> dict:
    """从 pnl_monday.json 的 A 口径结果生成冻结台账。"""
    src = json.loads(PNL_JSON.read_text(encoding="utf-8"))
    rows = [r for r in src["rows"] if r.get("A_shares")]
    book = {
        "created_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "basis": "A 口径：每只约 1 万元，向上取整到整手，零头补一手，至少 1 手",
        "signal_date": src["summary"]["signal_date"],
        "entry_date": src["summary"]["buy_date"],
        "entry_price_type": "开盘价（不复权）",
        "benchmark": BENCH,
        "positions": [{
            "symbol": r["symbol"], "name": r["name"], "board": r["board"],
            "shares": r["A_shares"], "entry_price": r["buy_open"], "cost": r["A_cost"],
        } for r in sorted(rows, key=lambda x: x["rank"])],
    }
    book["total_cost"] = round(sum(p["cost"] for p in book["positions"]), 2)
    POSITIONS.write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成冻结台账: {POSITIONS}（总成本 {book['total_cost']:,.0f} 元）")
    return book


def main():
    book = json.loads(POSITIONS.read_text(encoding="utf-8")) if POSITIONS.exists() else bootstrap_positions()
    pos = book["positions"]
    entry = pd.Timestamp(book["entry_date"])
    print(f"台账: {len(pos)} 只 | 建仓 {book['entry_date']} 开盘 | 总成本 {book['total_cost']:,.0f} 元")

    # ---- 取价 ----
    closes = {}
    for p in pos:
        df = fetch_raw(tx_symbol(p["symbol"]), count=60)
        closes[p["symbol"]] = df["close"] if len(df) else pd.Series(dtype=float)
        time.sleep(0.3)
    bench_df = fetch_raw(tx_symbol(BENCH), count=60)
    if not len(bench_df):
        print("❌ 基准指数取数失败，终止")
        return
    bench_close = bench_df["close"]
    # 基准起点：11-02 开盘（与组合建仓价同一时点）+ 11-02 收盘（更可交易的起算法）
    bench_open_base = float(bench_df.loc[entry, "open"]) if entry in bench_df.index else None
    bench_close_base = float(bench_df.loc[entry, "close"]) if entry in bench_df.index else None

    # 交易日历 = 沪深300 的 bar 日期（从建仓日起）
    cal = [d for d in bench_close.index if d >= entry]
    if not cal:
        print("❌ 建仓日之后没有交易日")
        return

    # ---- 分红（除权日 → 现金）----
    divs = {}
    for p in pos:
        ds = fetch_dividends(p["symbol"])
        divs[p["symbol"]] = [d for d in ds if pd.Timestamp(d["ex_date"]) > entry]
        time.sleep(0.25)
    div_events = []
    for p in pos:
        for d in divs[p["symbol"]]:
            hold_days = (pd.Timestamp(d["ex_date"]) - entry).days
            tax = div_tax_rate(hold_days)
            gross = d["per_share"] * p["shares"]
            div_events.append({
                "symbol": p["symbol"], "name": p["name"], "ex_date": d["ex_date"],
                "per_share": round(d["per_share"], 4), "shares": p["shares"],
                "gross": round(gross, 2), "tax_rate": tax,
                "net": round(gross * (1 - tax), 2), "hold_days": hold_days})
    if div_events:
        print("\n跟踪期内除权除息:")
        for e in div_events:
            print(f"  {e['name']} {e['symbol']} 除权日 {e['ex_date']} | 每股 {e['per_share']} 元 "
                  f"| 持 {e['hold_days']} 天 → 红利税 {e['tax_rate'] * 100:.0f}% | "
                  f"税前 {e['gross']:,.2f} 元 → 税后 {e['net']:,.2f} 元")

    # ---- 逐日 ----
    rows_out = []
    detail = None
    for d in cal:
        cash = 0.0
        mv = 0.0
        stale = 0
        per = []
        for p in pos:
            s = closes[p["symbol"]]
            if d in s.index:
                px = float(s.loc[d])
            else:
                valid = s[s.index < d]
                if not len(valid):
                    px = float(p["entry_price"])
                    stale += 1
                else:
                    px = float(valid.iloc[-1])   # 停牌：沿用最后价
                    stale += 1
            val = px * p["shares"]
            mv += val
            cash += sum(e["net"] for e in div_events
                        if e["symbol"] == p["symbol"] and entry < pd.Timestamp(e["ex_date"]) <= d)
            per.append({**p, "close": px, "mkt_value": val, "pnl": val - p["cost"],
                        "ret_pct": (px / p["entry_price"] - 1) * 100})
        total = mv + cash
        b_px = float(bench_close.loc[d])
        rows_out.append({
            "date": d.strftime("%Y-%m-%d"),
            "mv": round(mv, 2), "cash_div": round(cash, 2), "total": round(total, 2),
            "cost": book["total_cost"],
            "ret_pct": round((total / book["total_cost"] - 1) * 100, 3),
            "bench_close": b_px,
            "bench_ret_pct": round((b_px / bench_close_base - 1) * 100, 3),
            "bench_ret_from_open_pct": (round((b_px / bench_open_base - 1) * 100, 3)
                                        if bench_open_base else None),
            "n_stale": stale,
        })
        if d == cal[-1]:
            detail = per

    df = pd.DataFrame(rows_out)
    # 超额：主口径用「同起点」基准（11-02 开盘，与组合建仓价同一时点）
    df["excess_pct"] = (df["ret_pct"] - df["bench_ret_from_open_pct"]).round(3)
    df["excess_vs_close_base_pct"] = (df["ret_pct"] - df["bench_ret_pct"]).round(3)

    # ---- 当日涨跌幅：今日收盘 vs 上一交易日收盘（不是累计）----
    prev_date = pd.Timestamp(df.iloc[-2]["date"]) if len(df) > 1 else None
    if detail:
        for row in detail:
            s = closes[row["symbol"]]
            if prev_date is None:
                row["day_ret_pct"] = float("nan")
                continue
            if prev_date in s.index:
                ppx = float(s.loc[prev_date])
            else:
                v = s[s.index < prev_date]
                ppx = float(v.iloc[-1]) if len(v) else None
            row["day_ret_pct"] = (row["close"] / ppx - 1) * 100 if ppx else float("nan")

    # ---- 写 CSV（同日期覆盖）----
    if TRACK_CSV.exists():
        old = pd.read_csv(TRACK_CSV)
        old = old[~old["date"].isin(df["date"])]
        df = pd.concat([old, df], ignore_index=True).sort_values("date")
    df.to_csv(TRACK_CSV, index=False, encoding="utf-8-sig")
    print(f"\n已写入 {TRACK_CSV}（{len(df)} 个交易日）")

    if detail:
        ddf = pd.DataFrame(detail)
        ddf["weight_pct"] = (ddf["mkt_value"] / ddf["mkt_value"].sum() * 100).round(2)
        ddf = ddf.sort_values("pnl")
        ddf.to_csv(POS_CSV, index=False, encoding="utf-8-sig")
        print(f"已写入 {POS_CSV}（当日逐只明细）")

    # ---- 打印 ----
    print("\n" + "=" * 100)
    print(f"{'日期':<12}{'市值':>12}{'累计分红':>10}{'总资产':>12}{'收益率':>9}"
          f"{'300(开起)':>10}{'300(收起)':>10}{'超额':>8}{'停牌':>6}")
    for _, r in df.iterrows():
        print(f"{r['date']:<12}{r['mv']:>12,.0f}{r['cash_div']:>10,.0f}{r['total']:>12,.0f}"
              f"{r['ret_pct']:>8.2f}%{r['bench_ret_from_open_pct']:>9.2f}%{r['bench_ret_pct']:>9.2f}%"
              f"{r['excess_pct']:>7.2f}%{r['n_stale']:>6}")

    if detail:
        print(f"\n当日逐只（{df.iloc[-1]['date']}）按累计盈亏排序:")
        print(f"{'名称':<10}{'代码':<10}{'股数':>7}{'成本价':>9}{'现价':>9}{'市值':>11}"
              f"{'盈亏':>10}{'累计%':>9}{'当日%':>9}{'权重':>8}")
        for r in ddf.itertuples():
            print(f"{r.name:<10}{r.symbol:<10}{r.shares:>7}{r.entry_price:>9.2f}{r.close:>9.2f}"
                  f"{r.mkt_value:>11,.0f}{r.pnl:>10,.0f}{r.ret_pct:>8.2f}%"
                  f"{r.day_ret_pct:>8.2f}%{r.weight_pct:>7.2f}%")

    last = df.iloc[-1]
    print("\n" + "=" * 100)
    print(f"最新: {last['date']} | 总资产 {last['total']:,.0f} 元 | 成本 {book['total_cost']:,.0f} 元 "
          f"| 收益率 {last['ret_pct']:+.2f}% | 沪深300 {last['bench_ret_from_open_pct']:+.2f}%（开起） "
          f"/ {last['bench_ret_pct']:+.2f}%（收起）| 超额 {last['excess_pct']:+.2f}%")

    # ---- 追加人读日志（同一日期覆盖）----
    prev = df.iloc[-2] if len(df) > 1 else None
    if prev is not None:
        day_ret = (last["total"] / prev["total"] - 1) * 100
        day_bench = (last["bench_close"] / prev["bench_close"] - 1) * 100
        day_excess = day_ret - day_bench
    else:
        day_ret = day_bench = day_excess = float("nan")
    ddf2 = ddf.sort_values("day_ret_pct", ascending=False)
    up = "、".join(f"{r['name']} {r['day_ret_pct']:+.2f}%" for _, r in ddf2.head(3).iterrows())
    dn = "、".join(f"{r['name']} {r['day_ret_pct']:+.2f}%" for _, r in ddf2.tail(3).iloc[::-1].iterrows())
    maxw = ddf.sort_values("mkt_value", ascending=False).iloc[0]
    maxw_w = maxw["mkt_value"] / mv * 100 if mv else 0.0
    sec = (f"## {last['date']}\n\n"
           f"- 总资产 **{last['total']:,.0f} 元**（成本 {book['total_cost']:,.0f}）| "
           f"累计收益率 **{last['ret_pct']:+.2f}%** | 当日 {day_ret:+.2f}%\n"
           f"- 沪深300（开起）累计 {last['bench_ret_from_open_pct']:+.2f}% | 当日 {day_bench:+.2f}% | "
           f"**当日超额 {day_excess:+.2f}%** | **累计超额 {last['excess_pct']:+.2f}%**\n"
           f"- 当日最强：{up}\n- 当日最弱：{dn}\n"
           f"- 累计最大权重：{maxw['name']} {maxw_w:.2f}%（累计 {maxw['ret_pct']:+.2f}%）\n")
    if DAILY_LOG.exists():
        old = DAILY_LOG.read_text(encoding="utf-8")
        parts = old.split("\n## ")
        head = parts[0]
        body = [p for p in parts[1:] if not p.startswith(last["date"])]
        old = head + ("\n## " + "\n## ".join(body) if body else "")
    else:
        old = "# 每日净值快照（2026-11-02 建仓起）\n"
    if not old.endswith("\n"):
        old += "\n"
    DAILY_LOG.write_text(old + "\n" + sec, encoding="utf-8")
    print(f"已写入 {DAILY_LOG}")
    print(f"跟踪起点 {book['entry_date']}（开盘买入）｜已跟踪 {len(df)} 个交易日")


if __name__ == "__main__":
    main()
