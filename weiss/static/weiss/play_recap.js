// The recap of the opponent's turn (from play.js): on our turn, what they did on theirs (game.recap_view sends its
// log lines), summed up at the top of the controls panel and listed move by move under it, until it's put away or
// our turn ends.
//
// play.js makes one with WeissRecap.create(app) and calls render() as it draws the controls and dismiss() when its
// close button is clicked. `app` gives the live board and avatars as functions, and play.js's helpers.
(function () {
  "use strict";

  function create(app) {
    const { controlsEl, esc, who, logHtml, gameNumber } = app;

    let recapKey = ""; // the recap on show (game and turn), so it's only built once
    let recapDismissed = ""; // the one put away

    // Lines that are only the turn going round, left out of the list.
    const RECAP_SKIP = [/^moved to the .+ phase$/, /^ended their turn/, /^(stand|draw|clock|encore|end) phase: /, /^stood all their characters$/];

    // What the opponent's turn came to, as short phrases, from its log lines (in the words game.py logs them in).
    function recapSummary(recap, myName) {
      const count = { played: 0, climax: 0, attacks: 0, taken: 0, cancelled: 0, battles: 0, reversed: 0, abilities: 0 };
      const levels = { mine: 0, theirs: 0 };
      let refreshed = false;
      for (const { who: by, text } of recap.lines) {
        const mine = by === myName;
        let m;
        if (!mine && /^moved .+ from hand to (center|back) stage/.test(text)) count.played += 1;
        else if (!mine && /^moved .+ from hand to climax zone/.test(text)) count.climax += 1;
        else if (!mine && /^(front|side|direct) attack with /.test(text)) count.attacks += 1;
        else if (mine && (m = text.match(/^took (\d+) damage/))) count.taken += Number(m[1]);
        else if (mine && /^negated \d+ damage/.test(text)) count.cancelled += 1;
        else if ((m = text.match(/^battle: .* — (.+)$/))) {
          count.battles += 1;
          count.reversed += m[1] === "neither reversed" ? 0 : m[1].split(", ").length;
        } else if ((m = text.match(/^levelled up to level (\d+)/))) levels[mine ? "mine" : "theirs"] = Number(m[1]);
        else if (!mine && /^triggered the ability of /.test(text)) count.abilities += 1;
        else if (/^decked out/.test(text)) refreshed = true;
      }
      const plural = (n, word, many = `${word}s`) => `${n} ${n === 1 ? word : many}`;
      return [
        count.played && `Played ${plural(count.played, "character")}`,
        count.climax && `Played a climax`,
        count.attacks && plural(count.attacks, "attack"),
        count.taken ? { text: `You took ${count.taken} damage`, tone: "bad" } : count.attacks && { text: "You took no damage", tone: "good" },
        count.cancelled && { text: `You cancelled ${plural(count.cancelled, "hit")}`, tone: "good" },
        count.reversed && `${plural(count.reversed, "character")} reversed in battle`,
        levels.theirs && `They reached level ${levels.theirs}`,
        levels.mine && { text: `You reached level ${levels.mine}`, tone: "bad" },
        count.abilities && plural(count.abilities, "ability", "abilities"),
        refreshed && "A deck ran out",
      ].filter(Boolean).map((item) => (typeof item === "string" ? { text: item, tone: "" } : item));
    }

    function renderRecap() {
      const el = controlsEl.querySelector("[data-recap]");
      const recap = app.board().recap;
      const key = recap ? `${gameNumber()}:${recap.turn}` : "";
      if (!recap || key === recapDismissed) {
        el.hidden = true;
        el.innerHTML = "";
        recapKey = "";
        return;
      }
      if (key === recapKey) return; // already built: leave its list as open or closed as it is
      recapKey = key;
      const myName = app.board().me.name;
      const items = recapSummary(recap, myName);
      const lines = recap.lines.filter((entry) => !RECAP_SKIP.some((re) => re.test(entry.text)));
      const name = esc(recap.who);
      el.innerHTML = `
        <div class="turn-recap-head">
          <h2 class="turn-recap-title">While you were waiting <span>${app.avatars()[recap.who] ? `${who(recap.who)} ` : ""}${name}'s turn ${esc(recap.turn)}</span></h2>
          <button type="button" class="turn-recap-close" data-recap-close aria-label="Put away the recap of ${name}'s turn" title="Put it away">×</button>
        </div>
        ${items.length ? `<ul class="turn-recap-items">${items.map((item) => `<li class="${item.tone ? `recap-${item.tone}` : ""}">${esc(item.text)}</li>`).join("")}</ul>`
          : '<p class="muted small">Nothing much: no attacks and nothing played.</p>'}
        ${lines.length ? `<details class="turn-recap-moves"><summary>Every move (${lines.length})</summary>
          <ol>${lines.map((entry) => `<li>${entry.who ? `<b>${who(entry.who)}</b> ` : ""}${logHtml(entry)}</li>`).join("")}</ol></details>` : ""}`;
      el.hidden = false;
    }

    return {
      render: renderRecap,
      dismiss() {
        recapDismissed = recapKey;
        renderRecap();
      },
    };
  }

  window.WeissRecap = { create };
})();
