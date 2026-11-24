/* The people journal (world_people.html; docs/round-two-plan.md item 4). A person with no picture has a crest: their initial on
   a disc in their deck's colours. The colours come as a comma list in data-colors, and the disc's two colours are set from
   them here; with none, the crest keeps its plain colour from the stylesheet. */
(() => {
  // The same colours as the duel's versus intro (play_versus.js).
  const COLOURS = { Red: "#c8453c", Blue: "#2f72c4", Yellow: "#d9a620", Green: "#3d9a55", Purple: "#8052b8", White: "#d8d8de", Black: "#2a2a33" };
  for (const crest of document.querySelectorAll("[data-colors]")) {
    const known = crest.dataset.colors.split(",").map((colour) => COLOURS[colour.trim()]).filter(Boolean);
    if (!known.length) continue;
    crest.style.setProperty("--crest-a", known[0]);
    crest.style.setProperty("--crest-b", known[1] || "#1b1b24");
  }
})();
