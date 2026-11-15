"""获取申万一级行业成分股（对应图片第 1 段：`get_industry_stock`）。

## 图片原版的问题
原图用 `pro.index_member_all(l1_code=code)` 逐行业取成分，再用
`for stk in stock_list: df = df_all[df_all['ts_code'] == stk]` 逐只反查行业——
5000 只股票要扫 5000 次全表，是 O(N×M)。这里改成 `drop_duplicates` 向量化。

## 两个数据源
1. **tushare**（图片原版）：`pro.index_classify(level='L1', src='SW2021')` 取行业表，
   `pro.index_member_all(l1_code=...)` 取成分。需要 token + 2000 积分。
2. **sws**（申万宏源官网接口，免 token）：行业表走 akshare 的 `sw_index_first_info()`，
   成分走 `institute-sw/api/index_publish/details/component_stocks/`。

> 注：akshare 的 `index_component_sw()` 传 `"801010.SI"` 会报 KeyError，
> 因为它的 symbol 不带 `.SI` 后缀，而 `sw_index_first_info()` 返回的代码带后缀。
> 这里直接调上游接口，字段自己归一。

## 用法
```cmd
cd /d <repo>
.venv\\Scripts\\python.exe tools\\fetch_sw_industry.py --source sws
.venv\\Scripts\\python.exe tools\\fetch_sw_industry.py --source tushare
```

## 产出
```
data\\sw_industry\\members.parquet   # 成分明细（含 in_date/out_date/is_new，可做 PIT）
data\\sw_industry\\map.parquet       # qlib_symbol → l1_code / l1_name 的最新映射
data\\sw_industry\\industries.parquet# 行业表
```

## PIT 用法（重要）
`members.parquet` 里保留了 `in_date` / `out_date`（申万调整成分的纳入/剔除日），
做历史回测时**不能**直接用最新成分——那是未来函数。按 as-of 取法：

```python
df = pd.read_parquet("data/sw_industry/members.parquet")
df["in_date"] = pd.to_datetime(df["in_date"], errors="coerce")
df["out_date"] = pd.to_datetime(df["out_date"], errors="coerce")

def industry_asof(day: str) -> pd.Series:
    d = pd.Timestamp(day)
    m = (df["in_date"].isna() | (df["in_date"] <= d)) & \
        (df["out_date"].isna() | (df["out_date"] > d))
    sub = df.loc[m].drop_duplicates("qlib_symbol", keep="last")
    return sub.set_index("qlib_symbol")["l1_name"]
```
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tushare_common import (  # noqa: E402
    MEMBER_ROW_LIMIT,
    PSEUDO_INDUSTRY_ALL,
    PSEUDO_INDUSTRY_TOTAL,
    bare_code_to_qlib,
    call_with_retry,
    iter_chunks,
    make_pro,
    ts_code_to_qlib,
)

HERE = Path(__file__).resolve().parent
QLIB_ROOT = HERE.parent
OUT_DIR = QLIB_ROOT / "data" / "sw_industry"

SWS_COMPONENT_URL = ("https://www.swsresearch.com/institute-sw/api/index_publish/"
                      "details/component_stocks/")
SWS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
}


# ------------------------------------------------------------------ 行业表


def fetch_industries_tushare(pro, src: str = "SW2021") -> pd.DataFrame:
    """申万一级行业表（图片原版接口）。

    `index_code` 形如 `801010.SI`；SW2021 版有 31 个一级行业。
    """
    df = call_with_retry(pro.index_classify, level="L1", src=src)
    df = df.copy()
    df["index_code"] = df["index_code"].astype(str).str.strip()
    df["industry_name"] = df["industry_name"].astype(str).str.strip()
    # index_classify 里 industry_code 是申万内部行业代码（110000 这种），
    # index_code 才是指数代码（801010.SI），成分接口按 index_code 查。
    out = df[["index_code", "industry_name"]].copy()
    out = out[out["index_code"].str.len() > 0].drop_duplicates("index_code")
    return out.reset_index(drop=True)


def fetch_industries_sws() -> pd.DataFrame:
    """申万一级行业表（申万宏源官网，免 token）。"""
    import akshare as ak

    df = ak.sw_index_first_info()
    out = pd.DataFrame({
        "index_code": df["行业代码"].astype(str).str.strip(),
        "industry_name": df["行业名称"].astype(str).str.strip(),
    })
    return out.drop_duplicates("index_code").reset_index(drop=True)


# ------------------------------------------------------------------ 成分


def fetch_members_tushare(pro, index_codes: list[str], is_new: str = "Y") -> pd.DataFrame:
    """逐行业取成分（图片原版接口）。

    `index_member_all` 单次最多 2000 行，一级行业最大 543 只，一次够用。
    """
    frames = []
    for i, code in enumerate(index_codes, 1):
        df = call_with_retry(pro.index_member_all, l1_code=code, is_new=is_new)
        if df is None or df.empty:
            print(f"    [{i}/{len(index_codes)}] {code} → 空")
            continue
        df = df.copy()
        df["index_code"] = code
        frames.append(df)
        print(f"    [{i}/{len(index_codes)}] {code} → {len(df)} 只")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def fetch_members_sws(index_codes: list[str]) -> pd.DataFrame:
    """逐行业取成分（申万宏源官网接口，免 token）。"""
    import requests

    frames = []
    for i, code in enumerate(index_codes, 1):
        # 上游只认不带 .SI 后缀的代码
        bare = code.split(".")[0]
        r = requests.get(
            SWS_COMPONENT_URL,
            params={"swindexcode": bare, "page": "1", "page_size": "10000"},
            headers=SWS_HEADERS, verify=False, timeout=30,
        )
        r.raise_for_status()
        res = (r.json().get("data") or {}).get("results") or []
        if not res:
            print(f"    [{i}/{len(index_codes)}] {bare} → 空")
            continue
        df = pd.DataFrame(res)
        df["index_code"] = code
        frames.append(df)
        print(f"    [{i}/{len(index_codes)}] {bare} → {len(df)} 只")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ------------------------------------------------------------------ 归一


def normalize_members(raw: pd.DataFrame, source: str) -> pd.DataFrame:
    """把两个源的不同字段名归一成同一套 schema。"""
    if raw.empty:
        return pd.DataFrame(columns=[
            "qlib_symbol", "ts_code", "stock_name", "index_code",
            "l1_code", "l1_name", "in_date", "out_date", "is_new", "weight",
        ])

    df = raw.copy()

    if source == "tushare":
        df = df.rename(columns={
            "ts_code": "ts_code",
            "name": "stock_name",
            "l1_code": "l1_code",
            "l1_name": "l1_name",
            "in_date": "in_date",
            "out_date": "out_date",
            "is_new": "is_new",
        })
        # 申万接口的 l1_code 本身就是一级行业代码，取不到就用请求时的 index_code
        if "l1_code" not in df.columns:
            df["l1_code"] = df["index_code"]
        if "l1_name" not in df.columns:
            df["l1_name"] = None
        df["weight"] = None
    else:
        df = df.rename(columns={
            "stockcode": "ts_code",
            "stockname": "stock_name",
            "newweight": "weight",
            "beginningdate": "in_date",
        })
        df["ts_code"] = df["ts_code"].astype(str).str.extract(r"(\d{6})", expand=False)
        df["l1_code"] = df["index_code"]
        df["l1_name"] = None
        df["out_date"] = None
        df["is_new"] = "Y"

    df["ts_code"] = df["ts_code"].astype(str).str.strip()
    df = df[df["ts_code"].str.len() == 6]
    df["qlib_symbol"] = df["ts_code"].map(bare_code_to_qlib)
    df["ts_code"] = df["qlib_symbol"].map(lambda s: f"{s[2:]}.{s[:2]}")

    for c in ("in_date", "out_date"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce")

    keep = ["qlib_symbol", "ts_code", "stock_name", "index_code",
            "l1_code", "l1_name", "in_date", "out_date", "is_new", "weight"]
    for c in keep:
        if c not in df.columns:
            df[c] = None
    return df[keep]


def build_latest_map(members: pd.DataFrame, industries: pd.DataFrame) -> pd.DataFrame:
    """最新成分 → qlib_symbol → 一级行业的映射。

    图片原版是「取第一行匹配」，同一只股票可能在多个行业出现
    （申万调整成分的历史记录里 in_date/out_date 会有多段）。
    这里按「最新纳入日」取一条，保证一只股票只有一个行业。
    """
    if members.empty:
        return pd.DataFrame(columns=["qlib_symbol", "ts_code", "l1_code",
                                     "l1_name", "index_code", "in_date"])

    df = members.copy()
    df["_rank"] = df["in_date"].fillna(pd.Timestamp("1990-01-01"))
    df = df.sort_values("_rank").drop_duplicates("qlib_symbol", keep="last")
    df = df.drop(columns="_rank")

    name_map = dict(zip(industries["index_code"], industries["industry_name"]))
    df["l1_name"] = df["l1_name"].fillna(df["index_code"].map(name_map))
    df["l1_code"] = df["l1_code"].fillna(df["index_code"])
    return df[["qlib_symbol", "ts_code", "l1_code", "l1_name", "index_code", "in_date"]]


# ------------------------------------------------------------------ main


def main() -> int:
    ap = argparse.ArgumentParser(description="获取申万一级行业成分股")
    ap.add_argument("--source", choices=["sws", "tushare"], default="sws",
                    help="sws=申万宏源官网（免 token）；tushare=图片原版（需 token+2000积分）")
    ap.add_argument("--token", default=None, help="Tushare token（默认读环境变量 TUSHARE_TOKEN）")
    ap.add_argument("--is-new", choices=["Y", "N"], default="Y",
                    help="tushare 源：Y=只要最新成分（默认）；N=含已剔除的历史成分")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"== 申万一级行业成分股 | 源={args.source} ==")
    t0 = time.time()

    if args.source == "tushare":
        pro = make_pro(args.token)
        industries = fetch_industries_tushare(pro)
        print(f"行业表: {len(industries)} 个")
        codes = industries["index_code"].tolist()
        raw = fetch_members_tushare(pro, codes, is_new=args.is_new)
    else:
        industries = fetch_industries_sws()
        print(f"行业表: {len(industries)} 个")
        codes = industries["index_code"].tolist()
        raw = fetch_members_sws(codes)

    members = normalize_members(raw, args.source)
    latest = build_latest_map(members, industries)

    industries.to_parquet(out_dir / "industries.parquet", index=False)
    members.to_parquet(out_dir / "members.parquet", index=False)
    latest.to_parquet(out_dir / "map.parquet", index=False)

    print(f"\n产出 {out_dir}")
    print(f"  industries.parquet : {len(industries):>6} 行")
    print(f"  members.parquet    : {len(members):>6} 行 ({members['qlib_symbol'].nunique()} 只)")
    print(f"  map.parquet        : {len(latest):>6} 行")
    print(f"耗时 {time.time() - t0:.1f}s")

    if not latest.empty:
        print("\n行业分布（前 8）:")
        print(latest["l1_name"].value_counts().head(8).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
