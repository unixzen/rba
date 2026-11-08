#!/usr/bin/env python3
"""Scrape RBA VK wall metadata -> data/posts.json (incremental: stops when no new posts).
Cookies/temp files: /tmp. Cache of raw pages: pages/ (gitignored)."""
import re, html, json, time, subprocess, os, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "posts.json")
CACHE = os.path.join(ROOT, "pages", "wall")
os.makedirs(CACHE, exist_ok=True)

BASE = "https://vk.com/wall-165244874?own=1"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
COOK = "/tmp/rba_vk_cookies.txt"
STOP_BEFORE = datetime.datetime(2024, 8, 1).timestamp()
STEP = 26


def fetch(url, out):
    for attempt in range(5):
        r = subprocess.run(
            ["curl", "-s", "--max-time", "40", "-b", COOK, "-c", COOK, "-A", UA,
             "-H", "Accept-Language: ru-RU,ru;q=0.9", "-H", f"Referer: {BASE}",
             url, "-o", out, "-w", "%{http_code} %{size_download}"],
            capture_output=True, text=True)
        try:
            code, size = r.stdout.split()
        except ValueError:
            code, size = "0", "0"
        if code == "200" and int(size) > 100000:
            return True
        time.sleep(4 + attempt * 4)
    print("FAIL", url, r.stdout, file=sys.stderr)
    return False


def parse_wall(path):
    d = html.unescape(open(path, encoding="utf-8", errors="ignore").read())
    posts = {}
    for m in re.finditer(r'"badges":\{"type":11,"id":(\d+),"owner_id":-165244874\}', d):
        pid = int(m.group(1))
        seg = d[m.start():m.start() + 2500]
        back = d[max(0, m.start() - 2500):m.start()]
        ds = re.findall(r'"date":(\d{10})', back)
        ts = int(ds[-1]) if ds else 0
        tm = re.search(r'"text":"((?:[^"\\]|\\.)*)"', seg)
        txt = ""
        if tm:
            try:
                txt = json.loads('"' + tm.group(1) + '"')
            except Exception:
                txt = tm.group(1)
        posts[pid] = {"id": pid, "date": ts, "text": html.unescape(txt)}
    return posts


all_posts = {}
if os.path.exists(OUT):
    all_posts = {p["id"]: p for p in json.load(open(OUT))}
print(f"known posts: {len(all_posts)}", flush=True)

offset = 0
while True:
    tmp = f"{CACHE}/{offset}.html"
    if not fetch(f"{BASE}&offset={offset}", tmp):
        break
    posts = parse_wall(tmp)
    new = {k: v for k, v in posts.items() if k not in all_posts}
    all_posts.update(posts)
    dates = [v["date"] for v in posts.values() if v["date"]]
    mind = min(dates) if dates else 0
    print(f"offset={offset}: {len(posts)} posts ({len(new)} new), min date "
          f"{datetime.datetime.utcfromtimestamp(mind).strftime('%d.%m.%Y') if mind else '?'}",
          flush=True)
    if mind and mind < STOP_BEFORE:
        break
    if not new:
        break
    offset += STEP
    time.sleep(2.0)

items = sorted(all_posts.values(), key=lambda p: p["id"])
json.dump(items, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"TOTAL {len(items)} posts -> {OUT}")
