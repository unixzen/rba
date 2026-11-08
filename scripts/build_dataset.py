#!/usr/bin/env python3
"""Build rba_kids_dataset.json — full collected dataset for website building."""
import re, json, glob, datetime
from collections import defaultdict

import os
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# ---------------- shared normalization (same as aggregate.py) ----------------
NBA_TOKENS = ["BULLS","WARRIORS","SPURS","GRIZZLIES","THUNDER","LAKERS","TIMBERWOLVES",
              "TRAIL","SUNS","CELTICS","NETS","MAVERICKS","HEAT","SUPERSONICS","KINGS",
              "SACRAMENTO","MEMPHIS","CHICAGO","BOSTON","PHOENIX","DALLAS","MIAMI",
              "SEATTLE","MINNESOTA","PORTLAND","OKLAHOMA","GOLDEN STATE","SAN ANTONIO",
              "BROOKLYN","LOS ANGELES","NEW YORK","HOUSTON","DETROIT","PHILADELPHIA",
              "ATLANTA","CLEVELAND","INDIANA","MILWAUKEE","TORONTO","WASHINGTON","DENVER",
              "UTAH","NEW ORLEANS","ORLANDO","CHARLOTTE","CLIPPERS"]

TEAM_YEAR = {"wild cats":"2012", "ростовчанки":"2012", "basket belles":"2012",
             "белые афалины":"2014", "константиновск":"2014", "урожай":"2014",
             "сшор № 5":"2014", "волгодонск":"2014", "университет":"2012"}

ALIAS_DISPLAY = {"константиновск": "Урожай (Константиновск)"}

def is_nba(name):
    u = name.upper()
    return any(t in u for t in NBA_TOKENS)

def is_unknown_logo(name):
    return name.startswith("(")

def norm(name):
    n = name.lower().replace("ё", "е").strip()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"\s*№\s*", " № ", n)
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"\s*20\d\d\s*$", "", n)
    n = n.replace("i.s.b.a.", "исба").replace("i.s.b.", "исба").replace("i.s. basketball academy", "исба")
    n = n.replace("i.s. basketball", "исба").replace("i.s. academy", "исба")
    n = n.replace("гбу ро сшор № 5", "сшор № 5")
    n = n.replace("бк импульс", "импульс")
    n = n.replace("бузена", "буэна")
    n = re.sub(r"^дюсш[- ]?7$", "дюсш № 7", n)
    n = re.sub(r"^бк\s+", "", n)
    return n.strip()

def parse_date(s):
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", s or "")
    return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None

def parse_score(s):
    m = re.match(r"(\d+)\s*:\s*(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else None

def year_of(team):
    m = re.search(r"(20\d\d)", team)
    return m.group(1) if m else None

def season_of(d):
    if not d: return None
    if d <= datetime.date(2025, 6, 30): return "2024/2025"
    if d <= datetime.date(2026, 6, 30): return "2025/2026"
    return "2026/2027"

def game_group(g):
    ys = [y for y in (year_of(g["home"]), year_of(g["away"])) if y]
    if ys: return ys[0]
    for t in (g["home"], g["away"]):
        k = norm(t)
        if k in TEAM_YEAR: return TEAM_YEAR[k]
    return "unknown"

# ---------------- load raw games ----------------
games_raw = json.load(open(f"{BASE}/games.json"))

games, standings = [], defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"played":0,"wins":0,"losses":0,"scored":0,"conceded":0})))
team_names = {}   # (season, group, norm) -> display

def display_name(team, grp):
    k = norm(team)
    if k in ALIAS_DISPLAY and year_of(team) is None:
        return ALIAS_DISPLAY[k]
    return re.sub(r"\s+", " ", team).strip()

for g in games_raw:
    d = parse_date(g["date"])
    seas = season_of(d)
    grp = game_group(g)
    if is_nba(g["home"]) or is_nba(g["away"]):
        league = "rba_adult"
        grp = "nba"
    elif is_unknown_logo(g["home"]) or is_unknown_logo(g["away"]):
        league = "unknown"
    else:
        league = "rba_kids"
    sc = parse_score(g["score"])
    mpost = re.match(r"p(\d+)_", g.get("file") or "")
    rec = {
        "date": g["date"],
        "iso_date": d.isoformat() if d else None,
        "time": g["time"],
        "season": seas,
        "group": grp,
        "league": league,
        "home": g["home"],
        "away": g["away"],
        "home_key": norm(g["home"]),
        "away_key": norm(g["away"]),
        "home_display": display_name(g["home"], grp),
        "away_display": display_name(g["away"], grp),
        "score": g["score"] if sc else None,
        "kind": "result" if sc else (g["kind"] or "announcement"),
        "venue": g["venue"],
        "source_post": f"https://vk.com/wall-165244874_{mpost.group(1)}" if mpost else None,
        "source_image": g.get("file"),
    }
    games.append(rec)
    if league == "rba_kids" and sc and rec["kind"] == "result":
        hs, as_ = sc
        for team, gf, ga in ((g["home"], hs, as_), (g["away"], as_, hs)):
            k = norm(team)
            t = standings[seas][grp][k]
            t["played"] += 1; t["scored"] += gf; t["conceded"] += ga
            if gf > ga: t["wins"] += 1
            else: t["losses"] += 1
            tkey = (seas, grp, k)
            if tkey not in team_names or (year_of(team) and year_of(team) not in team_names[tkey]):
                team_names[tkey] = display_name(team, grp)

games.sort(key=lambda r: (r["iso_date"] or "", r["time"]))

standings_out = {}
for seas, groups in standings.items():
    standings_out[seas] = {}
    for grp, teams in groups.items():
        rows = []
        for k, t in teams.items():
            rows.append({
                "team": team_names.get((seas, grp, k), k),
                "key": k,
                "played": t["played"], "wins": t["wins"], "losses": t["losses"],
                "scored": t["scored"], "conceded": t["conceded"],
                "diff": t["scored"] - t["conceded"],
                "points": t["wins"] * 2 + t["losses"],
            })
        rows.sort(key=lambda r: (-r["points"], -r["diff"]))
        for i, r in enumerate(rows, 1):
            r["place"] = i
        standings_out[seas][grp] = rows

# ---------------- official results (from posts/photos) ----------------
official = {
    "2025/2026": {
        "2010": {"event": "Финал четырёх, 06.06.2026, ст. Кировская",
                 "champion": "РУСИЧ 2010 (КМЗ)",
                 "note": "Счёты матчей Ф4 карточками не публиковались; чемпион определён по фото с кубком и текстам постов"},
        "2012": {"event": "Финал четырёх, 14.06.2026, Панфилова 4",
                 "champion": "АМТ 2012 (Академия баскетбола Ткаченко)",
                 "runner_up": "Университет 2012",
                 "third": "Русич 2012",
                 "final_score": "АМТ 2012 53:31 Университет 2012",
                 "third_place_score": "Русич 2012 50:48 Кагальник 2012",
                 "semifinals": ["Университет 2012 54:18 Кагальник 2012", "Русич 2012 50:67 АМТ 2012"]},
        "2014": {"event": "Финал четырёх, 21.06.2026, Панфилова 4",
                 "champion": "ДЮСШ №7 (МБУ ДО ДЮСШ №7, Ростов-на-Дону)",
                 "runner_up": "Урожай (Константиновск)",
                 "third": "Легион 2014",
                 "final_score": "Константиновск 39:58 ДЮСШ №7",
                 "third_place_score": "СШОР №5 24:26 Легион 2014",
                 "semifinals": ["ДЮСШ №7 85:9 Легион 2014", "Константиновск 47:26 СШОР №5"]},
    }
}

# team aliases / notes
notes = [
    "Источник всех данных: карточки матчей и таблицы из VK-сообщества Rostov Basketball Association | RBA (vk.com/rba_rostov_basketball).",
    "Текст постов ВК при скрейпинге отдаётся без кириллицы, поэтому названия команд, счёты и даты извлечены из изображений-карточек (распознавание).",
    "Турнирные таблицы посчитаны по распознанным результатам: 2 очка за победу, 1 за поражение.",
    "Команда «Константиновск» на карточках подписана городом, логотип — БК «Урожай» (Константиновск); в таблицах используется «Урожай (Константиновск)».",
    "Команда ДЮСШ №7 (2010 г.р.) в официальной матрице лиги подписана как ROSTOVPUGS.",
    "«АМТ 2012» = Академия баскетбола Ткаченко.",
    "«Афалины» (2024/25) и «Белые Афалины» (2025/26, 2026/27) — одна организация, девочачья команда, дивизион 2014–2015 г.р.",
    "Взрослая лига RBA (команды с названиями NBA: Chicago Bulls и т.п.) вынесена в league='rba_adult' и не входит в RBA Kids.",
    "Некоторые игровые дни могли не попасть в карточки публикаций; данные могут дополняться.",
]

dataset = {
    "meta": {
        "title": "RBA Kids — результаты и турнирные таблицы",
        "source_name": "Rostov Basketball Association | RBA",
        "source_url": "https://vk.com/rba_rostov_basketball",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "seasons": ["2024/2025", "2025/2026", "2026/2027"],
        "points_system": {"win": 2, "loss": 1},
        "groups": ["2009", "2010", "2012", "2014", "2016", "unknown"],
        "notes": notes,
    },
    "games": games,
    "standings": standings_out,
    "official_results": official,
}

json.dump(dataset, open(f"{BASE}/rba_kids_dataset.json", "w"), ensure_ascii=False, indent=1)
print("games:", len(games),
      "| results:", sum(1 for g in games if g["kind"] == "result"),
      "| announcements:", sum(1 for g in games if g["kind"] != "result"))
print("standings groups:", {s: list(g.keys()) for s, g in standings_out.items()})
site = os.path.join(os.path.dirname(BASE), "data.js")
open(site, "w", encoding="utf-8").write("const DATA = " + json.dumps(dataset, ensure_ascii=False) + ";")
print("->", f"{BASE}/rba_kids_dataset.json")
print("->", site)
