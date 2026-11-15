"""体检 Tushare token：能不能认证、有没有接口权限、能调哪些接口。

## 为什么需要单独一个脚本
Tushare SDK 把错误细节吞得很干净——`pro.daily()` 抛的异常只有一句
「抱歉，您没有接口(daily)访问权限」，而这句背后可能是三种完全不同的病：

| 现象 | 真实原因 | 该怎么办 |
|---|---|---|
| `code 40001 / token不对` | token 写错/过期 | 重新拿 token |
| `code 40203 / 没有接口访问权限` | 账号**积分不足**（daily/adj_factor 要 120 分） | 攒积分，或先用 `--source tencent` |
| 401 / 超时 | 网络或 key 失效 | 重试 / 换 key |

这个脚本把「认证」和「权限」分开测，直接告诉你卡在哪一层，不会让你对着
「重试 4 次仍失败」瞎猜。

## 用法
```cmd
cd /d <repo>
.venv\\Scripts\\python.exe tools\\check_tushare.py
.venv\\Scripts\\python.exe tools\\check_tushare.py --token <另一个token>
```
token 来源优先级：`--token` > 环境变量 `TUSHARE_TOKEN` > `%USERPROFILE%\\.tushare_token`。
脚本**不会**打印 token 全文，只显示长度与前 4 / 后 4 位。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tushare_common import resolve_token  # noqa: E402

#: (接口, 参数, 说明, 需要的积分档位)
PROBES = [
    ("trade_cal", dict(exchange="SSE", start_date="20261101", end_date="20261110"),
     "交易日历", "0 分"),
    ("stock_basic", dict(exchange="", list_status="L", fields="ts_code,name"),
     "股票列表", "0 分"),
    ("daily", dict(ts_code="600519.SH", start_date="20261101", end_date="20261110"),
     "日线行情（图片原版用的就是它）", "120 分"),
    ("adj_factor", dict(ts_code="600519.SH", start_date="20261101", end_date="20261110"),
     "复权因子", "120 分"),
    ("daily_basic", dict(ts_code="600519.SH", start_date="20261101", end_date="20261110"),
     "每日指标（市值/PE 等）", "120 分"),
    ("index_classify", dict(level="L1", src="SW2021"),
     "申万行业分类", "2000 分"),
    ("index_member_all", dict(l1_code="801010.SI"),
     "申万行业成分（含计入日）", "2000 分"),
]

CODE_HINT = {
    40001: "token 无效/写错 → 重新复制 token",
    40203: "账号没有该接口权限 → 积分不足（daily 需 120 分）",
    40202: "积分不足 / 单次请求超限",
    40101: "必填参数缺失",
}

#: SDK 常把数字 code 吞掉，只留中文，这里按措辞反推
TEXT_HINT = [
    ("没有接口", 40203),
    ("权限", 40203),
    ("积分", 40202),
    ("token", 40001),
]


def _guess_code(msg: str) -> int | None:
    for c in CODE_HINT:
        if str(c) in msg:
            return c
    for text, c in TEXT_HINT:
        if text.lower() in msg.lower():
            return c
    return None


def _is_rate_limited(msg: str) -> bool:
    return any(h in msg for h in ("频率超限", "每分钟", "每小时", "最多访问"))


def _parse_limit(msg: str) -> str:
    """从「频率超限(1次/分钟)」里抠出口径，方便决定探测间隔。"""
    import re

    m = re.search(r"超限\((.+?)\)", msg)
    return m.group(1) if m else "未知"


def auth_contrast(tok: str) -> tuple[int | None, str, int | None, str]:
    """用「真 token」和「假 token」各打一次，靠返回码 + 措辞区分「认证 / 权限 / 限频」。

    ⚠ Tushare 的 `40203` **既表示"没有接口权限"也表示"频率超限"**，只看 code 会误判
    （2026-11-13 真踩过：先报 40203 无权限，权限开通后同样的 40203 变成 1 次/分钟）。
    所以必须连 msg 一起看：

      真 40101「token不对」          → token 本身无效
      真 ...「没有接口(x)访问权限」   → 账号该接口无权限
      真 ...「频率超限(n)」          → 权限有，只是调超了
      假 40101                      → 说明对照有效（假 token 一定进不来）
    """
    import json

    import requests

    def call(t: str) -> tuple[int | None, str]:
        payload = {"api_name": "trade_cal", "token": t,
                   "params": {"exchange": "SSE", "start_date": "20261101",
                              "end_date": "20261110"},
                   "fields": ""}
        try:
            r = requests.post("http://api.tushare.pro", data=json.dumps(payload),
                              headers={"Content-Type": "application/json"}, timeout=30)
            j = r.json()
            return j.get("code"), (j.get("msg") or "").replace("\n", " ")
        except Exception as e:  # noqa: BLE001
            return None, f"{type(e).__name__}: {str(e)[:60]}"

    rc, rmsg = call(tok)
    fc, fmsg = call("0" * 56)
    return rc, rmsg, fc, fmsg


def main() -> int:
    ap = argparse.ArgumentParser(description="Tushare token 体检")
    ap.add_argument("--token", default=None, help="不传则读环境变量/用户目录文件")
    ap.add_argument("--sleep", type=float, default=1.5,
                    help="接口之间的间隔秒数；账号是「1 次/分钟」档时必须给 62")
    ap.add_argument("--apis", default="", help="只测这几个接口，逗号分隔，如 daily,adj_factor")
    args = ap.parse_args()

    try:
        tok = resolve_token(args.token)
    except RuntimeError as e:
        print(f"❌ 没找到 token：{e}")
        return 2
    print(f"== Tushare token 体检 ==")
    print(f"   token 长度 {len(tok)}｜前4位 {tok[:4]}…｜后4位 …{tok[-4:]}")

    import tushare as ts

    pro = ts.pro_api(tok)
    print(f"   客户端：tushare {ts.__version__}\n")

    ok, denied = [], []
    limited: list[str] = []
    wanted = {s.strip() for s in args.apis.split(",") if s.strip()}
    probes = [p for p in PROBES if not wanted or p[0] in wanted]
    for api, kw, desc, need in probes:
        t0 = time.time()
        try:
            df = getattr(pro, api)(**kw)
            n = 0 if df is None else len(df)
            print(f"  ✅ {api:<17}{desc:<26}{'空表' if n == 0 else f'{n} 行':>8}"
                  f"  [{need}]  {time.time()-t0:.1f}s")
            ok.append(api)
        except Exception as e:  # noqa: BLE001
            msg = str(e).replace("\n", " ")
            if _is_rate_limited(msg):
                print(f"  ⏳ {api:<17}{desc:<26}{'限频':>8}  [{need}]  "
                      f"{_parse_limit(msg)}  (权限已开，只是调太快)")
                limited.append(api)
            else:
                code = _guess_code(msg)
                hint = CODE_HINT.get(code, "见 https://tushare.pro/document/1?doc_id=108")
                print(f"  ❌ {api:<17}{desc:<26}{'拒绝':>8}  [{need}]  {msg[:70]}")
                print(f"     ↳ {hint}")
                denied.append(api)
        time.sleep(args.sleep)

    print("\n" + "=" * 70)

    # 认证 vs 权限 vs 限频：靠「假 token 对照 + 措辞」定性
    rc, rmsg, fc, fmsg = auth_contrast(tok)
    print(f"认证对照：真 token → code {rc}「{rmsg[:46]}」｜假 token → code {fc}「{fmsg[:20]}」")
    if rc == 40101:
        print("结论：❌ token 本身无效（40101）→ 复制错了 / 已过期 / 换了账号")
        return 2
    if "没有接口" in rmsg:
        print("结论：token 有效，但该账号**没有接口权限**（40203 无权限，不是限频）")
        return 1
    if _is_rate_limited(rmsg):
        print("结论：token 有效、权限已开，只是探测太快被限频"
              f"（trade_cal：{_parse_limit(rmsg)}）。")
        print("      用 --sleep 62（或 --apis daily 单测）重跑；各接口限频档位见上面每行输出。")

    if ok and not denied:
        print("结论：✅ token 可用，全部接口通过")
        if limited:
            print(f"      （另有 {limited} 只是限频，用 --sleep 62 重跑可确认）")
        return 0
    if ok:
        print(f"结论：⚠ 部分可用 —— 能用 {ok}；缺权限 {denied}"
              + (f"；限频 {limited}" if limited else ""))
        return 1
    if limited and not denied:
        print(f"结论：⚠ 全部接口都只是**限频**（{limited}），没有权限问题")
        return 1
    print("结论：❌ 一个接口都调不通，且未能定性（详见上面的原始返回）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
