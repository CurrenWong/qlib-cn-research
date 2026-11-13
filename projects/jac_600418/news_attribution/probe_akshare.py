"""接口探针：逐个试 akshare 的新闻/公告/行情接口，每个独立子进程 + 超时强杀。

用法：..\\..\\..\\.venv\\Scripts\\python.exe probe_akshare.py
输出：probe_result.json（并打印摘要）
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE / "_probe_worker.py"

PROBES = [
    ("em_stock_news", "ak.stock_news_em(600418)  东财个股新闻"),
    ("em_global", "ak.stock_info_global_em()  东财全球快讯"),
    ("sina_global", "ak.stock_info_global_sina()  新浪7x24"),
    ("ths_global", "ak.stock_info_global_ths()  同花顺快讯"),
    ("cls_telegraph", "ak.stock_telegraph_cls(全部)  财联社电报"),
    ("cninfo_disclosure", "ak.stock_zh_a_disclosure_report_cninfo(600418)  巨潮公告"),
    ("sina_daily", "ak.stock_zh_a_daily(sh600418,qfq)  新浪日线"),
    ("em_daily", "ak.stock_zh_a_hist(600418)  东财日线"),
]

TIMEOUT = 100


def probe(name):
    try:
        p = subprocess.run(
            [sys.executable, "-u", str(WORKER), name],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "probe": name, "err": f"TIMEOUT >{TIMEOUT}s"}
    out = p.stdout or ""
    if "@@JSON@@" in out:
        j = out.split("@@JSON@@", 1)[1].strip()
        try:
            return json.loads(j)
        except json.JSONDecodeError:
            return {"ok": False, "probe": name, "err": "JSON parse fail: " + j[:200]}
    tail = (p.stderr or out)[-300:].replace("\n", " ")
    return {"ok": False, "probe": name, "err": f"no marker: {tail}"}


def main():
    results = []
    for name, desc in PROBES:
        r = probe(name)
        r["desc"] = desc
        results.append(r)
        if r.get("ok"):
            print(f"[OK  ] {name:18s} rows={r.get('rows'):>5}  cols={r.get('cols')}")
            for h in r.get("head", [])[:1]:
                for k, v in h.items():
                    print(f"         {k}: {v[:110]}")
        else:
            print(f"[FAIL] {name:18s} {r.get('err')}")
        print()

    (HERE / "probe_result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = [r["probe"] for r in results if r.get("ok")]
    print(f"可用接口 {len(ok)}/{len(PROBES)}: {ok}")
    print("结果已写入 probe_result.json")


if __name__ == "__main__":
    main()
