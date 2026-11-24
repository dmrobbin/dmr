/* The profile's recent games: each row with a recap has a "Recap" disclosure that opens the game's chart inline. The chart
   and the moments are drawn by play_summary.js (WeissSummary.recapHtml), the same graph as the game-over summary, so there's
   one chart in the codebase. One row is open at a time.

   The row's data comes from its attributes (profile.html): data-recap-me, data-recap-them, data-recap-points as
   "turn,mine,theirs;..." and the moments as the text of the list inside (data-recap-moment). */
(() => {
  function viewOf(body) {
    const points = (body.dataset.recapPoints || "").split(";").filter(Boolean).map((row) => row.split(",").map(Number));
    const moments = [...body.querySelectorAll("[data-recap-moment]")].map((el) => el.textContent.trim());
    // The viewer is "You", as on the game-over graph (the username would read differently there).
    return { me: "You", them: body.dataset.recapThem || "Your opponent", points, moments };
  }

  function wireProfile() {
    const toggles = document.querySelectorAll("[data-recap-toggle]");
    for (const toggle of toggles) {
      toggle.addEventListener("click", () => {
        const body = document.getElementById(toggle.getAttribute("aria-controls"));
        if (!body) return;
        const opening = body.hidden;
        for (const other of toggles) {
          if (other === toggle) continue;
          other.setAttribute("aria-expanded", "false");
          const otherBody = document.getElementById(other.getAttribute("aria-controls"));
          if (otherBody) otherBody.hidden = true;
        }
        if (opening && !body.dataset.rendered && window.WeissSummary) {
          const chart = document.createElement("div");
          chart.className = "recap-chart-host";
          chart.innerHTML = window.WeissSummary.recapHtml(viewOf(body));
          body.append(chart);
          body.dataset.rendered = "1";
        }
        body.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));
      });
    }
  }

  document.addEventListener("DOMContentLoaded", wireProfile);
})();
