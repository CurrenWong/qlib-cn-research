"""抓基本面 PIT 数据（东方财富 F10 三个接口）→ parquet 缓存。

三个来源：
  ① RPT_F10_FINANCE_MAINFINADATA  财务指标（165 字段），带 REPORT_DATE(报告期) + NOTICE_DATE(披露日)
  ② RPT_VALUEANALYSIS_DET        日频估值 PE_TTM/PB/PS/PEG/市值 + 行业名(BOARD_NAME)
  ③ RPT_PUBLIC_OP_NEWPREDICT     业绩预告（NOTICE_DATE + 增幅区间）

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\fetch_fundamental.py            # 全量（637 只）
    ..\\..\\.venv\\Scripts\\python.exe tools\\fetch_fundamental.py --symbols SH600519,SZ000001

产出：
    data\\fund_financials.parquet
    data\\fund_valuation.parquet
    data\\fund_predict.parquet
    results\\fetch_log.json
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
DATA = PROJ / "data"
RESULTS = PROJ / "results"
DATA.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
SEC_HEADERS = {**UA, "Referer": "https://emweb.securities.eastmoney.com/"}
WEB_HEADERS = {**UA, "Referer": "https://data.eastmoney.com/"}

# 财务指标要哪些字段（全量 165 字段太胖，按需取）
FIN_FIELDS = [
    "SECUCODE", "SECURITY_CODE", "SECURITY_NAME_ABBR", "REPORT_DATE", "REPORT_TYPE",
    "NOTICE_DATE", "UPDATE_DATE",
    "EPSJB", "BPS", "ROEJQ", "ROIC", "XSMLL", "ZZCJLL", "ZCFZL", "JYXJLYYSR", "XSJXLYYSR",
    "TOTALOPERATEREVETZ", "PARENTNETPROFITTZ", "KCFJCXSYJLRTZ", "YYZSRGDHBZC",
    "NETPROFITRPHBZC", "BPSTZ", "ROEJQTZ", "ZCFZLTZ", "MGJYXJJE", "GUARD_SPEED_RATIO",
    "NETCASH_OPERATE_PK", "PARENTNETPROFIT", "TOTALOPERATEREVE", "MLR",
    "DJD_TOI_YOY", "DJD_DPNP_YOY", "DJD_DEDUCTDPNP_YOY", "DJD_TOI_QOQ", "DJD_DPNP_QOQ",
    "CA_TA", "INTEREST_DEBT_RATIO", "SALE_ER_PK", "RE_RATIO_PK", "INVENTORY_TR_YOY",
]

FIN_URL = ("https://datacenter.eastmoney.com/securities/api/data/v1/get"
           "?reportName=RPT_F10_FINANCE_MAINFINADATA&columns=ALL&filter="
           "(SECUCODE%3D%22{code}%22)&pageNumber=1&pageSize=60&sortTypes=-1&"
           "sortColumns=REPORT_DATE&source=HSF10&client=PC")
VAL_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get"
           "?reportName=RPT_VALUEANALYSIS_DET&columns=ALL&filter="
           "(SECURITY_CODE%3D%22{code}%22)&pageNumber=1&pageSize=3000&sortTypes=-1&"
           "sortColumns=TRADE_DATE&source=WEB&client=WEB")
PRE_URL = ("https://datacenter-web.eastmoney.com/api/data/v1/get"
           "?reportName=RPT_PUBLIC_OP_NEWPREDICT&columns=ALL&filter="
           "(SECURITY_CODE%3D%22{code}%22)&pageNumber=1&pageSize=30&sortTypes=-1&"
           "sortColumns=NOTICE_DATE&source=WEB&client=WEB")


def qlib_to_secucode(sym: str) -> str:
    """SH600519 -> 600519.SH ; SZ000001 -> 000001.SZ ; BJ430017 -> 430017.BJ"""
    code = "".join(c for c in sym if c.isdigit())
    if sym.upper().startswith("SH"):
        return f"{code}.SH"
    if sym.upper().startswith("SZ"):
        return f"{code}.SZ"
    return f"{code}.BJ"


def secucode_to_qlib(s: str) -> str:
    code, mkt = s.split(".")
    return ("SH" if mkt == "SH" else "SZ" if mkt == "SZ" else "BJ") + code


def fetch(url: str, headers: dict, tries: int = 3, timeout: int = 25):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code != 200:
                last = f"HTTP {r.status_code}"
                time.sleep(1.2 * (i + 1))
                continue
            j = r.json()
            if j.get("success") is False:
                last = str(j.get("message"))[:80]
                time.sleep(1.0 * (i + 1))
                continue
            return (j.get("result") or {}).get("data") or []
        except Exception as e:                                  # noqa: BLE001
            last = f"{type(e).__name__}: {str(e)[:60]}"
            time.sleep(1.2 * (i + 1))
    return {"__error__": last}


def do_one(sym: str):
    sc = qlib_to_secucode(sym)
    code = sc.split(".")[0]
    out = {"symbol": sym}

    rows = fetch(FIN_URL.format(code=sc), SEC_HEADERS)
    if isinstance(rows, list):
        keep = []
        for r in rows:
            rec = {k: r.get(k) for k in FIN_FIELDS}
            rec["symbol"] = sym
            keep.append(rec)
        out["fin"] = keep
    else:
        out["fin"] = []
        out["fin_err"] = rows.get("__error__")

    rows = fetch(VAL_URL.format(code=code), WEB_HEADERS)
    if isinstance(rows, list):
        keep = []
        for r in rows:
            keep.append({
                "symbol": sym, "trade_date": r.get("TRADE_DATE"),
                "pe_ttm": r.get("PE_TTM"), "pe_lar": r.get("PE_LAR"),
                "pb_mrq": r.get("PB_MRQ"), "ps_ttm": r.get("PS_TTM"),
                "peg_car": r.get("PEG_CAR"), "total_mv": r.get("TOTAL_MARKET_CAP"),
                "float_mv": r.get("NOTLIMITED_MARKETCAP_A"), "close_price": r.get("CLOSE_PRICE"),
                "change_rate": r.get("CHANGE_RATE"), "board_name": r.get("BOARD_NAME"),
            })
        out["val"] = keep
    else:
        out["val"] = []
        out["val_err"] = rows.get("__error__")

    rows = fetch(PRE_URL.format(code=code), WEB_HEADERS)
    if isinstance(rows, list):
        keep = []
        for r in rows:
            lo, hi = r.get("ADD_AMP_LOWER"), r.get("ADD_AMP_UPPER")
            mid = (lo + hi) / 2 if (lo is not None and hi is not None) else lo
            keep.append({
                "symbol": sym, "notice_date": r.get("NOTICE_DATE"),
                "report_date": r.get("REPORT_DATE"), "predict_growth": mid,
                "predict_low": lo, "predict_high": hi, "predict_type": r.get("PREDICT_TYPE"),
                "reason": (r.get("CHANGE_REASON_EXPLAIN") or "")[:200],
            })
        out["pre"] = keep
    else:
        out["pre"] = []
        out["pre_err"] = rows.get("__error__")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.symbols:
        syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        feats = pd.read_parquet(_ROOT + r"/projects/csi300_lgbm/data/features.parquet",
                                columns=["symbol"])
        syms = sorted(feats["symbol"].unique().tolist())
    if args.limit:
        syms = syms[: args.limit]
    print(f"目标股票 {len(syms)} 只，并发 {args.workers}")

    fin, val, pre, errors = [], [], [], []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(do_one, s): s for s in syms}
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            fin.extend(r["fin"])
            val.extend(r["val"])
            pre.extend(r["pre"])
            for k in ("fin", "val", "pre"):
                if r.get(f"{k}_err"):
                    errors.append({"symbol": r["symbol"], "part": k, "err": r[f"{k}_err"]})
            if i % 50 == 0:
                print(f"  {i}/{len(syms)}  fin={len(fin)} val={len(val)} pre={len(pre)} "
                      f"err={len(errors)}  {time.time()-t0:.0f}s", flush=True)

    for name, rows in [("fund_financials", fin), ("fund_valuation", val), ("fund_predict", pre)]:
        df = pd.DataFrame(rows)
        p = DATA / f"{name}.parquet"
        df.to_parquet(p, index=False)
        print(f"写出 {p}  {df.shape}  {p.stat().st_size/1024/1024:.1f}MB")

    log = {
        "n_symbols": len(syms), "n_fin_rows": len(fin), "n_val_rows": len(val),
        "n_pre_rows": len(pre), "n_errors": len(errors),
        "errors": errors[:100], "seconds": round(time.time() - t0, 1),
        "symbols_with_fin": len({r["symbol"] for r in fin}),
        "symbols_with_val": len({r["symbol"] for r in val}),
    }
    (RESULTS / "fetch_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    print(json.dumps({k: v for k, v in log.items() if k != "errors"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
