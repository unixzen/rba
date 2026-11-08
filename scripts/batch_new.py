#!/usr/bin/env python3
"""Create transcription batches for images not yet transcribed -> data/batches/nXX.json"""
import json, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
man = json.load(open(os.path.join(ROOT, "data", "manifest.json")))

done = set()
for f in glob.glob(os.path.join(ROOT, "data", "out", "*.txt")):
    for m in re.findall(r"file:\s*(\S+)", open(f, encoding="utf-8").read()):
        done.add(m)

todo = [m for m in man
        if m["file"] not in done
        and os.path.exists(os.path.join(ROOT, "img", m["file"]))
        and os.path.getsize(os.path.join(ROOT, "img", m["file"])) > 10000]
todo.sort(key=lambda m: (m["date"], m["file"]))
print("to transcribe:", len(todo))

B = os.path.join(ROOT, "data", "batches")
os.makedirs(B, exist_ok=True)
for f in glob.glob(os.path.join(B, "n*.json")):
    os.remove(f)
batches = [todo[i:i + 14] for i in range(0, len(todo), 14)]
for i, b in enumerate(batches):
    json.dump(b, open(os.path.join(B, f"n{i:02d}.json"), "w"), ensure_ascii=False, indent=1)
print("batches:", len(batches), [len(b) for b in batches])
