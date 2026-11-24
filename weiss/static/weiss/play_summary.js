// The game's summary (from play.js), opened from the game-over screen: how the damage went turn by turn for both
// players (a line graph against the levels), and the numbers worth a look: the biggest hits, how many damages were
// cancelled, climaxes played and refreshes. game.timeline_view sends the data with the game over.
//
// play.js calls WeissSummary.html(timeline, {me, them}) for the panel's insides; it shows and hides the panel.
(function () {
  "use strict";

  const LOSE_AT = 28; // damage points at level 4: 7 per level, 1 per clock card
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const plural = (n, word, many = `${word}s`) => `${n} ${n === 1 ? word : many}`;
  // A damage total as the level and clock it is ("L2 · 3").
  const asLevel = (points) => `L${Math.floor(points / 7)} · ${points % 7}`;

  // The graph's points, from the start of the game, one per turn ended.
  function series(timeline) {
    return [{ turn: 0, mine: 0, theirs: 0 }, ...(timeline.points || [])];
  }

  function chartHtml(points, names) {
    // Drawn at about the size it shows, so its text stays readable on a phone (the SVG scales to fit).
    const narrow = window.innerWidth < 600;
    const W = narrow ? 340 : 560, H = narrow ? 220 : 240, left = 30, right = narrow ? 62 : 90, top = 12, bottom = 40;
    const short = (label) => (label.length > (narrow ? 8 : 12) ? `${label.slice(0, narrow ? 7 : 11)}…` : label);
    const lastTurn = Math.max(1, points[points.length - 1].turn);
    const x = (turn) => left + (turn / lastTurn) * (W - left - right);
    const y = (value) => top + (1 - Math.min(value, LOSE_AT) / LOSE_AT) * (H - top - bottom);
    // The levels as recessive guide lines, level 4 (losing) at the top.
    const grid = [7, 14, 21, 28].map((v) => `<line x1="${left}" x2="${W - right}" y1="${y(v)}" y2="${y(v)}" class="gs-grid${v === LOSE_AT ? " gs-grid-lose" : ""}"/>
      <text x="${left - 6}" y="${y(v) + 4}" class="gs-axis" text-anchor="end">L${v / 7}</text>`).join("");
    const step = Math.max(1, Math.ceil(lastTurn / (narrow ? 6 : 10)));
    const ticks = points.filter((p) => p.turn % step === 0 || p.turn === lastTurn)
      .map((p) => `<text x="${x(p.turn)}" y="${H - 24}" class="gs-axis" text-anchor="middle">${p.turn}</text>`).join("");
    const line = (key) => points.map((p, i) => `${i ? "L" : "M"}${x(p.turn).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ");
    const dots = (key, who) => points.slice(1).map((p) => `<circle cx="${x(p.turn)}" cy="${y(p[key])}" r="4" class="gs-dot gs-${key}" tabindex="-1">
      <title>${esc(who)} after turn ${p.turn}: ${asLevel(p[key])} (${plural(p[key], "damage point")})</title></circle>`).join("");
    // Direct labels at the ends of the lines, nudged apart if they'd overlap.
    const end = points[points.length - 1];
    let [ym, yt] = [y(end.mine), y(end.theirs)];
    if (Math.abs(ym - yt) < 14) {
      const mid = (ym + yt) / 2;
      [ym, yt] = end.mine >= end.theirs ? [mid - 7, mid + 7] : [mid + 7, mid - 7];
    }
    return `<svg class="gs-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Damage by turn: ${esc(names.me)} ended at ${asLevel(end.mine)}, ${esc(names.them)} at ${asLevel(end.theirs)}">
      ${grid}${ticks}
      <text x="${(left + W - right) / 2}" y="${H - 4}" class="gs-axis" text-anchor="middle">Turn</text>
      <path d="${line("theirs")}" class="gs-line gs-theirs"/><path d="${line("mine")}" class="gs-line gs-mine"/>
      ${dots("theirs", names.them)}${dots("mine", names.me)}
      <text x="${x(end.turn) + 8}" y="${ym + 4}" class="gs-end">${esc(short(names.me))}</text>
      <text x="${x(end.turn) + 8}" y="${yt + 4}" class="gs-end">${esc(short(names.them))}</text>
    </svg>`;
  }

  // The same numbers as a table, for screen readers and anyone who'd rather read them.
  function tableHtml(points, names) {
    const rows = points.slice(1).map((p) => `<tr><td>${p.turn}</td><td>${asLevel(p.mine)}</td><td>${asLevel(p.theirs)}</td></tr>`).join("");
    return `<details class="gs-table"><summary>As a table</summary>
      <table><thead><tr><th scope="col">After turn</th><th scope="col">${esc(names.me)}</th><th scope="col">${esc(names.them)}</th></tr></thead>
      <tbody>${rows}</tbody></table></details>`;
  }

  function tile(value, label, note = "") {
    return `<div class="gs-tile"><span class="gs-tile-value">${value}</span><span class="gs-tile-label">${label}</span>${note ? `<span class="gs-tile-note">${note}</span>` : ""}</div>`;
  }

  function html(timeline, names) {
    const points = series(timeline);
    const hits = timeline.hits || [];
    const dealt = hits.filter((h) => !h.mine);
    const taken = hits.filter((h) => h.mine);
    const biggest = (list) => list.filter((h) => !h.cancelled).reduce((best, h) => (h.amount > best ? h.amount : best), 0);
    const cancelled = (list) => list.filter((h) => h.cancelled).length;
    const tiles = [
      tile(timeline.turns || points[points.length - 1].turn, "Turns"),
      tile(biggest(dealt), "Biggest hit you landed", dealt.length ? `${plural(dealt.length - cancelled(dealt), "damage")} got through` : ""),
      tile(biggest(taken), "Biggest hit you took"),
      tile(`${cancelled(taken)}<small> / ${taken.length}</small>`, "Damages you cancelled", `${esc(names.them)} cancelled ${cancelled(dealt)} of ${dealt.length}`),
      tile(`${timeline.climaxes.mine}<small> – ${timeline.climaxes.theirs}</small>`, "Climaxes played", "you – them"),
      tile(`${timeline.refreshes.mine}<small> – ${timeline.refreshes.theirs}</small>`, "Refreshes", "you – them"),
    ].join("");
    const graph = points.length > 1
      ? `<figure class="gs-figure"><figcaption>Damage by turn <span class="gs-legend"><span class="gs-key gs-mine"></span>${esc(names.me)} <span class="gs-key gs-theirs"></span>${esc(names.them)}</span></figcaption>
          ${chartHtml(points, names)}${tableHtml(points, names)}</figure>`
      : `<p class="gs-empty">The game ended before a turn was over, so there's no graph to draw.</p>`;
    return `<div class="gs-tiles">${tiles}</div>${graph}`;
  }

  // A duel's recap (a profile row's recap_view: {me, them, points: [[turn, mine, theirs], ...], moments: [text, ...]}):
  // the same graph and text alternative, then the moments, with no tiles (a recap has no hits or climaxes to count).
  function recapHtml(view) {
    const rows = (view && view.points) || [];
    if (!rows.length) return `<p class="gs-empty">No turns to chart for this game.</p>`;
    const names = { me: view.me || "You", them: view.them || "Your opponent" };
    const points = [{ turn: 0, mine: 0, theirs: 0 }, ...rows.map(([turn, mine, theirs]) => ({ turn, mine, theirs }))];
    const graph = points.length > 1
      ? `<figure class="gs-figure"><figcaption>Damage by turn <span class="gs-legend"><span class="gs-key gs-mine"></span>${esc(names.me)} <span class="gs-key gs-theirs"></span>${esc(names.them)}</span></figcaption>
          ${chartHtml(points, names)}${tableHtml(points, names)}</figure>`
      : `<p class="gs-empty">The game ended before a turn was over, so there's no graph to draw.</p>`;
    const moments = (view.moments || []).length
      ? `<ul class="gs-moments">${view.moments.map((text) => `<li>${esc(text)}</li>`).join("")}</ul>` : "";
    return `${graph}${moments}`;
  }

  window.WeissSummary = { html, recapHtml };
})();
