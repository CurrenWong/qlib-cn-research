# -*- coding: utf-8 -*-
"""派生指标 / 股价 / 汇总（qlib 部分必须在 __main__ 内，Windows 下会 fork）。

跑法：把 data_prep_head.py 的内容 + 本文件拼成 data_prep.py 后执行。
本文件单独也能跑：`python data_prep_tail.py`（自己做 qlib 初始化）。
"""
import json

import qlib
from qlib.data import D

import os as _os
from pathlib import Path as _Path

# 仓库根目录：优先环境变量 QLIB_ROOT，否则按本文件位置往上推
_ROOT = _os.environ.get("QLIB_ROOT") or str(_Path(__file__).resolve().parents[2])

OUT = _ROOT + r"/projects/q3_2026/data.json"
Y = 1e8


def yi(x):
    return round(x / Y, 2)


def derive(d):
    pl = d["pl"]
    d["gm"] = tuple(round((r - c) / r * 100, 2) for r, c in zip(pl["rev"], pl["cost"]))
    d["rd_ratio"] = tuple(round(x / r * 100, 2) for x, r in zip(pl["rd"], pl["rev"]))
    d["sell_ratio"] = tuple(round(x / r * 100, 2) for x, r in zip(pl["sell"], pl["rev"]))
    d["delta"] = {k: round(v[0] - v[1], 2) for k, v in pl.items()}
    return d


def fetch_prices():
    qlib.init(provider_uri=_ROOT + r"/qlib_data/cn_data_2026", region="cn")
    df = D.features(["SZ002230", "SH600418", "SH000300"], ["$close", "$factor"],
                    start_time="2026-09-15", end_time="2026-10-30", freq="day")
    df.index.names = ["instrument", "datetime"]
    series, px = {}, {}
    for code in ("SZ002230", "SH600418", "SH000300"):
        s = df.loc[code]
        real = s["$close"] / s["$factor"]
        series[code] = [[d.strftime("%Y-%m-%d"), round(float(v), 2)] for d, v in real.items()]
        px[code] = {"last": round(float(real.iloc[-1]), 2),
                    "chg_since_0915": round(float(real.iloc[-1] / real.iloc[0] - 1) * 100, 2),
                    "high_2026": round(float(real.max()), 2)}
    for c in series:
        w = [x for x in series[c] if x[0] >= "2026-10-19"]
        px[c]["chg_since_1019"] = round((w[-1][1] / w[0][1] - 1) * 100, 2)
    return series, px


def main(IFLY, JAC):
    IFLY, JAC = derive(IFLY), derive(JAC)
    IFLY["nonop_sum"] = tuple(
        round(sum(v[i] for v in (IFLY["pl"]["other_inc"], IFLY["pl"]["inv_inc"],
                                 IFLY["pl"]["fv_gain"])) / Y, 2) for i in (0, 1))
    series, px = fetch_prices()

    IFLY["mcap"] = round(IFLY["shares"] * px["SZ002230"]["last"] / Y, 1)
    JAC["mcap"] = round(JAC["shares"] * px["SH600418"]["last"] / Y, 1)
    IFLY["pb"] = round(IFLY["mcap"] / yi(IFLY["9m"]["equity"]), 2)
    JAC["pb"] = round(JAC["mcap"] / yi(JAC["9m"]["equity"]), 2)
    IFLY["pe_9m_annualized"] = round(IFLY["mcap"] / (yi(IFLY["9m"]["np"]) * 4 / 3), 0)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"iflytek": IFLY, "jac": JAC, "price": px, "series": series,
                   "date_range": ["2026-09-15", "2026-10-30"]}, f,
                  ensure_ascii=False, indent=1)

    for d in (IFLY, JAC):
        print("=" * 70)
        print(f"{d['name']} {d['code']}  市值 {d['mcap']} 亿  PB {d['pb']}")
        print(f"  9M 营收 {yi(d['9m']['rev'])}亿  归母 {yi(d['9m']['np'])}亿  "
              f"扣非 {yi(d['9m']['np_adj'])}亿  OCF {yi(d['9m']['ocf'])}亿")
        print(f"  毛利率 {d['gm'][0]}% / {d['gm'][1]}%   研发/营收 {d['rd_ratio'][0]}% / "
              f"{d['rd_ratio'][1]}%   销售/营收 {d['sell_ratio'][0]}% / {d['sell_ratio'][1]}%")
        print(f"  研发增量 {yi(d['delta']['rd'])}亿  OCF 变动 "
              f"{yi(d['cf']['ocf'][0] - d['cf']['ocf'][1])}亿")
    print(f"\n讯飞非经营收益合计 {IFLY['nonop_sum']} 亿"
          f"  增量 {round(IFLY['nonop_sum'][0] - IFLY['nonop_sum'][1], 2)} 亿")
    print(f"讯飞 9M 年化 PE = {IFLY['pe_9m_annualized']}")
    print("股价:", json.dumps(px, ensure_ascii=False, indent=1))
    print(f"已写 {OUT}")
    return IFLY, JAC
