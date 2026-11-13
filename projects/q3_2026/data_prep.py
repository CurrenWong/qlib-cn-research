# -*- coding: utf-8 -*-
"""把两家三季报的关键数字算成 data.json，供画图与自检共用。

所有原始数字都来自 pdf/*.txt（由 PDF 抽取，不可手改）。
派生指标（毛利率、占比、增量）在这里算，并在 note 里写明口径。
"""
import json

import qlib
from qlib.data import D

OUT = r"D:\Project\qlib\projects\q3_2026\data.json"
Y = 1e8  # 亿


def yi(x):
    return round(x / Y, 2)


# ---------------- 科大讯飞 002230 ----------------
IFLY = {
    "name": "科大讯飞", "code": "002230",
    "q3": {  # 本报告期（单季）
        "rev": 6_564_463_508.59, "rev_yoy": 7.99,
        "np": 225_728_040.54, "np_yoy": 31.05,
        "np_adj": -126_131_419.94, "np_adj_yoy": -580.70,
    },
    "9m": {
        "rev": 18_187_236_503.46, "rev_yoy": 7.05,
        "np": 21_887_211.44, "np_yoy": 132.83,
        "np_adj": -762_999_219.37, "np_adj_yoy": -125.79, "np_adj_prev": -337_930_808.45,
        "ocf": 264_088_015.65, "ocf_yoy": 115.28,
        "eps": 0.0093, "roe": 0.10,
        "assets": 53_951_235_122.73, "equity": 22_819_501_229.76,
    },
    # 利润表（9M 本期 / 上期）
    "pl": {
        "rev": (18_187_236_503.46, 16_989_434_774.08),
        "cost": (10_942_883_891.28, 10_145_644_011.13),
        "sell": (3_608_019_140.07, 3_226_635_803.45),
        "admin": (958_698_109.96, 910_135_287.13),
        "rd": (3_850_369_331.35, 3_187_878_581.84),
        "fin": (168_640_833.64, 121_722_795.00),
        "other_inc": (960_812_317.93, 793_856_332.94),
        "inv_inc": (207_954_051.15, 22_698_245.99),
        "fv_gain": (257_878_623.21, 3_938_936.87),
        "credit_imp": (-248_513_970.52, -347_171_765.38),
        "asset_imp": (55_616_154.45, 1_859_448.64),
        "op_profit": (-215_822_262.24, -228_700_345.15),
        "non_op_net": (324_312.83, -13_257_738.79),
        "total_profit": (-215_497_949.41, -241_958_083.94),
        "tax": (-192_650_247.95, -158_564_151.90),
        "net": (-22_847_701.46, -83_393_932.04),
        "minority": (-44_734_912.90, -16_718_505.75),
        "np": (21_887_211.44, -66_675_426.29),
    },
    # 非经常性损益（9M）
    "nonrec": {"asset_disp": 84_192_675.99, "gov_grant": 470_983_486.49,
               "fv": 369_856_136.37, "other": 3_854_551.62,
               "tax": -138_492_983.19, "minority": -5_507_436.47,
               "total": 784_886_430.81},
    "bs": {"cash": (4_498_221_373.70, 2_451_175_870.25),
           "ar": (17_801_989_775.59, 16_295_940_653.57),
           "inv": (4_791_213_849.31, 3_031_003_519.83),
           "contract_liab": (2_578_937_464.61, 1_665_686_892.10),
           "st_loan": (1_892_479_282.50, 1_161_359_197.75),
           "lt_loan": (4_061_934_051.02, 2_716_235_614.99),
           "deferred_tax_asset": (2_430_079_360.70, 2_260_124_921.29)},
    "cf": {"ocf": (264_088_015.65, 122_671_557.01),
           "capex": (3_477_820_819.71, 2_123_410_343.10),
           "raise_invest": (4_113_670_529.53, 417_051_293.00),
           "borrow_in": (12_755_863_015.96, 4_705_860_853.67)},
    "shares": 2_402_079_841, "place_price": 44.33, "place_size": 3_999_999_986.84,
    "place_shares": 90_232_348, "holders": 464_095,
}

# ---------------- 江淮汽车 600418 ----------------
JAC = {
    "name": "江淮汽车", "code": "600418",
    "q3": {"rev": 12_241_522_545.15, "rev_yoy": 6.33,
           "np": -391_793_515.11, "np_adj": -475_289_534.78,
           "roe": -3.20, "roe_prev": -6.45},
    "9m": {"rev": 34_371_550_535.26, "rev_yoy": 11.33,
           "np": -1_140_720_258.05, "np_prev": -1_434_211_488.72,
           "np_adj": -1_466_164_549.30, "np_adj_prev": -1_763_088_717.18,
           "ocf": -4_877_612_350.61, "ocf_prev": -2_448_273_737.52,
           "eps": -0.51, "eps_prev": -0.66, "roe": -9.63, "roe_prev": -13.47,
           "assets": 50_975_215_840.75, "equity": 11_984_325_421.24},
    "pl": {
        "rev": (34_371_550_535.26, 30_872_942_134.24),
        "cost": (30_200_264_109.50, 27_529_752_450.06),
        "sell": (2_175_035_587.17, 1_610_199_269.60),
        "admin": (1_339_516_544.79, 1_786_193_183.37),
        "rd": (1_316_860_821.03, 1_202_365_319.73),
        "fin": (270_220_143.50, -151_517_791.72),
        "other_inc": (308_921_999.33, 389_666_159.35),
        "inv_inc": (-79_496_581.24, -243_037_065.37),
        "op_profit": (-1_099_863_486.67, -1_457_974_547.21),
        "total_profit": (-1_080_963_479.59, -1_460_562_397.22),
        "net": (-1_144_472_902.96, -1_526_612_152.86),
        "np": (-1_140_720_258.05, -1_434_211_488.72),
    },
    "nonrec_total": 325_444_291.25,
    "bs": {"cash": (12_704_383_932.67, 17_140_010_938.17),
           "inv": (4_100_078_697.49, 3_013_237_671.15),
           "notes_pay": (11_790_378_223.98, 14_258_827_893.92),
           "st_loan": (335_185_000.00, 170_697_814.63),
           "lt_loan": (3_829_170_959.62, 2_373_000_000.00),
           "retained": (-1_867_473_367.96, -726_753_109.91)},
    "cf": {"sales_cash": (30_220_355_871.51, 24_690_432_279.35),
           "buy_goods": (32_191_797_709.54, 24_462_194_076.20),
           "ocf": (-4_877_612_350.61, -2_448_273_737.52),
           "capex": (2_147_777_182.18, 1_032_901_656.18),
           "raise_invest": (3_479_984_117.39, 0.0),
           "borrow_in": (3_387_053_021.82, 2_193_711_895.34)},
    "shares": 2_254_178_195, "place_price": 49.88, "place_size": 3_499_999_991.52,
    "place_shares": 70_168_404, "holders": 243_007,
}




# -*- coding: utf-8 -*-
"""派生指标 / 股价 / 汇总（qlib 部分必须在 __main__ 内，Windows 下会 fork）。

跑法：把 data_prep_head.py 的内容 + 本文件拼成 data_prep.py 后执行。
本文件单独也能跑：`python data_prep_tail.py`（自己做 qlib 初始化）。
"""
import json

import qlib
from qlib.data import D

OUT = r"D:\Project\qlib\projects\q3_2026\data.json"
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
    qlib.init(provider_uri=r"D:\Project\qlib\qlib_data\cn_data_2026", region="cn")
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


if __name__ == '__main__':
    main(IFLY, JAC)

