#!/usr/bin/env python3
"""Aggregate transcriptions (out/b*.txt) -> games.json + standings + markdown report.
Includes name normalization and RBA Kids vs adult RBA split."""
import re, json, os, glob, datetime
from collections import defaultdict

import os
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
games = {}
tables_raw = []
photos = []

def parse_score(s):
    m = re.match(r"(\d+)\s*:\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else None

for f in sorted(glob.glob(f"{BASE}/out/*.txt")):
    txt = open(f, encoding="utf-8").read()
    blocks = re.split(r"\n(?=file: )", txt)
    for b in blocks:
        mfile = re.search(r"file:\s*(\S+)", b)
        mtype = re.search(r"type:\s*(\w+)", b)
        if not mfile or not mtype:
            continue
        fn, typ = mfile.group(1), mtype.group(1)
        if typ == "match_card":
            d = {}
            for part in re.findall(r"(date|time|venue|home|away|score|kind):\s*([^|\n]+)", b):
                d[part[0]] = part[1].strip()
            if not d.get("home") or not d.get("away"):
                continue
            key = (d.get("date",""), d["home"].lower(), d["away"].lower())
            rec = {"file": fn, "date": d.get("date",""), "time": d.get("time",""),
                   "venue": d.get("venue",""), "home": d["home"], "away": d["away"],
                   "score": d.get("score",""), "kind": d.get("kind","")}
            if key not in games:
                games[key] = rec
            else:
                if not parse_score(games[key]["score"]) and parse_score(rec["score"]):
                    games[key] = rec
        elif typ == "table":
            tables_raw.append({"file": fn, "text": b.strip()})
        else:
            photos.append({"file": fn, "note": b.strip()[:200]})

# ---------- normalization ----------
NBA = ["CHICAGO BULLS","GOLDEN STATE","SAN ANTONIO SPURS","MEMPHIS GRIZZLIES","OKLAHOMA CITY",
       "LOS ANGELES LAKERS","MINNESOTA TIMBERWOLVES","PORTLAND TRAIL","SACRAMENTO KINGS",
       "PHOENIX SUNS","BOSTON CELTICS","BROOKLYN NETS","DALLAS MAVERICKS","MIAMI HEAT",
       "SEATTLE SUPERSONICS","DETROIT PISTONS","HOUSTON ROCKETS","NEW YORK KNICKS",
       "PHILADELPHIA","ATLANTA HAWKS","CLEVELAND CAVALIERS","INDIANA PACERS","MILWAUKEE",
       "TORONTO RAPTORS","WASHINGTON WIZARDS","DENVER NUGGETS","UTAH JAZZ","NEW ORLEANS",
       "LA CLIPPERS","ORLANDO MAGIC","CHARLOTTE HORNETS"]

def is_nba(name):
    u = name.upper()
    tokens = ["BULLS","WARRIORS","SPURS","GRIZZLIES","THUNDER","LAKERS","TIMBERWOLVES",
              "TRAIL","SUNS","CELTICS","NETS","MAVERICKS","HEAT","SUPERSONICS","KINGS",
              "SACRAMENTO","MEMPHIS","CHICAGO","BOSTON","PHOENIX","DALLAS","MIAMI",
              "SEATTLE","MINNESOTA","PORTLAND","OKLAHOMA","GOLDEN STATE","SAN ANTONIO",
              "BROOKLYN","LOS ANGELES","NEW YORK","HOUSTON","DETROIT","PHILADELPHIA",
              "ATLANTA","CLEVELAND","INDIANA","MILWAUKEE","TORONTO","WASHINGTON","DENVER",
              "UTAH","NEW ORLEANS","ORLANDO","CHARLOTTE","CLIPPERS"]
    return any(t in u for t in tokens)

# teams without year in name -> their age group (from league matrices / opponents)
TEAM_YEAR = {"wild cats":"2012", "ростовчанки":"2012", "basket belles":"2012",
             "белые афалины":"2014", "константиновск":"2014", "урожай":"2014",
             "сшор № 5":"2014", "волгодонск":"2014", "университет":"2012"}

def is_unknown_logo(name):
    return name.startswith("(")

def norm(name):
    n = name.lower().replace("ё", "е").strip()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"\s*№\s*", " № ", n)
    n = re.sub(r"\s+", " ", n)
    # strip trailing year tag (handled by group scoping instead)
    n = re.sub(r"\s*20\d\d\s*$", "", n)
    # unify known club aliases
    n = n.replace("i.s.b.a.", "исба").replace("i.s.b.", "исба").replace("i.s. basketball academy", "исба")
    n = n.replace("i.s. basketball", "исба").replace("i.s. academy", "исба")
    n = n.replace("гбу ро сшор № 5", "сшор № 5").replace("сшор № 5", "сшор № 5")
    n = n.replace("бк импульс", "импульс").replace("бк и м п у л ь с", "импульс")
    n = n.replace("бузена", "буэна")
    n = re.sub(r"^дюсш[- ]?7$", "дюсш № 7", n)
    n = re.sub(r"^бк\s+", "", n)
    n = n.strip()
    return n

DISPLAY = {}
def display(name, grp=""):
    k = (grp, norm(name))
    k2 = norm(name)
    if k not in DISPLAY:
        # prefer the variant that contains a year tag
        if re.search(r"20\d\d", name) or k2 not in DISPLAY:
            DISPLAY[k] = re.sub(r"\s+", " ", name).strip()
        else:
            DISPLAY[k] = DISPLAY[k2]
        if k2 not in DISPLAY:
            DISPLAY[k2] = DISPLAY[k]
    return DISPLAY[k]

def parse_date(s):
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", s or "")
    return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None

def parse_score(s):
    m = re.match(r"(\d+)\s*:\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else None

def year_of(team):
    m = re.search(r"(20\d\d)", team)
    return m.group(1) if m else None

def game_group(g):
    ys = [y for y in (year_of(g["home"]), year_of(g["away"])) if y]
    if ys:
        return ys[0]
    for t in (g["home"], g["away"]):
        k = norm(t)
        if k in TEAM_YEAR:
            return TEAM_YEAR[k]
    return "—"

def season_of(d):
    if not d: return "?"
    if d <= datetime.date(2025, 6, 30): return "2024/2025"
    if d <= datetime.date(2026, 6, 30): return "2025/2026"
    return "2026/2027"

game_list = sorted(games.values(), key=lambda g: (parse_date(g["date"]) or datetime.date(2000,1,1), g["time"]))

def bucket(g):
    if is_nba(g["home"]) or is_nba(g["away"]):
        return "adult"
    if is_unknown_logo(g["home"]) or is_unknown_logo(g["away"]):
        return "unknown"
    return "kids"

standings = defaultdict(lambda: defaultdict(lambda: {"И":0,"В":0,"П":0,"З":0,"П2":0}))
results_count = 0
adult_games = []
unknown_games = []
kids_results = []

for g in game_list:
    bkt = bucket(g)
    if bkt == "adult":
        adult_games.append(g); continue
    if bkt == "unknown":
        unknown_games.append(g); continue
    if "result" not in (g["kind"] or ""):
        continue
    sc = parse_score(g["score"])
    if not sc:
        continue
    results_count += 1
    kids_results.append(g)
    d = parse_date(g["date"])
    grp = game_group(g)
    seas = season_of(d)
    t = standings[(seas, grp)]
    hs, as_ = sc
    for team, gf, ga in ((g["home"], hs, as_), (g["away"], as_, hs)):
        k = norm(team)
        r = t[k]
        if "_name" not in r or (str(grp) in team and str(grp) not in r["_name"]):
            r["_name"] = re.sub(r"\s+", " ", team).strip()
        r["И"] += 1; r["З"] += gf; r["П2"] += ga
        if gf > ga: r["В"] += 1
        else: r["П"] += 1

# ---------- report ----------
out = []
out.append("# RBA Kids — результаты игр и турнирные таблицы\n")
out.append("Источник: VK-сообщество «Rostov Basketball Association | RBA» (vk.com/rba_rostov_basketball)\n")
out.append(f"Распознано карточек матчей RBA Kids: {len(game_list) - len(adult_games) - len(unknown_games)} (результатов со счётом: {results_count}).\n")
out.append(f"Отдельно: матчей взрослой лиги RBA (отфильтровано): {len(adult_games)}, прочих/неопознанных: {len(unknown_games)}.\n")

for seas in ["2024/2025", "2025/2026", "2026/2027"]:
    out.append(f"\n## СЕЗОН {seas}\n")
    out.append("\n### Результаты игр\n")
    cur_date = None
    for g in kids_results + [x for x in game_list if bucket(x)=="kids" and "result" not in (x["kind"] or "")]:
        d = parse_date(g["date"])
        if season_of(d) != seas: continue
        if g["date"] != cur_date:
            cur_date = g["date"]
            out.append(f"\n**{g['date']}**\n")
        h, a = display(g["home"]), display(g["away"])
        if "result" in (g["kind"] or "") and g["score"]:
            out.append(f"- {h} — {a} — **{g['score']}** ({g['time']}, {g['venue']})")
        else:
            out.append(f"- {h} — {a} — анонс/без счёта ({g['time']}, {g['venue']})")

    out.append("\n### Турнирные таблицы (рассчитано по результатам; 2 очка за победу)\n")
    for (s2, grp), teams in sorted(standings.items()):
        if s2 != seas: continue
        out.append(f"\n**Возрастная группа {grp}**\n")
        out.append("| # | Команда | И | В | П | Забито | Пропущено | Разница | Очки |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        rows = sorted(teams.items(), key=lambda kv: (-(kv[1]["В"]*2+kv[1]["П"]), -(kv[1]["З"]-kv[1]["П2"])))
        for i, (team, r) in enumerate(rows, 1):
            out.append(f"| {i} | {r.get('_name', display(team, grp))} | {r['И']} | {r['В']} | {r['П']} | {r['З']} | {r['П2']} | {r['З']-r['П2']:+d} | {r['В']*2+r['П']} |")

out.append("\n## Официальные итоги/таблицы из постов (транскрипция картинок)\n")
for t in tables_raw:
    out.append(f"\n### {t['file']}\n")
    out.append(t["text"])

out.append("\n## Матчи взрослой лиги RBA (не входят в RBA Kids)\n")
for g in adult_games:
    out.append(f"- {g['date']} {g['home']} — {g['away']} {g['score']} ({g['kind']})")

open(f"{BASE}/report.md", "w", encoding="utf-8").write("\n".join(out))
json.dump(game_list, open(f"{BASE}/games.json","w"), ensure_ascii=False, indent=1)
print("kids cards:", len(game_list)-len(adult_games)-len(unknown_games), "kids results:", results_count,
      "adult:", len(adult_games), "unknown:", len(unknown_games), "tables:", len(tables_raw))
