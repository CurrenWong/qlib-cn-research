"""新闻抓取层。

技术要点：akshare 的 `stock_news_em` 把东财搜索接口的分页写死成 pageIndex=1/pageSize=10，
且它自带的 cookie 缺一不可（自己拼请求会返回空）。
所以这里**复用 akshare 自己的请求头与 cookie**，只在发送前改写 pageIndex / pageSize / sort。

三个来源：
  em_news   东财个股新闻（可翻页，回溯深）        —— 主来源
  cninfo    巨潮公告（600418 正式公告，按年拉）   —— 最硬的证据
  flash     东财/同花顺/财联社快讯（仅最近若干条） —— 当日背景
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import akshare as ak

HERE = Path(__file__).resolve().parent
CACHE = HERE / "news_cache"
CACHE.mkdir(exist_ok=True)

_EM_MODULE = sys.modules[ak.stock_news_em.__module__] if False else None  # placeholder


def _em_module():
    import sys

    return sys.modules[ak.stock_news_em.__module__]


# ------------------------------------------------------------------ 东财搜索
def em_search_page(
    keyword: str = "600418",
    page_index: int = 1,
    page_size: int = 50,
    sort: str = "default",
    timeout: int = 40,
) -> list[dict]:
    """调用东财搜索接口（akshare 的头 + 改写的分页），返回原始文章列表。"""
    mod = _em_module()
    orig_get = mod.requests.get

    def patched(url, *args, **kwargs):
        params = kwargs.get("params")
        if isinstance(params, dict) and "param" in params:
            inner = json.loads(params["param"])
            node = inner["param"]["cmsArticleWebOld"]
            node["pageIndex"] = page_index
            node["pageSize"] = page_size
            node["sort"] = sort
            params = dict(params)
            params["param"] = json.dumps(inner, ensure_ascii=False)
            kwargs["params"] = params
        kwargs.setdefault("timeout", timeout)
        return orig_get(url, *args, **kwargs)

    mod.requests.get = patched
    try:
        import requests as _rq

        params = json.loads(json.dumps(_build_em_param(keyword, page_index, page_size, sort)))
        resp = orig_get(
            "https://search-api-web.eastmoney.com/search/jsonp",
            params=params,
            headers=_EM_HEADERS,
            timeout=timeout,
        )
        txt = resp.text.strip()
        if txt.startswith("jQuery"):
            txt = txt[txt.find("(") + 1 : txt.rfind(")")]
        data = json.loads(txt)
        return data.get("result", {}).get("cmsArticleWebOld") or []
    finally:
        mod.requests.get = orig_get


def _build_em_param(keyword, page_index, page_size, sort):
    """直接复用 akshare 源码里的参数结构 + 完整请求头（含 cookie）。"""
    inner = {
        "uid": "",
        "keyword": keyword,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": sort,
                "pageIndex": page_index,
                "pageSize": page_size,
                "preTag": "<em>",
                "postTag": "</em>",
            }
        },
    }
    return {
        "cb": "jQuery35101792940631092459_1764599530165",
        "param": json.dumps(inner, ensure_ascii=False),
        "_": "1764599530176",
    }


def _em_cookie() -> str:
    """东财会话 Cookie：环境变量 EM_SEARCH_COOKIE 优先，其次 ~/.em_search_cookie。

    以前是写死在这里的。会话 Cookie 属于个人凭据，不能进仓库，
    所以改成外部注入；两个来源都没有就发空 cookie（多数情况下仍能拿到结果）。
    """
    val = os.environ.get("EM_SEARCH_COOKIE", "").strip()
    if val:
        return val
    p = Path.home() / ".em_search_cookie"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


_EM_HEADERS = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en,zh-CN;q=0.9,zh;q=0.8",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "cookie": _em_cookie(),
    "host": "search-api-web.eastmoney.com",
    "pragma": "no-cache",
    "referer": "https://so.eastmoney.com/news/s?keyword=603777",
    "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "script",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    ),
}


def _clean(text: str) -> str:
    text = re.sub(r"</?em>", "", str(text))
    text = text.replace("　", " ").replace("\r\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def em_news(keyword="600418", pages=1, page_size=50, sort="default", sleep=0.6):
    """翻页抓取东财个股新闻，返回标准化记录列表。"""
    out, seen = [], set()
    for pi in range(1, pages + 1):
        try:
            rows = em_search_page(keyword, pi, page_size, sort)
        except Exception as e:  # noqa: BLE001
            print(f"  [em_news] page {pi} 失败: {type(e).__name__}: {str(e)[:90]}")
            break
        if not rows:
            print(f"  [em_news] page {pi} 空，停止")
            break
        for r in rows:
            url = "http://finance.eastmoney.com/a/" + str(r.get("code", "")) + ".html"
            if url in seen:
                continue
            seen.add(url)
            out.append(
                {
                    "date": str(r.get("date", ""))[:19],
                    "title": _clean(r.get("title", "")),
                    "content": _clean(r.get("content", "")),
                    "media": str(r.get("mediaName", "")),
                    "url": url,
                }
            )
        print(f"  [em_news] page {pi}: +{len(rows)}（累计 {len(out)}）")
    return out


# ------------------------------------------------------------------ 巨潮公告
def cninfo_announcements(code="600418", start="20010101", end="20261028"):
    df = ak.stock_zh_a_disclosure_report_cninfo(
        symbol=code, market="沪深京", keyword="", start_date=start, end_date=end
    )
    if df is None or not len(df):
        return []
    return [
        {
            "date": str(r["公告时间"])[:10],
            "title": str(r["公告标题"]),
            "url": str(r["公告链接"]),
            "media": "巨潮资讯",
        }
        for _, r in df.iterrows()
    ]


# ------------------------------------------------------------------ 快讯
def flash_news():
    """东财 + 同花顺 + 财联社 快讯（仅最近若干条，用于当日背景）。"""
    out = []
    for name, fn in [
        ("东财快讯", lambda: ak.stock_info_global_em()),
        ("同花顺快讯", lambda: ak.stock_info_global_ths()),
        ("财联社电报", lambda: ak.stock_info_global_cls()),
    ]:
        try:
            df = fn()
            if df is None or not len(df):
                print(f"  [flash] {name}: 空")
                continue
            for _, r in df.iterrows():
                t = str(r.get("发布时间") or r.get("时间") or r.get("发布日期") or "")
                title = str(r.get("标题") or "")
                content = str(r.get("摘要") or r.get("内容") or "")
                url = str(r.get("链接") or r.get("网址") or "")
                out.append(
                    {
                        "date": t[:19],
                        "title": _clean(title),
                        "content": _clean(content),
                        "media": name,
                        "url": url,
                    }
                )
            print(f"  [flash] {name}: {len(df)} 条")
        except Exception as e:  # noqa: BLE001
            print(f"  [flash] {name} 失败: {type(e).__name__}: {str(e)[:90]}")
    return out


def save(name: str, rows: list[dict]):
    p = CACHE / f"{name}.json"
    p.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  已缓存 {p.name}: {len(rows)} 条")
    return p


def load(name: str) -> list[dict]:
    p = CACHE / f"{name}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import sys

    print("== 分页深度测试（page_size=50）==")
    for pi in (1, 2, 3, 5, 10):
        rows = em_search_page("600418", pi, 50, "default")
        if rows:
            ds = [r.get("date", "")[:10] for r in rows]
            print(f"  page {pi}: {len(rows)} 条 | {ds[0]} ~ {ds[-1]} | {rows[0].get('title','')[:34]}")
        else:
            print(f"  page {pi}: 空")
