#!/bin/bash
# RBA Kids — пайплайн обновления сайта
#
#   ./scripts/update.sh             # всё: сбор -> распознавание -> сборка -> commit
#   ./scripts/update.sh --push      # то же + push (GitHub Pages обновится)
#   ./scripts/update.sh status      # что нового / сколько не обработано
#   ./scripts/update.sh build       # только пересобрать данные и data.js
#   ./scripts/update.sh scrape      # только забрать новые посты
#
# Прокси (если нужен для доступа к VK): HTTPS_PROXY=https://user:pass@host:port ./scripts/update.sh ...
# Модель распознавания:            PI_PROVIDER=... PI_MODEL=... ./scripts/update.sh ...
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PUSH=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --push) PUSH=1 ;;
    *) ARGS+=("$a") ;;
  esac
done
CMD="${ARGS[0]:-all}"

say() { printf '\n\033[1;32m== %s\033[0m\n' "$*"; }

do_status() {
  say "status"
  python3 - <<'EOF'
import json, os, glob, re
root = os.path.dirname(os.path.abspath("scripts")) if os.path.basename(os.getcwd()) == "scripts" else os.getcwd()
posts = json.load(open("data/posts.json"))
imgs = json.load(open("data/images.json"))
man = json.load(open("data/manifest.json"))
done = set()
for f in glob.glob("data/out/*.txt"):
    done |= set(re.findall(r"file:\s*(\S+)", open(f, encoding="utf-8").read()))
untr = [m for m in man if m["file"] not in done and os.path.exists("img/" + m["file"])]
print(f"постов ВК:            {len(posts)}")
print(f"постов с картинками:  {len(imgs)}")
print(f"карточек скачано:     {len(man)}")
print(f"не распознано:        {len(untr)}")
games = json.load(open("data/games.json"))
print(f"матчей в базе:        {len(games)}")
EOF
}

do_scrape()    { say "1/6 новые посты ВК";   python3 scripts/scrape_wall.py; }
do_extract()   { say "2/6 картинки постов";  python3 scripts/extract_images.py; }
do_download()  { say "3/6 скачать картинки"; python3 scripts/download_images.py; }
do_batch()     { say "4/6 батчи";            python3 scripts/batch_new.py; }

do_transcribe() {
  say "5/6 распознавание (pi-агенты)"
  python3 scripts/batch_new.py
  for b in data/batches/n*.json; do
    [ -e "$b" ] || continue
    id="$(basename "$b" .json)"
    if [ -f "data/out/$id.txt" ]; then echo "$id уже готов"; continue; fi
    echo "--- батч $id"
    bash scripts/transcribe.sh "$id"
  done
}

do_build() {
  say "6/6 сборка данных"
  python3 scripts/aggregate.py
  python3 scripts/build_dataset.py
}

do_commit() {
  say "git commit"
  git add -A
  if git diff --cached --quiet; then
    echo "изменений нет"
  else
    git commit -m "data: обновление $(date +%Y-%m-%d)"
    if [ "$PUSH" = "1" ]; then
      say "git push"
      git push
    else
      echo "(push пропущен — запустите с --push или git push)"
    fi
  fi
}

case "$CMD" in
  status)   do_status ;;
  scrape)   do_scrape ;;
  extract)  do_extract ;;
  download) do_download ;;
  batch)    do_batch ;;
  transcribe) do_transcribe ;;
  build)    do_build ;;
  all)      do_scrape; do_extract; do_download; do_transcribe; do_build; do_status; do_commit ;;
  *)        echo "неизвестная команда: $CMD"; exit 1 ;;
esac
