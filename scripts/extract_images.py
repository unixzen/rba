#!/usr/bin/env python3
"""Fetch VK post pages for candidate posts -> extract attachment image URLs -> data/images.json.
Skips posts already in images.json (incremental)."""
import re, html, json, time, subprocess, os, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "data", "posts.json")
OUT = os.path.join(ROOT, "data", "images.json")
PAGES = os.path.join(ROOT, "pages", "posts")
os.makedirs(PAGES, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
COOK = "/tmp/rba_vk_cookies.txt"
AVATAR_MARKERS = ("L895R0KTpcI", "ZPwPCPh81v7k", "P7OMjXl", "ava=1")


def want(p):
    t = p["text"]
    if p["date"] < datetime.datetime(2024, 8, 1).timestamp():
        return False
    if "ids" not in t.lower():          # RBA Kids / RBA KIDS
        return False
    if "#" in t:                        # photo-report posts have stripped hashtags
        return False
    if len(re.findall(r"\b\d{1,2}:\d{2}\b", t)) >= 2:   # schedule announcements
        return False
    if any(x in t.lower() for x in ("ghetto", "shop", "ozon", "wildberries")):
        return False
    return True


def fetch(url, out):
    for attempt in range(4):
        r = subprocess.run(
            ["curl", "-s", "--max-time", "40", "-b", COOK, "-c", COOK, "-A", UA,
             "-H", "Accept-Language: ru-RU,ru;q=0.9",
             "-H", "Referer: https://vk.com/wall-165244874",
             url, "-o", out, "-w", "%{http_code} %{size_download}"],
            capture_output=True, text=True)
        try:
            code, size = r.stdout.split()
        except ValueError:
            code, size = "0", "0"
        if code == "200" and int(size) > 50000:
            return True
        time.sleep(3 + attempt * 5)
    print("FAIL", url, r.stdout, file=sys.stderr)
    return False


def extract_images(path):
    d = html.unescape(open(path, encoding="utf-8", errors="ignore").read()).replace("\\/", "/")
    urls = re.findall(r'https?://(?:sun|pp|ps|cs)[\w.-]*userapi\.com[^"\'\\ )>]+', d)
    best = {}
    for u in urls:
        if any(m in u for m in AVATAR_MARKERS) or "blur=" in u or "type=album" in u:
            continue
        base = u.split("?")[0]
        if base not in best or len(u) > len(best[base]):
            best[base] = u
    return [u for b, u in best.items() if not (b.endswith(".png") and "/s/v1/" not in b)]


posts = json.load(open(POSTS))
sel = [p for p in posts if want(p)]
result = {}
if os.path.exists(OUT):
    result = json.load(open(OUT))
todo = [p for p in sel if str(p["id"]) not in result]
print(f"candidate posts: {len(sel)}, new to process: {len(todo)}", flush=True)

for i, p in enumerate(todo):
    pid = str(p["id"])
    path = f"{PAGES}/{pid}.html"
    if not os.path.exists(path) or os.path.getsize(path) < 50000:
        if not fetch(f"https://vk.com/wall-165244874_{pid}", path):
            result[pid] = {"date": p["date"], "text": p["text"], "images": [], "error": True}
            json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=1)
            continue
        time.sleep(1.5)
    imgs = extract_images(path)
    result[pid] = {"date": p["date"], "text": p["text"], "images": imgs}
    if i % 20 == 0:
        print(f"{i}/{len(todo)} pid={pid} imgs={len(imgs)}", flush=True)
        json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=1)

json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=1)
tot = sum(len(v["images"]) for v in result.values())
print(f"DONE {len(result)} posts, {tot} images -> {OUT}")
