#!/usr/bin/env python3
"""Download attachment images from data/images.json -> img/ + data/manifest.json.
Skips images already on disk (incremental)."""
import json, os, re, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "img")
os.makedirs(IMG, exist_ok=True)

data = json.load(open(os.path.join(ROOT, "data", "images.json")))
manifest = []
for pid, info in sorted(data.items(), key=lambda kv: kv[1]["date"]):
    for i, u in enumerate(info["images"]):
        ext = ".png" if u.split("?")[0].endswith(".png") else ".jpg"
        fn = f"p{pid}_{i}{ext}"
        path = os.path.join(IMG, fn)
        if not os.path.exists(path) or os.path.getsize(path) < 5000:
            r = subprocess.run(
                ["curl", "-sL", "--max-time", "60",
                 "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121",
                 u, "-o", path, "-w", "%{http_code} %{size_download}"],
                capture_output=True, text=True)
            try:
                code, size = r.stdout.split()
            except ValueError:
                code, size = "0", "0"
            if code != "200" or int(size) < 5000:
                print("FAIL", pid, i, r.stdout, u[:80], flush=True)
                if os.path.exists(path):
                    os.remove(path)
                continue
            time.sleep(0.4)
        manifest.append({"post": int(pid), "date": info["date"], "text": info["text"],
                         "file": fn, "url": u})

json.dump(manifest, open(os.path.join(ROOT, "data", "manifest.json"), "w"),
          ensure_ascii=False, indent=1)
print("TOTAL FILES", len(manifest))
