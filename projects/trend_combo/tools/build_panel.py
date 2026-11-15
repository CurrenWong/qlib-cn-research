"""PIT 对齐 + 面板构建：把基本面快照摊成日频，与 qlib 价量面板合并。

关键纪律：**任何基本面字段只能从 NOTICE_DATE（披露日）当天起可见**，用 merge_asof(backward) 实现。
估值是日频，本身没有前视问题（PE_TTM 当天收盘价算的）。

用法：
    ..\\..\\.venv\\Scripts\\python.exe tools\\build_panel.py

产出：
    data\\panel_merged.parquet   (datetime, symbol, 价量特征 + 基本面因子 + 估值因子)
    results\\panel_stats.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[3])

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
DATA = PROJ / "data"
RESULTS = PROJ / "results"
RESULTS.mkdir(exist_ok=True)

PRICE_FEATS = Path(_ROOT + r"/projects/csi300_lgbm/data/features.parquet")

# ---------------------------------------------------------------- 因子分组
# 方向：+1 表示"数值越大越看多"。方向在 eval 里会用训练期 IC 符号复核。
PRICE_GROUPS = {
    "trend": ["mom_20", "mom_60", "mom_120", "ma_slope_20", "ma_slope_60",
              "ma_dist_20", "ma_dist_60", "ma_cross_5_20", "price_pos_250", "rel_str_60"],
    "reversal": ["rev_3", "rev_10", "mom_5_ex", "mom_20_ex", "dd_60"],
    "risk": ["vol_20", "vol_60", "hl_range_20", "beta_60", "alpha_20"],
    "flow": ["vol_ratio", "vol_ratio_5_20", "vol_z_20", "liq_change"],
}

FUND_GROUPS = {
    "valuation": ["pe_pct_3y", "pb_pct_3y", "ps_pct_3y", "pe_log", "cap_log"],
    "growth": ["rev_yoy", "rev_qoq", "np_yoy", "dnp_yoy", "rev_gap"],
    "quality": ["roe", "roic", "gross_margin", "net_margin", "debt_ratio",
                "cfo_to_np", "inv_turn"],
    "delta": ["roe_yoy", "bps_yoy"],
}
EVENT_FIELDS = ["predict_growth", "days_since_predict"]

FUND_DIRECTION = {   # +1 看多 / -1 看空
    "pe_pct_3y": -1, "pb_pct_3y": -1, "ps_pct_3y": -1, "pe_log": -1, "cap_log": 0,
    "rev_yoy": 1, "rev_qoq": 1, "np_yoy": 1, "dnp_yoy": 1, "rev_gap": 1,
    "roe": 1, "roic": 1, "gross_margin": 1, "net_margin": 1, "debt_ratio": -1,
    "cfo_to_np": 1, "inv_turn": 1,
    "roe_yoy": 1, "bps_yoy": 1,
    "predict_growth": 1, "days_since_predict": -1,
}


def asof_align(dates: pd.DataFrame, right: pd.DataFrame, on_right: str, cols: list):
    """按 symbol 做 merge_asof(backward)：取 notice_date <= date 的最新一条。"""
    if right.empty:
        for c in cols:
            dates[c] = np.nan
        return dates
    right = right.sort_values(on_right).reset_index(drop=True)
    out = pd.merge_asof(
        dates.sort_values("datetime"),
        right[["symbol", on_right] + cols].sort_values(on_right),
        left_on="datetime", right_on=on_right, by="symbol", direction="backward",
    )
    return out


def main():
    print("① 读价量面板 …")
    px = pd.read_parquet(PRICE_FEATS)
    px["datetime"] = pd.to_datetime(px["datetime"])
    px = px[["datetime", "symbol"] + [c for c in px.columns
                                      if c not in ("datetime", "symbol")]]
    print(f"   价量: {px.shape}  {px['datetime'].min().date()} ~ {px['datetime'].max().date()}"
          f"  {px['symbol'].nunique()} 只")

    print("② 读基本面缓存 …")
    fin = pd.read_parquet(DATA / "fund_financials.parquet")
    val = pd.read_parquet(DATA / "fund_valuation.parquet")
    pre = pd.read_parquet(DATA / "fund_predict.parquet")

    # ---------- 估值：日频 ----------
    val["trade_date"] = pd.to_datetime(val["trade_date"])
    val = val.dropna(subset=["trade_date"]).sort_values(["symbol", "trade_date"])
    def roll_pct(col):
        return (val.groupby("symbol")[col].rolling(750, min_periods=250)
                .rank(pct=True).reset_index(level=0, drop=True))
    val["pe_pct_3y"] = roll_pct("pe_ttm")
    val["pb_pct_3y"] = roll_pct("pb_mrq")
    val["ps_pct_3y"] = roll_pct("ps_ttm")
    val["pe_log"] = np.log(val["pe_ttm"].clip(lower=0.1))
    val["cap_log"] = np.log(val["total_mv"].clip(lower=1.0))
    val["board_name"] = val["board_name"].ffill()

    # ---------- 财务：季频 PIT ----------
    fin["NOTICE_DATE"] = pd.to_datetime(fin["NOTICE_DATE"])
    fin["REPORT_DATE"] = pd.to_datetime(fin["REPORT_DATE"])
    fin = fin.sort_values(["symbol", "NOTICE_DATE"])
    # 同一天披露多份（更正公告）→ 取最后一条
    fin = fin.drop_duplicates(["symbol", "NOTICE_DATE"], keep="last")
    fin["cfo_to_np"] = fin["NETCASH_OPERATE_PK"] / fin["PARENTNETPROFIT"].replace(0, np.nan)
    fin["rev_gap"] = fin["TOTALOPERATEREVETZ"] - fin["PARENTNETPROFITTZ"]
    fin_cols = {
        "roe": "ROEJQ", "roic": "ROIC", "gross_margin": "XSMLL", "net_margin": "ZZCJLL",
        "debt_ratio": "ZCFZL", "inv_turn": "GUARD_SPEED_RATIO",
        "rev_yoy": "TOTALOPERATEREVETZ", "rev_qoq": "YYZSRGDHBZC",
        "np_yoy": "PARENTNETPROFITTZ", "dnp_yoy": "KCFJCXSYJLRTZ",
        "roe_yoy": "ROEJQTZ", "bps_yoy": "BPSTZ",
    }
    fin_keep = fin[["symbol", "NOTICE_DATE", "REPORT_DATE"] + list(fin_cols.values())
                   + ["cfo_to_np", "rev_gap"]].copy()
    fin_keep = fin_keep.rename(columns={v: k for k, v in fin_cols.items()})
    fin_keep = fin_keep.dropna(subset=["NOTICE_DATE"])
    fin_keep["NOTICE_DATE"] = fin_keep["NOTICE_DATE"].dt.normalize()

    # ---------- 业绩预告：事件 PIT ----------
    pre["notice_date"] = pd.to_datetime(pre["notice_date"])
    pre = pre.sort_values(["symbol", "notice_date"])
    pre = pre.drop_duplicates(["symbol", "notice_date"], keep="last")
    pre = pre.dropna(subset=["notice_date"])
    pre["notice_date"] = pre["notice_date"].dt.normalize()

    print("③ PIT 对齐 …")
    base = px[["datetime", "symbol"]].copy()

    df = asof_align(base, fin_keep, "NOTICE_DATE",
                    list(fin_cols.keys()) + ["REPORT_DATE", "cfo_to_np", "rev_gap"])
    df["days_since_report"] = (df["datetime"] - df["NOTICE_DATE"]).dt.days

    df = asof_align(df, pre[["symbol", "notice_date", "predict_growth"]],
                    "notice_date", ["predict_growth"])
    df["days_since_predict"] = (df["datetime"] - df["notice_date"]).dt.days

    val_keep = val[["symbol", "trade_date", "pe_pct_3y", "pb_pct_3y", "ps_pct_3y",
                    "pe_log", "cap_log", "board_name", "pe_ttm", "pb_mrq", "total_mv"]]
    df = pd.merge(df, val_keep.rename(columns={"trade_date": "datetime"}),
                  on=["datetime", "symbol"], how="left")

    print("④ 合并价量特征 …")
    out = px.merge(df, on=["datetime", "symbol"], how="left")
    out["label_fwd20"] = out.groupby("symbol")["close"].transform(
        lambda s: s.shift(-20) / s - 1)

    out.to_parquet(DATA / "panel_merged.parquet", index=False)
    print(f"   写出 panel_merged.parquet {out.shape}")

    stats = {
        "rows": int(len(out)),
        "symbols": int(out["symbol"].nunique()),
        "dates": int(out["datetime"].nunique()),
        "start": str(out["datetime"].min().date()),
        "end": str(out["datetime"].max().date()),
        "coverage": {},
    }
    for c in list(FUND_GROUPS) + ["event"]:
        cols = FUND_GROUPS.get(c, EVENT_FIELDS)
        for cc in cols:
            if cc in out.columns:
                cov = float(out[cc].notna().mean())
                stats["coverage"][cc] = {
                    "notna": round(cov, 4),
                    "first_date": str(out.loc[out[cc].notna(), "datetime"].min().date())
                    if out[cc].notna().any() else None,
                }
    (RESULTS / "panel_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "coverage"},
                     ensure_ascii=False, indent=2))
    for cc, v in stats["coverage"].items():
        print(f"   {cc:18s} 覆盖 {v['notna']:.1%}  首日 {v['first_date']}")


if __name__ == "__main__":
    main()
