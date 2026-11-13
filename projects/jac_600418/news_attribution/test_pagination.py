"""探针2：东财个股新闻搜索接口能翻多深？能按时间排序吗？

沿用 akshare 的请求配方，只改 pageIndex / pageSize / sort。
"""

import json

import requests

URL = "https://search-api-web.eastmoney.com/search/jsonp"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en,zh-CN;q=0.9,zh;q=0.8",
    "referer": "https://so.eastmoney.com/news/s?keyword=600418",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "cookie": "qgqp_b_id=652bf4c98a74e210088f372a17d4e27b; nid18=010d039dd427dc4d187090491f47d7ad",
}


def build(keyword: str, page_index: int, page_size: int, sort: str):
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


def fetch(keyword="600418", page_index=1, page_size=10, sort="default", timeout=30):
    r = requests.get(URL, params=build(keyword, page_index, page_size, sort),
                     headers=HEADERS, timeout=timeout)
    txt = r.text.strip()
    if txt.startswith("jQuery"):
        txt = txt[txt.find("(") + 1 : txt.rfind(")")]
    data = json.loads(txt)
    return data.get("result", {}).get("cmsArticleWebOld") or []


def show(tag, rows):
    if not rows:
        print(f"  {tag}: 空")
        return
    dates = [x.get("date", "") for x in rows]
    print(f"  {tag}: {len(rows)} 条 | {dates[0]} ~ {dates[-1]}")
    print(f"      首: {rows[0].get('title', '')[:46]}")
    print(f"      尾: {rows[-1].get('title', '')[:46]}")


if __name__ == "__main__":
    print("A) pageSize 生效性（sort=default, pageIndex=1）")
    for ps in (10, 50, 100):
        try:
            show(f"pageSize={ps}", fetch(page_size=ps))
        except Exception as e:  # noqa: BLE001
            print(f"  pageSize={ps}: 失败 {type(e).__name__}: {str(e)[:90]}")

    print("\nB) 翻页深度（pageSize=50）")
    for pi in (1, 2, 3, 5, 10, 20):
        try:
            show(f"pageIndex={pi}", fetch(page_index=pi, page_size=50))
        except Exception as e:  # noqa: BLE001
            print(f"  pageIndex={pi}: 失败 {type(e).__name__}: {str(e)[:90]}")

    print("\nC) 排序方式（pageSize=50, pageIndex=1）")
    for s in ("time", "date", "default", "score"):
        try:
            show(f"sort={s}", fetch(sort=s, page_size=50))
        except Exception as e:  # noqa: BLE001
            print(f"  sort={s}: 失败 {type(e).__name__}: {str(e)[:90]}")
