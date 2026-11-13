"""探针 worker：跑一个 akshare 接口，输出 JSON 结果。

被 probe_akshare.py 以子进程调用（每个接口独立超时强杀，避免卡死拖垮全场）。
用法：python _probe_worker.py <probe_name>
"""

import json
import sys
import warnings

warnings.filterwarnings("ignore")


def shape(df, head=2):
    """把 DataFrame 压成可 JSON 序列化的结构摘要。"""
    if df is None:
        return {"rows": 0, "cols": [], "head": []}
    rows = []
    for _, r in df.head(head).iterrows():
        d = {}
        for k in df.columns:
            v = r[k]
            s = str(v)
            d[str(k)] = s[:180]
        rows.append(d)
    return {"rows": int(len(df)), "cols": [str(c) for c in df.columns], "head": rows}


def run(name):
    import akshare as ak

    if name == "em_stock_news":
        return shape(ak.stock_news_em(symbol="600418"))
    if name == "em_global":
        return shape(ak.stock_info_global_em())
    if name == "sina_global":
        return shape(ak.stock_info_global_sina())
    if name == "ths_global":
        return shape(ak.stock_info_global_ths())
    if name == "cls_telegraph":
        return shape(ak.stock_telegraph_cls(symbol="全部"))
    if name == "cninfo_disclosure":
        return shape(
            ak.stock_zh_a_disclosure_report_cninfo(
                symbol="600418",
                market="沪深京",
                keyword="",
                start_date="20250101",
                end_date="20261028",
            )
        )
    if name == "sina_daily":
        return shape(ak.stock_zh_a_daily(symbol="sh600418", adjust="qfq"))
    if name == "em_daily":
        return shape(
            ak.stock_zh_a_hist(
                symbol="600418",
                period="daily",
                start_date="20250101",
                end_date="20261028",
                adjust="qfq",
            )
        )
    raise ValueError(f"unknown probe: {name}")


if __name__ == "__main__":
    nm = sys.argv[1]
    try:
        out = {"ok": True, "probe": nm, **run(nm)}
    except Exception as e:  # noqa: BLE001
        out = {
            "ok": False,
            "probe": nm,
            "err": f"{type(e).__name__}: {e}"[:300],
        }
    print("@@JSON@@" + json.dumps(out, ensure_ascii=False))
