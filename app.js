/* RBA Kids — простой статик-сайт на vanilla JS */
"use strict";

/* ---------- вспомогательные ---------- */
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const GAMES = DATA.games;
const STANDINGS = DATA.standings;
const OFFICIAL = DATA.official_results;

// нормализованные ключи команд -> красивое имя (из таблиц, иначе первое встреченное)
const TEAM_NAME = {};
for (const g of GAMES) {
  if (!TEAM_NAME[g.home_key]) TEAM_NAME[g.home_key] = g.home_display;
  if (!TEAM_NAME[g.away_key]) TEAM_NAME[g.away_key] = g.away_display;
}
for (const season in STANDINGS)
  for (const grp in STANDINGS[season])
    for (const row of STANDINGS[season][grp])
      TEAM_NAME[row.key] = row.team;

const SEASONS = DATA.meta.seasons;
const GROUP_LABEL = { "2009": "2009 г.р.", "2010": "2010 г.р.", "2012": "2012 г.р.",
                      "2014": "2014 г.р.", "2016": "2016 г.р.", "unknown": "Прочие / без года",
                      "nba": "Взрослая лига RBA" };

function teamName(key) { return TEAM_NAME[key] || key; }
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

/* ---------- вкладки ---------- */
$$(".tab").forEach((btn) => btn.addEventListener("click", () => {
  $$(".tab").forEach((b) => b.classList.remove("active"));
  $$(".panel").forEach((p) => p.classList.remove("active"));
  btn.classList.add("active");
  $("#tab-" + btn.dataset.tab).classList.add("active");
}));

function gotoTeam(key) {
  $("#c-team").value = key;
  renderTeam();
  $$(".tab").forEach((b) => b.classList.remove("active"));
  $$(".panel").forEach((p) => p.classList.remove("active"));
  document.querySelector('[data-tab="teams"]').classList.add("active");
  $("#tab-teams").classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ================= ВКЛАДКА «ТАБЛИЦЫ» ================= */
const tSeason = $("#t-season"), tGroup = $("#t-group"), tMy = $("#t-myteam");
let sortCol = null, sortDir = -1;

function fillSelect(sel, values, labelFn, keepFirst) {
  const cur = sel.value;
  while (sel.options.length > (keepFirst ? 1 : 0)) sel.remove(keepFirst ? 1 : 0);
  values.forEach((v) => sel.add(new Option(labelFn(v), v)));
  if (values.includes(cur)) sel.value = cur;
}

SEASONS.forEach((s) => tSeason.add(new Option(s, s)));
tSeason.value = SEASONS[SEASONS.length - 1];

function groupsOf(season) {
  return Object.keys(STANDINGS[season] || {}).sort();
}

function renderGroupSelect() {
  fillSelect(tGroup, groupsOf(tSeason.value), (g) => GROUP_LABEL[g] || g, false);
}

function renderMyTeams() {
  const teams = new Set();
  for (const g of GAMES) {
    if (g.league !== "rba_kids") continue;
    teams.add(g.home_key); teams.add(g.away_key);
  }
  const arr = [...teams].sort((a, b) => teamName(a).localeCompare(teamName(b), "ru"));
  const cur = localStorage.getItem("myTeam") || "";
  tMy.add(new Option("— не выбрана —", ""));
  arr.forEach((k) => tMy.add(new Option(teamName(k), k)));
  tMy.value = cur;
}

function renderFinals() {
  const box = $("#t-finals");
  const f = (OFFICIAL[tSeason.value] || {})[tGroup.value];
  if (!f) { box.style.display = "none"; return; }
  box.style.display = "block";
  let html = `<b>Итоги сезона</b> — ${esc(f.event)}<br>`;
  if (f.champion) html += `🏆 Чемпион: <b>${esc(f.champion)}</b><br>`;
  if (f.runner_up) html += `🥈 Второе место: ${esc(f.runner_up)}<br>`;
  if (f.third) html += `🥉 Третье место: ${esc(f.third)}<br>`;
  if (f.final_score) html += `Финал: ${esc(f.final_score)}<br>`;
  if (f.third_place_score) html += `Матч за 3-е место: ${esc(f.third_place_score)}<br>`;
  if (f.note) html += `<span class="hint">${esc(f.note)}</span>`;
  box.innerHTML = html;
}

const COLS = [
  { k: "place", t: "#", num: true },
  { k: "team", t: "Команда" },
  { k: "played", t: "И", num: true },
  { k: "wins", t: "В", num: true },
  { k: "losses", t: "П", num: true },
  { k: "scored", t: "Забито", num: true },
  { k: "conceded", t: "Пропущено", num: true },
  { k: "diff", t: "Разница", num: true },
  { k: "points", t: "Очки", num: true },
];

function renderStandings() {
  const rows = (STANDINGS[tSeason.value] || {})[tGroup.value] || [];
  const my = localStorage.getItem("myTeam") || "";
  const thead = $("#standings thead"), tbody = $("#standings tbody");

  thead.innerHTML = "<tr>" + COLS.map((c) =>
    `<th data-k="${c.k}">${c.t}${sortCol === c.k ? (sortDir === 1 ? " ▲" : " ▼") : ""}</th>`).join("") + "</tr>";

  const data = [...rows];
  if (sortCol) {
    data.sort((a, b) => {
      const x = a[sortCol], y = b[sortCol];
      return (typeof x === "string" ? String(x).localeCompare(String(y), "ru") : x - y) * sortDir;
    });
  }

  tbody.innerHTML = data.map((r) => {
    const cls = [];
    if (r.key === my) cls.push("my-team");
    if (!sortCol && r.place <= 3) cls.push("p" + r.place);
    const dcls = r.diff > 0 ? "diff-pos" : r.diff < 0 ? "diff-neg" : "";
    return `<tr class="${cls.join(" ")}">
      <td class="pos">${r.place}</td>
      <td><a href="#" data-team="${esc(r.key)}" class="team-link">${esc(r.team)}</a></td>
      <td>${r.played}</td><td class="w">${r.wins}</td><td class="l">${r.losses}</td>
      <td>${r.scored}</td><td>${r.conceded}</td>
      <td class="${dcls}">${r.diff > 0 ? "+" : ""}${r.diff}</td>
      <td><b>${r.points}</b></td></tr>`;
  }).join("");

  thead.querySelectorAll("th[data-k]").forEach((th) => th.addEventListener("click", () => {
    const k = th.dataset.k;
    if (sortCol === k) sortDir = -sortDir; else { sortCol = k; sortDir = -1; }
    renderStandings();
  }));
  tbody.querySelectorAll(".team-link").forEach((a) =>
    a.addEventListener("click", (e) => { e.preventDefault(); gotoTeam(a.dataset.team); }));

  renderFinals();
}

tSeason.addEventListener("change", () => { sortCol = null; renderGroupSelect(); renderStandings(); });
tGroup.addEventListener("change", () => { sortCol = null; renderStandings(); });
tMy.addEventListener("change", () => {
  localStorage.setItem("myTeam", tMy.value);
  renderStandings(); renderGames();
});

/* ================= ВКЛАДКА «МАТЧИ» ================= */
const gSeason = $("#g-season"), gGroup = $("#g-group"), gTeam = $("#g-team"),
      gMonth = $("#g-month"), gVenue = $("#g-venue");

SEASONS.forEach((s) => gSeason.add(new Option(s, s)));
[...new Set(GAMES.map((g) => g.group))].sort()
  .forEach((g) => gGroup.add(new Option(GROUP_LABEL[g] || g, g)));
[...new Set(GAMES.map((g) => g.iso_date ? g.iso_date.slice(0, 7) : null).filter(Boolean))].sort()
  .forEach((m) => gMonth.add(new Option(m, m)));
[...new Set(GAMES.map((g) => g.venue).filter(Boolean))].sort()
  .forEach((v) => gVenue.add(new Option(v, v)));

function renderGames() {
  const teamQ = gTeam.value.trim().toLowerCase();
  const my = localStorage.getItem("myTeam") || "";
  const list = GAMES.filter((g) => {
    if (gSeason.value && g.season !== gSeason.value) return false;
    if (gGroup.value && g.group !== gGroup.value) return false;
    if (gMonth.value && !(g.iso_date || "").startsWith(gMonth.value)) return false;
    if (gVenue.value && g.venue !== gVenue.value) return false;
    if (teamQ) {
      const hay = (g.home + " " + g.away + " " + g.home_display + " " + g.away_display).toLowerCase();
      if (!hay.includes(teamQ)) return false;
    }
    return true;
  });

  let html = "", curDate = null;
  for (const g of [...list].reverse()) {   // сначала — самые новые матчи
    if (g.date !== curDate) {
      curDate = g.date;
      html += `<div class="day">${esc(g.date)} · сезон ${esc(g.season)}</div>`;
    }
    const score = g.score
      ? `<span class="score">${esc(g.score)}</span>`
      : `<span class="score upcoming">анонс</span>`;
    const mark = (k) => k === my ? " ✦" : "";
    html += `<div class="game-row">
      <span class="time">${esc(g.time)}</span>
      <span class="team" data-team="${esc(g.home_key)}">${esc(g.home_display)}${mark(g.home_key)}</span>
      ${score}
      <span class="team" data-team="${esc(g.away_key)}">${esc(g.away_display)}${mark(g.away_key)}</span>
      <span class="venue">${esc(g.venue || "")}</span>
    </div>`;
  }
  if (!html) html = "<p class='hint'>Ничего не найдено — попробуйте изменить фильтры.</p>";
  $("#games-list").innerHTML = html;
  $$("#games-list .team").forEach((el) =>
    el.addEventListener("click", () => gotoTeam(el.dataset.team)));
}

[gSeason, gGroup, gMonth, gVenue].forEach((el) => el.addEventListener("change", renderGames));
gTeam.addEventListener("input", renderGames);

/* ================= ВКЛАДКА «КОМАНДЫ» ================= */
const cTeam = $("#c-team");

function initTeamSelect() {
  const teams = new Set();
  for (const g of GAMES) {
    if (g.league !== "rba_kids") continue;
    teams.add(g.home_key); teams.add(g.away_key);
  }
  [...teams].sort((a, b) => teamName(a).localeCompare(teamName(b), "ru"))
    .forEach((k) => cTeam.add(new Option(teamName(k), k)));
  const my = localStorage.getItem("myTeam");
  if (my) cTeam.value = my;
}

function renderTeam() {
  const key = cTeam.value;
  if (!key) return;
  const games = GAMES.filter((g) => g.home_key === key || g.away_key === key)
    .filter((g) => g.league === "rba_kids");

  let w = 0, l = 0, gf = 0, ga = 0;
  const h2h = {};
  const rows = games.map((g) => {
    const home = g.home_key === key;
    const opp = home ? g.away_key : g.home_key;
    const sc = g.score ? g.score.split(":").map(Number) : null;
    let res = "—";
    if (sc) {
      const [a, b] = home ? sc : [sc[1], sc[0]];
      gf += a; ga += b;
      res = a > b ? "В" : "П";
      if (a > b) w++; else l++;
      const h = h2h[opp] || (h2h[opp] = { g: 0, w: 0, l: 0, gf: 0, ga: 0 });
      h.g++; h.gf += a; h.ga += b;
      if (a > b) h.w++; else h.l++;
    }
    return { g, home, opp, res, sc };
  });

  $("#team-card").innerHTML = `
    <h2 style="margin:6px 0">${esc(teamName(key))}</h2>
    <div class="stat-cards">
      <div class="stat"><div class="num">${games.length}</div><div class="lbl">матчей</div></div>
      <div class="stat"><div class="num">${w}</div><div class="lbl">побед</div></div>
      <div class="stat"><div class="num">${l}</div><div class="lbl">поражений</div></div>
      <div class="stat"><div class="num">${gf}:${ga}</div><div class="lbl">счёт суммарно</div></div>
      <div class="stat"><div class="num">${games.length ? (gf / games.length).toFixed(1) : 0}</div><div class="lbl">в среднем за игру</div></div>
    </div>`;

  $("#h2h tbody").innerHTML = Object.entries(h2h)
    .sort((a, b) => b[1].g - a[1].g)
    .map(([k, h]) => `<tr>
      <td><a href="#" data-team="${esc(k)}" class="team-link">${esc(teamName(k))}</a></td>
      <td>${h.g}</td><td class="w">${h.w}</td><td class="l">${h.l}</td>
      <td>${h.gf}:${h.ga}</td></tr>`).join("");

  let html = "", curDate = null;
  for (const r of [...rows].reverse()) {   // сначала — самые свежие матчи
    if (r.g.date !== curDate) { curDate = r.g.date; html += `<div class="day">${esc(r.g.date)}</div>`; }
    const score = r.sc ? (r.home ? `${r.sc[0]}:${r.sc[1]}` : `${r.sc[1]}:${r.sc[0]}`) : "анонс";
    html += `<div class="game-row">
      <span class="time">${esc(r.g.time)}</span>
      <span class="${r.res === "В" ? "w" : r.res === "П" ? "l" : ""}">${r.res}</span>
      <span class="team" data-team="${esc(r.opp)}">${esc(teamName(r.opp))}</span>
      <span class="score ${r.sc ? "" : "upcoming"}">${score}</span>
      <span class="venue">${esc(r.g.venue || "")} · ${esc(GROUP_LABEL[r.g.group] || r.g.group)}</span>
    </div>`;
  }
  $("#team-games").innerHTML = html || "<p class='hint'>Матчей не найдено.</p>";

  $$("#team-games .team-link, #h2h .team-link").forEach((a) =>
    a.addEventListener("click", (e) => { e.preventDefault(); gotoTeam(a.dataset.team); }));
  $$("#team-games .team").forEach((el) =>
    el.addEventListener("click", () => gotoTeam(el.dataset.team)));
}

cTeam.addEventListener("change", renderTeam);

/* ---------- старт ---------- */
renderGroupSelect();
renderMyTeams();
renderStandings();
renderGames();
initTeamSelect();
renderTeam();
