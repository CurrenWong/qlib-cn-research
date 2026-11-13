import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.64; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Referer": "https://gu.qq.com/"}
q = "sz300394,sh600795,sh601229"
r = requests.get(f"https://qt.gtimg.cn/q={q}", headers=UA, timeout=30)
print("status", r.status_code, "len", len(r.text))
txt = r.content.decode("gbk", errors="ignore")
print("txt head:", repr(txt[:200]))
for line in txt.split(";"):
    line = line.strip()
    if not line.startswith("v_"):
        print("SKIP:", repr(line[:60]))
        continue
    body = line.split("=", 1)[1].strip('"')
    f = body.split("~")
    print("name", f[1], "code", f[2], "nfields", len(f),
          "now", f[3], "prevclose", f[4], "open", f[5])
