/* Portraits: a recipe of paper-doll parts (see weiss.portraits) drawn as stacked images.

   Each part is layers; each layer's image is picked by the recipe's choices (skin tone, hair colour, expression...)
   and the part's own colour, and drawn at its place on the base's canvas, highest z on top. Sizes are percentages, so
   a portrait scales to any box.

     const kit = await Portrait.load(manifestUrl);
     kit.draw(element, recipe);                         // the portrait as saved
     kit.draw(element, recipe, { mood: "happy" });      // with the base's expression for a feeling, if it has one
     kit.draw(element, recipe, { crop: "face" });       // filling its (positioned) parent with the face, any style

   Any element with data-portrait="{recipe}" and data-manifest="url" on a page is drawn as saved. */
(() => {
  const kits = new Map(); // manifest url -> Promise<kit>

  // A recipe saved before there were art styles and skin tones: {base: "female", hair, parts: {slot: id}}.
  function upgrade(recipe) {
    if (!recipe || recipe.choices) return recipe;
    const base = `sutemo_${recipe.base}`;
    const parts = {};
    for (const [slot, id] of Object.entries(recipe.parts || {})) parts[slot] = { id: `sutemo_${id}`, color: "" };
    return { base, choices: { skin: "1", hair: recipe.hair }, parts };
  }

  function makeKit(manifest, root) {
    const parts = new Map(manifest.parts.map((p) => [p.id, p]));

    // The recipe as drawn: its base's defaults under it, and a mood's expression over it.
    function resolve(recipe, mood) {
      const base = manifest.bases[recipe.base];
      const choices = { ...base.defaults.choices, ...recipe.choices };
      const chosen = { ...recipe.parts };
      const feeling = mood && base.moods && base.moods[mood];
      if (feeling) {
        Object.assign(choices, feeling.choices || {});
        Object.assign(chosen, feeling.parts || {});
      }
      return { base, choices, chosen };
    }

    function layers(recipe, options = {}) {
      recipe = upgrade(recipe);
      const { base, choices, chosen } = resolve(recipe, options.mood);
      const picks = [...base.always.map((id) => ({ id, color: "" })), ...Object.values(chosen)];
      const out = [];
      for (const pick of picks) {
        const part = pick && parts.get(pick.id);
        if (!part || part.base !== recipe.base) continue;
        const own = pick.color || (part.colors ? part.colors[0].key : "");
        for (const layer of part.layers) {
          if (layer.when && !Object.entries(layer.when).every(([dim, allowed]) => allowed.includes(choices[dim]))) continue;
          const key = layer.key.map((dim) => (dim === "own" ? own : choices[dim])).join("|");
          const art = layer.art[key];
          if (art) out.push({ ...art, z: layer.z });
        }
      }
      return out.sort((a, b) => a.z - b.z);
    }

    function draw(element, recipe, options = {}) {
      recipe = upgrade(recipe);
      const base = recipe && manifest.bases[recipe.base];
      if (!base) return;
      const [width, height] = base.size;
      element.classList.add("portrait-doll");
      element.style.aspectRatio = `${width} / ${height}`;
      element.style.setProperty("--doll-zoom", base.zoom || 1); // a style drawn smaller in its canvas is shown bigger
      if (options.crop === "face" && base.face) {
        // Sized so the face is about half its box, and placed with the face in the middle (the box is square).
        const [cx, cy, faceWidth] = base.face;
        const across = 55 / faceWidth;
        element.style.position = "absolute";
        element.style.width = `${across}%`;
        element.style.left = `${50 - cx * across}%`;
        element.style.top = `${50 - cy * across * (height / width)}%`;
      }
      element.replaceChildren(...layers(recipe, options).map((art) => {
        const img = document.createElement("img");
        img.src = root + art.src;
        img.alt = "";
        img.draggable = false;
        img.decoding = "async";
        img.style.left = `${(art.x / width) * 100}%`;
        img.style.top = `${(art.y / height) * 100}%`;
        img.style.width = `${(art.w / width) * 100}%`;
        return img;
      }));
    }

    return { manifest, parts, draw, upgrade };
  }

  function load(url) {
    if (!kits.has(url)) {
      const root = url.slice(0, url.lastIndexOf("/") + 1);
      const promise = fetch(url).then((r) => {
        if (!r.ok) throw new Error(`Couldn't load the portrait parts (${r.status}).`);
        return r.json();
      }).then((manifest) => makeKit(manifest, root));
      promise.catch(() => kits.delete(url)); // let a later try fetch again
      kits.set(url, promise);
    }
    return kits.get(url);
  }

  async function drawSaved(element) {
    try {
      const recipe = JSON.parse(element.dataset.portrait || "null");
      if (!recipe || !recipe.base) return;
      (await load(element.dataset.manifest)).draw(element, recipe, { crop: element.dataset.crop });
    } catch {
      element.hidden = true;
    }
  }

  window.Portrait = { load, upgrade };
  document.querySelectorAll("[data-portrait][data-manifest]").forEach(drawSaved);
})();
