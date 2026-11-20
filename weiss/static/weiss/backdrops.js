/* Scene backgrounds: illustrated scenes drawn as SVG, with nothing to load, for ScenePlayer (scene.js) and the scene
   editor's gallery. A script's "background city" draws SceneBackdrops.draw("city").

   Each is 1600 × 900 and fills the stage cropped to fit ("slice"), so what matters stays near the middle. Details
   that look random (stars, windows, trees) come from a fixed seed, so a background looks the same every time.
   Some move a little (rain, snow, petals, embers, twinkling): see the vn-bg rules in site.css, which still them for
   anyone who's asked for reduced motion. The names are weiss.scenes.BACKGROUNDS. */
(() => {
  const W = 1600;
  const H = 900;
  let drawn = 0; // each drawing's ids are its own: a page can show several at once (a crossfade, the gallery)

  function seeded(seed) {
    let s = seed >>> 0 || 1;
    return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296);
  }

  // A drawing's toolkit: unique ids, a seeded random number, and the pieces scenes are made of.
  function kit(seed) {
    const prefix = `bg${++drawn}-`;
    const r = seeded(seed);
    const between = (a, b) => a + r() * (b - a);
    const k = {
      r,
      between,
      id: (name) => prefix + name,
      url: (name) => `url(#${prefix}${name})`,
      stops: (list) => list.map(([at, color, alpha = 1]) => `<stop offset="${at}" stop-color="${color}" stop-opacity="${alpha}"/>`).join(""),
      // A gradient from top to bottom (or left to right).
      linear(name, list, across = false) {
        return `<linearGradient id="${k.id(name)}" x1="0" y1="0" x2="${across ? 1 : 0}" y2="${across ? 0 : 1}">${k.stops(list)}</linearGradient>`;
      },
      radial(name, list, cx = 0.5, cy = 0.5, rad = 0.5) {
        return `<radialGradient id="${k.id(name)}" cx="${cx}" cy="${cy}" r="${rad}">${k.stops(list)}</radialGradient>`;
      },
      fill: (paint) => `<rect width="${W}" height="${H}" fill="${paint}"/>`,
      // A soft light: a circle fading out from its middle.
      glow(name, x, y, size, color, alpha = 0.8) {
        return `<defs>${k.radial(name, [[0, color, alpha], [1, color, 0]])}</defs><circle cx="${x}" cy="${y}" r="${size}" fill="${k.url(name)}"/>`;
      },
      stars(count, maxY, color = "#fff", minX = 0, maxX = W) {
        let out = "";
        for (let i = 0; i < count; i++) {
          const size = between(0.8, 2.6);
          out += `<circle class="vn-twinkle" style="animation-delay:${(-r() * 4).toFixed(2)}s" cx="${between(minX, maxX).toFixed(0)}" cy="${(r() * maxY).toFixed(0)}" r="${size.toFixed(1)}" fill="${color}" opacity="${between(0.35, 1).toFixed(2)}"/>`;
        }
        return out;
      },
      // A line of hills or mountains across the picture: `rough` is how far each step can rise or fall.
      ridge(base, rough, step, color, smooth = true) {
        let y = base;
        const points = [];
        for (let x = -step; x <= W + step; x += step) {
          y = Math.min(H, Math.max(base - rough * 2.5, y + between(-rough, rough) * (smooth ? 0.5 : 1) + (base - y) * 0.25));
          points.push([x, y]);
        }
        let d = `M${-step} ${H} L${points[0][0]} ${points[0][1].toFixed(0)}`;
        for (let i = 1; i < points.length; i++) {
          const [x, py] = points[i];
          const [px, ppy] = points[i - 1];
          d += smooth ? ` Q${px} ${ppy.toFixed(0)} ${((px + x) / 2).toFixed(0)} ${((ppy + py) / 2).toFixed(0)}` : ` L${x} ${py.toFixed(0)}`;
        }
        return `<path d="${d} L${W + step} ${H} Z" fill="${color}"/>`;
      },
      // Buildings, some of their windows lit.
      skyline(base, color, lit, minH, maxH, litShare = 0.3, top = true) {
        let out = "";
        for (let x = -20; x < W + 20;) {
          const w = between(60, 150);
          const h = between(minH, maxH);
          const y = base - h;
          out += `<rect x="${x.toFixed(0)}" y="${y.toFixed(0)}" width="${(w - 4).toFixed(0)}" height="${(h + 4).toFixed(0)}" fill="${color}"/>`;
          if (top && r() < 0.25) out += `<rect x="${(x + w / 2 - 3).toFixed(0)}" y="${(y - between(20, 60)).toFixed(0)}" width="4" height="70" fill="${color}"/>`;
          if (lit) {
            for (let wy = y + 14; wy < base - 12; wy += 22) {
              for (let wx = x + 10; wx < x + w - 16; wx += 18) {
                if (r() < litShare) out += `<rect x="${wx.toFixed(0)}" y="${wy.toFixed(0)}" width="9" height="12" fill="${lit}" opacity="${between(0.5, 1).toFixed(2)}"/>`;
              }
            }
          }
          x += w;
        }
        return out;
      },
      // Pines, in rows across the picture.
      pines(base, color, count, minH, maxH, snow = "") {
        let out = "";
        for (let i = 0; i < count; i++) {
          const x = between(-40, W + 40);
          const h = between(minH, maxH);
          const w = h * 0.42;
          const y = base + between(-10, 30);
          out += `<rect x="${(x - w * 0.05).toFixed(0)}" y="${(y - h * 0.15).toFixed(0)}" width="${(w * 0.1).toFixed(0)}" height="${(h * 0.2).toFixed(0)}" fill="${color}"/>`;
          for (let tier = 0; tier < 3; tier++) {
            const ty = y - h * 0.12 - tier * h * 0.28;
            const tw = w * (1 - tier * 0.25);
            out += `<polygon points="${(x - tw / 2).toFixed(0)},${ty.toFixed(0)} ${(x + tw / 2).toFixed(0)},${ty.toFixed(0)} ${x.toFixed(0)},${(ty - h * 0.42).toFixed(0)}" fill="${color}"/>`;
            if (snow) out += `<polygon points="${(x - tw * 0.18).toFixed(0)},${(ty - h * 0.3).toFixed(0)} ${(x + tw * 0.18).toFixed(0)},${(ty - h * 0.3).toFixed(0)} ${x.toFixed(0)},${(ty - h * 0.42).toFixed(0)}" fill="${snow}"/>`;
          }
        }
        return out;
      },
      // Things that fall (snow, petals, rain drops) or rise (embers), each on its own loop.
      drifting(count, make, kind = "fall") {
        let out = "";
        for (let i = 0; i < count; i++) {
          const x = between(-50, W + 50);
          const style = `--dx:${between(-140, 140).toFixed(0)}px;animation-duration:${between(5, 13).toFixed(1)}s;animation-delay:${(-r() * 13).toFixed(1)}s`;
          out += `<g class="vn-${kind}" style="${style}"><g transform="translate(${x.toFixed(0)} 0)">${make(i)}</g></g>`;
        }
        return out;
      },
      rain(count, color = "#b8c8e0") {
        let lines = "";
        for (let i = 0; i < count; i++) {
          const x = between(-100, W + 100);
          const y = between(0, H);
          const len = between(30, 60);
          lines += `<line x1="${x.toFixed(0)}" y1="${y.toFixed(0)}" x2="${(x - len * 0.25).toFixed(0)}" y2="${(y + len).toFixed(0)}"/>`;
        }
        // Two copies, one above the other, so the loop never shows a seam.
        return `<g class="vn-rain" stroke="${color}" stroke-width="2" stroke-linecap="round" opacity=".45"><g>${lines}</g><g transform="translate(0 -${H})">${lines}</g></g>`;
      },
      clouds(count, minY, maxY, color, alpha, minX = -100, maxX = W) {
        let out = "";
        for (let i = 0; i < count; i++) {
          const x = between(minX, maxX);
          const y = between(minY, maxY);
          const s = between(0.6, 1.5);
          out += `<g opacity="${alpha}" fill="${color}" transform="translate(${x.toFixed(0)} ${y.toFixed(0)}) scale(${s.toFixed(2)})">
            <ellipse cx="0" cy="0" rx="90" ry="26"/><ellipse cx="-45" cy="-14" rx="48" ry="30"/><ellipse cx="30" cy="-24" rx="56" ry="38"/><ellipse cx="80" cy="-6" rx="40" ry="22"/></g>`;
        }
        return out;
      },
      // Shafts of light coming down from above.
      shafts(name, color, count, alpha = 0.12) {
        let out = `<defs>${k.linear(name, [[0, color, alpha], [1, color, 0]])}</defs>`;
        for (let i = 0; i < count; i++) {
          const x = between(100, W - 100);
          const spread = between(60, 180);
          out += `<polygon points="${(x - 30).toFixed(0)},0 ${(x + 30).toFixed(0)},0 ${(x + spread + 120).toFixed(0)},${H} ${(x + 120 - spread).toFixed(0)},${H}" fill="${k.url(name)}"/>`;
        }
        return out;
      },
    };
    return k;
  }

  // --- The scenes ----------------------------------------------------------------------------------------

  // ---- The time of day (0 morning, 1 noon, 2 evening, 3 night). Without one, a picture is drawn at noon. ----
  const hexRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const rgbHex = (c) => `#${c.map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0")).join("")}`;
  const mixHex = (a, b, f) => { const A = hexRgb(a), B = hexRgb(b); return rgbHex(A.map((v, i) => v + (B[i] - v) * f)); };
  // A colour as it looks at a time: night pulls it toward navy and dark, evening warms it, morning lifts it.
  const tone = (hex, t) => (t === 3 ? mixHex(hex, "#070a1e", 0.72) : t === 2 ? mixHex(hex, "#e07a50", 0.16) : t === 0 ? mixHex(hex, "#ffe0b0", 0.1) : hex);
  // Something that differs by time: pick(t, [morning, noon, evening, night]).
  const pick = (t, list) => list[t];
  // How much light a time gives off: lamps and windows glow at evening and night, dimly by day.
  const LIGHT = [0.25, 0.05, 0.75, 1];

  // The sky at a time: its gradient, the sun (low and gold in the morning, high at noon, down on the horizon at
  // evening) or the moon and stars at night, and clouds that match the light.
  const SKIES = [
    { stops: [[0, "#7aa6d6"], [0.45, "#e8c8b0"], [0.8, "#ffe2b8"]], sun: [330, 560, 170, "#ffe8b0"], clouds: "#fff3e4", cloudA: 0.8 },
    { stops: [[0, "#3a8fe0"], [0.7, "#bfe3ff"], [1, "#e8f4ff"]], sun: [1180, 150, 200, "#fffbe8"], clouds: "#ffffff", cloudA: 0.85 },
    { stops: [[0, "#2a1a4a"], [0.42, "#7a3a6a"], [0.7, "#ff7a4a"], [0.86, "#ffc070"]], sun: [820, 690, 300, "#ffb060"], clouds: "#e88a6a", cloudA: 0.6 },
    { stops: [[0, "#02030c"], [0.5, "#080c26"], [0.85, "#14193e"]], moon: [1180, 170, 140], stars: 150, clouds: "#1c2236", cloudA: 0.7 },
  ];
  function skyPaint(k, t) {
    const s = SKIES[t];
    let out = `<defs>${k.linear("sky", s.stops)}</defs>${k.fill(k.url("sky"))}`;
    if (s.stars) out += k.stars(s.stars, 600, "#f4f0ff");
    if (s.sun) {
      const [x, y, r, color] = s.sun;
      out += `${k.glow(`sun${t}`, x, y, r * 2.2, color, 0.7)}<circle cx="${x}" cy="${y}" r="${Math.round(r * 0.3)}" fill="${color}"/>`;
    }
    if (s.moon) {
      const [x, y, r] = s.moon;
      out += `${k.glow("moon", x, y, r * 3, "#c8d4ff", 0.35)}<circle cx="${x}" cy="${y}" r="${Math.round(r * 0.22)}" fill="#f0f4ff"/>`;
    }
    out += k.clouds(5, 60, 280, s.clouds, s.cloudA);
    return out;
  }
  // The colours of a window's view at a time, top to bottom: a sky through the glass.
  const WINDOW_SKY = [["#9cc4ea", "#f8dcb0"], ["#87c6f0", "#dff0ff"], ["#3a2a5e", "#ff9a5a"], ["#03050f", "#1a2250"]];

  // Things that say where a place is, drawn the same way in each place that has them. Each takes the drawing's kit
  // (k), so colours and glows follow the time (k.light).
  const props = {
    // A lamp: a post, a hood and a glow that switches on with the light.
    lamp(k, x, base, h, glow = "#ffd9a0", id = "") {
      return `<rect x="${x - 4}" y="${base - h}" width="8" height="${h}" fill="#1e1a22"/><rect x="${x - 16}" y="${base - h - 6}" width="32" height="10" rx="4" fill="#2a2430"/>`
        + `${k.glow(`lamp${id}${Math.round(x)}`, x, base - h - 2, 150, glow, 0.15 + 0.7 * k.light)}<circle cx="${x}" cy="${base - h - 2}" r="9" fill="${k.light > 0.5 ? "#fff4d8" : "#8a8070"}"/>`;
    },
    // A bench in front of a wall or path: a seat, a back and two legs.
    bench(x, y, w, color = "#5a3e2a") {
      return `<rect x="${x}" y="${y}" width="${w}" height="10" rx="3" fill="${color}"/><rect x="${x}" y="${y - 26}" width="${w}" height="7" rx="3" fill="${color}"/>`
        + `<rect x="${x + 6}" y="${y + 10}" width="8" height="22" fill="#2a1e16"/><rect x="${x + w - 14}" y="${y + 10}" width="8" height="22" fill="#2a1e16"/>`;
    },
    // A window with a view outside (a sky gradient in the given colours), a frame and cross bars.
    window(k, name, x, y, w, h, top, bottom, frame = "#2a1810") {
      return `<defs>${k.linear(name, [[0, top], [1, bottom]])}</defs><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${k.url(name)}"/>`
        + `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="none" stroke="${frame}" stroke-width="16"/>`
        + `<rect x="${x + w / 2 - 8}" y="${y}" width="16" height="${h}" fill="${frame}"/><rect x="${x}" y="${y + h / 2 - 8}" width="${w}" height="16" fill="${frame}"/>`
        + `<rect x="${x - 10}" y="${y + h}" width="${w + 20}" height="12" rx="4" fill="${frame}"/>`;
    },
    // A pendant lamp hanging from the top of the picture, lit more at night.
    pendant(k, x, y = 230, glow = "#ffd08a") {
      return `<line x1="${x}" y1="0" x2="${x}" y2="${y - 36}" stroke="#1e140f" stroke-width="3"/><path d="M${x - 34} ${y} q34 -44 68 0 Z" fill="#2e1e16"/>`
        + `${k.glow(`pend${Math.round(x)}`, x, y + 6, 210, glow, 0.12 + 0.7 * k.light)}<circle cx="${x}" cy="${y + 6}" r="10" fill="${k.light > 0.5 ? "#fff0c0" : "#8a7a60"}"/>`;
    },
    // A table in front, seen from the front: a top and four legs.
    table(x, y, w, color = "#6a4228") {
      return `<rect x="${x}" y="${y}" width="${w}" height="16" rx="4" fill="${color}"/><rect x="${x + 14}" y="${y + 16}" width="10" height="110" fill="#2a1a10"/><rect x="${x + w - 24}" y="${y + 16}" width="10" height="110" fill="#2a1a10"/>`;
    },
    // A cup on a surface, for small details.
    cup(x, y, color = "#f2ead8") {
      return `<rect x="${x}" y="${y - 22}" width="20" height="22" rx="4" fill="${color}"/><rect x="${x + 20}" y="${y - 16}" width="6" height="8" fill="none" stroke="${color}" stroke-width="3"/>`;
    },
    // A row of plants in pots along a ledge.
    plants(x0, x1, y, color = "#2e5a3a") {
      let out = "";
      for (let x = x0; x < x1; x += 34) out += `<ellipse cx="${x}" cy="${y - 20}" rx="22" ry="30" fill="${color}"/><rect x="${x - 10}" y="${y - 4}" width="20" height="18" fill="#5a3a26"/>`;
      return out;
    },
  };

  const SCENES = {
    default: { label: "Default", draw(k) {
      return `<defs>${k.radial("v", [[0, "#3a3446"], [0.7, "#141219"], [1, "#07060a"]], 0.5, 0.32, 0.8)}</defs>${k.fill(k.url("v"))}
        ${k.shafts("s", "#e8dcff", 3, 0.09)}
        <rect y="690" width="${W}" height="210" fill="#0c0b10" opacity=".7"/>${k.glow("pool", 800, 760, 520, "#8a7aa8", 0.25)}`;
    } },

    dusk: { label: "Dusk", draw(k) {
      return `<defs>${k.linear("sky", [[0, "#23173a"], [0.45, "#6d3b62"], [0.72, "#d8735a"], [0.82, "#f4b26a"]])}</defs>${k.fill(k.url("sky"))}
        ${k.stars(40, 260)}${k.glow("sun", 820, 600, 340, "#ffcf7a", 0.75)}<circle cx="820" cy="610" r="70" fill="#ffe2a8"/>
        ${k.clouds(5, 240, 420, "#f2a07a", 0.35)}
        ${k.ridge(560, 40, 80, "#6a3550")}${k.ridge(640, 50, 70, "#46223e")}${k.ridge(730, 40, 60, "#2a1428")}`;
    } },

    night: { label: "Night", draw(k) {
      return `<defs>${k.linear("sky", [[0, "#04060f"], [0.6, "#101a3a"], [0.85, "#1f2c55"]])}</defs>${k.fill(k.url("sky"))}
        ${k.stars(170, 620)}${k.glow("moonglow", 1220, 190, 230, "#c8d4ff", 0.35)}
        <circle cx="1220" cy="190" r="62" fill="#f3f0e4"/><circle cx="1200" cy="175" r="10" fill="#d8d3c3"/><circle cx="1240" cy="210" r="14" fill="#dcd7c8"/><circle cx="1232" cy="168" r="6" fill="#d8d3c3"/>
        ${k.ridge(640, 55, 70, "#141c38")}${k.ridge(740, 45, 60, "#0a0f22")}`;
    } },

    dawn: { label: "Dawn", draw(k) {
      return `<defs>${k.linear("sky", [[0, "#3d5f99"], [0.42, "#b79ac0"], [0.6, "#f6c8a0"], [0.62, "#ffe4b8"]])}${k.linear("sea", [[0, "#c9a3a8"], [1, "#2c3c5c"]])}</defs>
        ${k.fill(k.url("sky"))}${k.clouds(6, 120, 380, "#fbd9c4", 0.45)}
        ${k.glow("sun", 800, 560, 360, "#fff0c8", 0.8)}<circle cx="800" cy="560" r="80" fill="#fff4d6"/>
        ${k.ridge(540, 60, 90, "#6a6b8f", false)}
        <rect y="560" width="${W}" height="340" fill="${k.url("sea")}"/>
        ${Array.from({ length: 14 }, (_, i) => `<rect x="${(800 - 160 + i * 3 + k.between(-40, 40)).toFixed(0)}" y="${575 + i * 22}" width="${(320 - i * 12).toFixed(0)}" height="4" rx="2" fill="#fff0c8" opacity="${(0.8 - i * 0.05).toFixed(2)}"/>`).join("")}
        <rect y="540" width="${W}" height="60" fill="#f6dccc" opacity=".25"/>`;
    } },

    crimson: { label: "Crimson", draw(k) {
      return `<defs>${k.radial("sky", [[0, "#ff7a3c"], [0.35, "#b0201f"], [0.75, "#3a0710"], [1, "#12020a"]], 0.5, 1, 0.95)}</defs>${k.fill(k.url("sky"))}
        ${k.clouds(7, 120, 420, "#2a0508", 0.55)}
        ${k.ridge(640, 70, 60, "#2a050c", false)}${k.ridge(760, 50, 50, "#140207", false)}
        ${k.drifting(46, () => `<circle r="${k.between(2, 5).toFixed(1)}" fill="${k.r() < 0.5 ? "#ffb347" : "#ff6a2c"}"/>`, "rise")}`;
    } },

    ocean: { label: "Ocean", draw(k) {
      let waves = "";
      for (let y = 560; y < H; y += 26) {
        let d = `M0 ${y}`;
        for (let x = 0; x <= W; x += 80) d += ` q40 ${k.between(-8, 8).toFixed(0)} 80 0`;
        waves += `<path d="${d}" stroke="#d9f0ff" stroke-width="2" fill="none" opacity="${(0.15 + (y - 560) / 1400).toFixed(2)}"/>`;
      }
      return `<defs>${k.linear("sky", [[0, "#5aa6e0"], [1, "#bfe3f6"]])}${k.linear("sea", [[0, "#3a8cc0"], [1, "#0e3a5e"]])}</defs>
        ${k.fill(k.url("sky"))}${k.glow("sun", 1180, 170, 220, "#fffbe8", 0.8)}<circle cx="1180" cy="170" r="54" fill="#fffdf2"/>
        ${k.clouds(7, 140, 420, "#ffffff", 0.75)}
        <rect y="540" width="${W}" height="360" fill="${k.url("sea")}"/><rect y="538" width="${W}" height="4" fill="#e8f6ff" opacity=".6"/>${waves}
        <path d="M380 260 q14 -12 28 0 q14 -12 28 0" stroke="#203040" stroke-width="3" fill="none"/><path d="M470 300 q10 -9 20 0 q10 -9 20 0" stroke="#203040" stroke-width="3" fill="none"/>`;
    } },

    forest: { label: "Forest", draw(k) {
      // A forest at a time: the canopy's light (bright by day, dim at evening, black at night with the stars through the
      // gaps), the far trees in haze, the middle pines, the near trunks, the fern floor and the light shafts by day.
      const t = k.time;
      let trunks = "";
      for (const [x, w] of [[60, 70], [220, 46], [1400, 60], [1560, 80]]) trunks += `<rect x="${x}" y="-20" width="${w}" height="940" fill="${tone("#14100c", t)}"/><rect x="${x + w * 0.2}" y="-20" width="${w * 0.12}" height="940" fill="${tone("#24201a", t)}" opacity=".6"/>`;
      let ferns = "";
      for (let x = 0; x < W; x += 60) ferns += `<path d="M${x} 900 q 30 -${k.between(60, 110).toFixed(0)} ${k.between(-10, 50).toFixed(0)} -${k.between(90, 140).toFixed(0)} q -10 ${k.between(40, 70).toFixed(0)} -${k.between(10, 30).toFixed(0)} ${k.between(60, 80).toFixed(0)}" fill="${tone("#0a1a0c", t)}"/>`;
      return `<defs>${k.linear("sky", [[0, tone("#3c5e3e", t)], [0.5, tone("#1d3a24", t)], [1, tone("#0a160d", t)]])}${k.linear("floor", [[0, tone("#1a2a1a", t)], [1, tone("#050c06", t)]])}</defs>${k.fill(k.url("sky"))}
        ${t < 3 ? k.shafts("light", pick(t, ["#fff0c0", "#f0ffd0", "#ffb070", "#000"]), 5, t === 2 ? 0.1 : 0.14) : ""}
        ${t === 3 ? k.stars(60, 300, "#f6f0ff") : ""}
        ${k.pines(500, tone("#2e5a3a", t), 26, 200, 300)}
        ${k.pines(580, tone("#244a30", t), 26, 240, 360)}
        ${k.pines(680, tone("#1a3622", t), 24, 280, 420)}
        ${k.glow("mist", 800, 620, 900, "#c8f0c8", 0.12)}
        ${k.pines(780, tone("#0f2215", t), 18, 340, 520)}
        <rect y="780" width="${W}" height="120" fill="${k.url("floor")}"/>
        ${ferns}
        ${trunks}
        ${props.lamp(k, 330, 780, 120, "#ffd0a0", "f")}`;
    } },

    void: { label: "Void", draw(k) {
      return `${k.fill("#000")}${k.glow("n1", 520, 380, 420, "#3a1a5a", 0.35)}${k.glow("n2", 1150, 560, 380, "#102a4a", 0.3)}
        ${k.glow("n3", 820, 300, 700, "#1a1040", 0.5)}${k.stars(160, H, "#6f63a0")}
        <path d="M-40 520 C 300 430, 620 610, 980 500 S 1420 420, 1640 500 L 1640 600 C 1300 560, 900 660, 560 600 S 120 640, -40 600 Z" fill="#7a5aa8" opacity=".08"/>
        ${k.stars(60, H, "#b9a8ff")}`;
    } },

    city: { label: "City", draw(k) {
      // The town's skyline at a time: a daytime city by day, the lit city by evening and night. The street is lit by
      // the lamps and the signs glow when it's dark.
      const t = k.time;
      const color = pick(t, ["#8c98b8", "#9aa6c4", "#3a2a50", "#0b0c1c"]);
      const lit = t >= 2 ? pick(t, [null, null, "#ffb070", "#ffd889"]) : null;
      return `${skyPaint(k, t)}
        ${k.skyline(680, tone("#1a1d40", t), lit ? tone("#6a76b8", t) : null, 120, 300, 0.1)}
        ${k.skyline(740, pick(t, ["#a8b4cc", "#b8c4dc", "#2e2650", "#1e2148"]), lit, 160, 380, 0.14)}
        ${t >= 2 ? k.glow("haze", 800, 760, 900, "#ff6ab4", 0.12 + 0.12 * k.light) : ""}
        ${k.skyline(840, color, lit ? "#ffd889" : null, 140, 470, t >= 2 ? 0.32 : 0)}
        ${props.lamp(k, 360, 830, 180, "#ffb0d0", "c")}${props.lamp(k, 1240, 830, 180, "#9fe8ff", "d")}
        <rect x="260" y="540" width="120" height="14" rx="7" fill="${t >= 2 ? "#ff4fa8" : "#c05a8a"}" opacity="${0.35 + 0.5 * k.light}"/><rect x="1180" y="480" width="16" height="140" rx="8" fill="${t >= 2 ? "#4fe0ff" : "#5a9ab0"}" opacity="${0.35 + 0.5 * k.light}"/>
        <rect y="820" width="${W}" height="80" fill="${tone("#4a4a58", t)}"/><rect y="818" width="${W}" height="4" fill="${tone("#2a2a48", t)}"/>`;
    } },

    rooftop: { label: "Rooftop", draw(k) {
      // A rooftop at a time: the sky with its sun, sunset or moon; the far and near skylines (their windows lit as the
      // evening comes on); the water tower and rail; string lights that glow at evening and night; plants in front.
      const t = k.time;
      let rail = "";
      for (let x = 0; x <= W; x += 46) rail += `<rect x="${x}" y="610" width="6" height="140" fill="${tone("#1a1520", t)}"/>`;
      let strings = "";
      for (let i = 0; i < 16; i++) strings += `<circle cx="${(i * 100 + 40).toFixed(0)}" cy="${(560 + Math.sin(i * 0.9) * 12 + 14).toFixed(0)}" r="5" fill="#ffd98a" opacity="${(0.25 + 0.7 * k.light).toFixed(2)}"/>`;
      const lit = t >= 2 ? "#ffd99a" : null;
      return `<defs>${k.linear("roof", [[0, tone("#3a3045", t)], [1, tone("#1e1a24", t)]])}</defs>${skyPaint(k, t)}
        ${k.skyline(600, tone("#6a4a72", t), lit, 60, 220, 0.06)}
        ${k.skyline(660, tone("#4a2f52", t), lit, 80, 300, 0.12)}
        <g fill="${tone("#1a1520", t)}"><rect x="1240" y="380" width="170" height="150" rx="10"/><polygon points="1225,380 1425,380 1325,320"/><rect x="1258" y="530" width="10" height="210"/><rect x="1382" y="530" width="10" height="210"/><rect x="1258" y="600" width="134" height="8"/><rect x="1330" y="250" width="6" height="70"/></g>
        <rect x="1280" y="420" width="90" height="36" rx="4" fill="#ffd27a" opacity="${(0.1 + 0.5 * k.light).toFixed(2)}"/>
        ${strings}
        <rect y="740" width="${W}" height="160" fill="${k.url("roof")}"/><rect y="740" width="${W}" height="6" fill="${tone("#3d3545", t)}"/>
        ${rail}<rect y="602" width="${W}" height="12" fill="${tone("#1a1520", t)}"/><rect y="672" width="${W}" height="6" fill="${tone("#1a1520", t)}"/>
        ${props.plants(60, 420, 860, tone("#2e5a3a", t))}${props.plants(1180, 1560, 870, tone("#2e5a3a", t))}
        ${k.glow("rim", 800, 900, 700, "#ffb070", 0.05 + 0.2 * k.light)}`;
    } },

    rain: { label: "Rainy street", draw(k) {
      // A wet back alley at a time: an overcast sky by day, the dark sky of the night, the walls in perspective, the
      // puddled street reflecting the lights, a shop sign and a lamp, and the rain in front.
      const t = k.time;
      let reflections = "";
      for (let i = 0; i < 46; i++) {
        const x = k.between(0, W);
        reflections += `<rect x="${x.toFixed(0)}" y="${k.between(770, 830).toFixed(0)}" width="${k.between(6, 16).toFixed(0)}" height="${k.between(40, 130).toFixed(0)}" fill="${k.r() < 0.6 ? "#ffd889" : "#7fd0ff"}" opacity="${(0.1 + 0.2 * k.light).toFixed(2)}"/>`;
      }
      return `<defs>${k.linear("sky", [[0, pick(t, ["#8a94a4", "#7a8494", "#3a2a4a", "#060a18"])], [1, pick(t, ["#b8c0cc", "#9aa4b4", "#7a4a5a", "#1a2238"])]])}${k.linear("street", [[0, tone("#2a3242", t)], [1, tone("#0e1118", t)]])}${k.linear("wall", [[0, tone("#1e2432", t)], [1, tone("#0e1118", t)]])}</defs>${k.fill(k.url("sky"))}
        ${k.skyline(700, tone("#2a3242", t), t >= 2 ? "#e8c880" : null, 200, 480, 0.22)}
        ${k.skyline(780, tone("#1a1f2c", t), t >= 2 ? "#e8c880" : null, 240, 540, 0.18)}
        <rect y="760" width="${W}" height="140" fill="${k.url("street")}"/>${reflections}
        <polygon points="0,0 360,120 360,900 0,900" fill="${k.url("wall")}"/><polygon points="1600,0 1240,120 1240,900 1600,900" fill="${k.url("wall")}"/>
        <rect x="300" y="110" width="20" height="790" fill="#10131a" opacity=".6"/>
        <g fill="#10131a"><rect x="1150" y="380" width="12" height="390"/><path d="M1156 386 q70 -40 120 10" stroke="#10131a" stroke-width="10" fill="none"/><rect x="1252" y="392" width="44" height="18" rx="6"/></g>
        ${k.glow("lamp", 1274, 430, 200, "#ffdc9a", 0.15 + 0.6 * k.light)}
        <rect x="90" y="300" width="170" height="60" rx="8" fill="#17202e"/><rect x="100" y="312" width="150" height="36" rx="4" fill="#ff6a9a" opacity="${(0.3 + 0.4 * k.light).toFixed(2)}"/>
        ${k.glow("sign", 175, 330, 220, "#ff6a9a", 0.1 + 0.35 * k.light)}
        ${k.rain(260)}`;
    } },

    sakura: { label: "Cherry blossoms", draw(k) {
      // The plaza at a time of day: the sky, distant hills and roofs, the paving, the blossom trees (lit at evening
      // and night only by the lamps), the lamps and a bench, petals in the air and a branch across the corner.
      const t = k.time;
      const pink = (c) => tone(c, t);
      let blossoms = "";
      for (const [cx, cy, scale] of [[180, 140, 1], [330, 90, 1], [470, 170, 1], [260, 260, 1], [600, 120, 1], [90, 300, 1], [420, 300, 0.8]]) {
        for (let i = 0; i < 26; i++) blossoms += `<circle cx="${(cx + k.between(-80, 80) * scale).toFixed(0)}" cy="${(cy + k.between(-50, 50) * scale).toFixed(0)}" r="${(k.between(14, 34) * scale).toFixed(0)}" fill="${pink(["#ffc4d6", "#ffb0c8", "#ffd8e4", "#f79ab8"][Math.floor(k.r() * 4)])}"/>`;
      }
      let roofs = "";
      for (let x = -20; x < W + 40; x += k.between(110, 170)) {
        const w = k.between(90, 140), h = k.between(50, 90);
        roofs += `<rect x="${x.toFixed(0)}" y="${(656 - h).toFixed(0)}" width="${w.toFixed(0)}" height="${(h + 60).toFixed(0)}" fill="${tone("#c4a6c8", t)}"/><polygon points="${(x - 10).toFixed(0)},${(656 - h).toFixed(0)} ${(x + w / 2).toFixed(0)},${(628 - h).toFixed(0)} ${(x + w + 10).toFixed(0)},${(656 - h).toFixed(0)}" fill="${tone("#a88aae", t)}"/>`;
      }
      let petals = "";
      for (let i = 0; i < 70; i++) petals += `<ellipse cx="${k.between(0, W).toFixed(0)}" cy="${k.between(760, 900).toFixed(0)}" rx="${k.between(5, 9).toFixed(0)}" ry="3" fill="${pink(k.r() < 0.5 ? "#ffc4d6" : "#ffe0ea")}" opacity=".8"/>`;
      return `<defs>${k.linear("paving", [[0, tone("#b6d4a0", t)], [1, tone("#7aa86c", t)]])}</defs>${skyPaint(k, t)}
        ${k.ridge(560, 40, 110, tone("#c2a8cc", t))}${roofs}${k.ridge(690, 24, 70, tone("#9cc48e", t))}
        <rect y="720" width="${W}" height="180" fill="${k.url("paving")}"/>
        <path d="M560 900 L780 720 L840 720 L1040 900 Z" fill="${tone("#e6dccb", t)}"/>
        ${blossoms}
        <path d="M-20 900 C 60 700, 60 520, 140 420 S 300 220, 520 150 M140 420 C 220 380, 300 360, 420 300 M90 560 C 40 480, 10 420, -20 380" stroke="${tone("#4a2f2a", t)}" stroke-width="34" fill="none" stroke-linecap="round"/>
        ${props.lamp(k, 430, 760, 190, "#ffdca0", "a")}${props.lamp(k, 1170, 760, 190, "#ffdca0", "b")}
        ${props.bench(1290, 800, 140, tone("#5a3e2a", t))}
        ${petals}
        <path d="M1640 900 C 1560 860, 1480 840, 1380 860" stroke="${tone("#4a2f2a", t)}" stroke-width="18" fill="none" stroke-linecap="round"/>
        ${[[1500, 840], [1430, 850], [1560, 870]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="26" fill="${pink("#ffb0c8")}"/><circle cx="${x + 12}" cy="${y - 10}" r="18" fill="${pink("#ffd8e4")}"/>`).join("")}
        ${k.drifting(40, () => `<ellipse rx="7" ry="4" fill="${k.r() < 0.5 ? "#ffb7cc" : "#ffd3df"}" transform="rotate(${k.between(0, 180).toFixed(0)})"/>`, "fall")}`;
    } },

    shrine: { label: "Shrine", draw(k) {
      // A shrine at a time: the sky and its sun or moon, far mountains and the cedars (greener by day, black at
      // night), the torii gate across the path, stone lanterns that light up after dusk, and grass in front.
      const t = k.time;
      const lantern = (x) => `${k.glow(`l${x}`, x, 600, 110, "#ffb35a", 0.12 + 0.5 * k.light)}<rect x="${x - 18}" y="572" width="36" height="56" rx="10" fill="${k.light > 0.5 ? "#ffcf7a" : "#8a6a48"}"/><rect x="${x - 22}" y="566" width="44" height="8" fill="#3a1e14"/><rect x="${x - 4}" y="628" width="8" height="90" fill="#3a2a22"/>`;
      const stoneLantern = (x) => `<rect x="${x - 10}" y="700" width="20" height="60" fill="#5a5258"/><rect x="${x - 24}" y="680" width="48" height="22" rx="4" fill="#6a6268"/><rect x="${x - 14}" y="652" width="28" height="26" fill="${k.light > 0.5 ? "#ffcf7a" : "#7a6a5a"}" opacity="${(0.4 + 0.5 * k.light).toFixed(2)}"/><rect x="${x - 30}" y="642" width="60" height="12" rx="4" fill="#5a5258"/>${k.glow(`sl${x}`, x, 664, 90, "#ffb35a", 0.1 + 0.4 * k.light)}`;
      const pine = pick(t, ["#2e5a3a", "#264c34", "#2a1a2e", "#06080f"]);
      return `<defs>${k.linear("path", [[0, tone("#5a4a52", t)], [1, tone("#2a2026", t)]])}${k.linear("hill", [[0, tone("#4a3450", t)], [1, tone("#2a1a2e", t)]])}</defs>${skyPaint(k, t)}
        ${k.ridge(520, 60, 120, tone("#6a4a6c", t))}${k.ridge(590, 40, 90, tone("#4a3050", t))}
        ${k.pines(640, pine, 24, 260, 420)}
        <rect y="720" width="${W}" height="180" fill="${k.url("hill")}"/>
        <polygon points="700,720 900,720 1100,900 500,900" fill="${k.url("path")}"/>
        <g fill="${tone("#c8322a", t)}"><rect x="610" y="300" width="36" height="430"/><rect x="954" y="300" width="36" height="430"/><rect x="560" y="360" width="480" height="26"/>
          <path d="M520 262 Q800 300 1080 262 L1092 236 Q800 274 508 236 Z"/></g><rect x="508" y="226" width="584" height="14" fill="#1e1012" rx="4"/>
        <rect x="770" y="386" width="60" height="70" fill="#1e1012"/>
        ${lantern(470)}${lantern(1130)}
        ${stoneLantern(300)}${stoneLantern(1300)}
        <rect x="1380" y="740" width="120" height="30" rx="6" fill="#6a6268"/><ellipse cx="1440" cy="744" rx="48" ry="8" fill="${tone("#2a4a6a", t)}"/>
        <g fill="${tone("#1a1020", t)}" opacity=".9"><path d="M0 900 Q40 840 80 900 Q120 820 160 900 Z"/><path d="M1480 900 Q1520 830 1560 900 Q1600 840 1640 900 Z"/></g>
        ${t >= 2 ? k.stars(20, 600, "#ffe08a") : ""}`;
    } },

    snow: { label: "Snowfield", draw(k) {
      return `<defs>${k.linear("sky", [[0, "#7d93b5"], [1, "#d7e0ee"]])}</defs>${k.fill(k.url("sky"))}
        ${k.ridge(460, 110, 110, "#f4f7fc", false)}${k.ridge(470, 60, 110, "#c3cfe0", false)}
        ${k.ridge(610, 40, 80, "#e8eef7")}
        ${k.pines(700, "#2c4a4a", 24, 180, 320, "#f4f8ff")}
        <rect y="760" width="${W}" height="140" fill="#f2f6fc"/>
        ${k.drifting(110, () => `<circle r="${k.between(2, 5).toFixed(1)}" fill="#ffffff" opacity=".9"/>`, "fall")}`;
    } },

    beach: { label: "Beach", draw(k) {
      // A beach at a time: the sky with its sun or moon, the far sea and island, the sea with waves (the moon's path
      // across it at night), the wet and dry sand, a palm on the right and rocks in front.
      const t = k.time;
      return `<defs>${k.linear("sea", [[0, tone("#22a8c8", t)], [1, tone("#0a6a9a", t)]])}${k.linear("far", [[0, tone("#5ab8d8", t)], [1, tone("#2a88b0", t)]])}${k.linear("sand", [[0, tone("#f6e2b0", t)], [1, tone("#e2c48a", t)]])}${k.linear("wet", [[0, tone("#c8a878", t)], [1, tone("#a88858", t)]])}</defs>
        ${skyPaint(k, t)}
        <rect y="470" width="${W}" height="60" fill="${k.url("far")}"/><path d="M900 530 q60 -36 150 -20 q70 0 110 20 Z" fill="${tone("#3a8a6a", t)}" opacity=".7"/>
        <rect y="500" width="${W}" height="220" fill="${k.url("sea")}"/>
        ${t === 3 ? `<path d="M1150 500 L1135 900 L1220 900 L1210 500 Z" fill="#c8d4ff" opacity=".18"/><path d="M1170 540 q30 10 40 40 M1150 610 q40 12 52 46" stroke="#e8f0ff" stroke-width="3" fill="none" opacity=".4"/>` : ""}
        <path d="M0 540 Q400 520 800 540 T1600 540" stroke="#ffffff" stroke-width="3" fill="none" opacity=".25"/><path d="M0 600 Q400 580 800 600 T1600 600" stroke="#ffffff" stroke-width="4" fill="none" opacity=".2"/>
        <path d="M0 700 Q200 680 400 700 T800 700 T1200 700 T1600 700 L1600 900 L0 900 Z" fill="${k.url("sand")}"/>
        <path d="M0 780 Q200 760 400 780 T800 780 T1200 780 T1600 780 L1600 900 L0 900 Z" fill="${k.url("wet")}" opacity=".5"/>
        <path d="M0 704 Q200 684 400 704 T800 704 T1200 704 T1600 704" stroke="#ffffff" stroke-width="6" fill="none" opacity=".8"/>
        <ellipse cx="520" cy="860" rx="90" ry="22" fill="${tone("#8a7050", t)}"/><ellipse cx="560" cy="848" rx="50" ry="14" fill="${tone("#a08660", t)}"/>
        <path d="M1290 900 C1300 760, 1320 620, 1370 470" stroke="${tone("#5a4030", t)}" stroke-width="22" fill="none"/>
        <g fill="${tone("#2f4a2a", t)}"><path d="M1370 470 q-120 -40 -220 40 q110 -20 220 -40"/><path d="M1370 470 q100 -70 220 -20 q-110 -10 -220 20"/><path d="M1370 470 q-40 -110 -150 -130 q80 40 150 130"/><path d="M1370 470 q60 -110 160 -110 q-90 30 -160 110"/><path d="M1370 470 q-20 -60 -60 -90 q50 30 60 90"/></g>`;
    } },

    space: { label: "Space", draw(k) {
      return `${k.fill("#03030a")}${k.glow("n1", 420, 300, 520, "#6a2a8a", 0.4)}${k.glow("n2", 1100, 220, 460, "#1a6a8a", 0.35)}${k.glow("n3", 800, 700, 500, "#8a2a5a", 0.25)}
        <path d="M-40 760 C 360 560, 760 640, 1100 420 S 1500 300, 1640 260 L 1640 360 C 1420 420, 1200 560, 880 720 S 300 860, -40 900 Z" fill="#8a6aa8" opacity=".07"/>
        ${k.stars(260, H)}
        <defs>${k.radial("planet", [[0, "#f0b878"], [0.6, "#b0603a"], [1, "#3a1a1a"]], 0.35, 0.3, 0.8)}</defs>
        <ellipse cx="1220" cy="640" rx="330" ry="60" fill="none" stroke="#e8c8a0" stroke-width="10" opacity=".5" transform="rotate(-14 1220 640)"/>
        <circle cx="1220" cy="640" r="190" fill="${k.url("planet")}"/>
        <path d="M 900 720 A 330 60 -14 0 0 1540 560" fill="none" stroke="#f2d8b8" stroke-width="10" opacity=".75" transform="rotate(0)"/>
        <circle cx="380" cy="180" r="34" fill="#c8ccd8"/><circle cx="372" cy="172" r="34" fill="#03030a" opacity=".55"/>`;
    } },

    ruins: { label: "Ruins", draw(k) {
      // An old warehouse at a time: the sky through the broken roof (the sun, the sunset, or the moon), the far
      // skyline, the brick walls and columns, the collapsed beam and rubble, the fires that glow at night and the
      // dust in the air.
      const t = k.time;
      let columns = "";
      for (const [x, h, c] of [[220, 380, "#3a3036"], [420, 250, "#4a3a40"], [1100, 330, "#4a3a40"], [1320, 420, "#3a3036"], [760, 160, "#2e262c"]]) {
        const top = 760 - h;
        columns += `<rect x="${x}" y="${top}" width="70" height="${h}" fill="${tone(c, t)}"/><polygon points="${x},${top} ${x + 22},${top - 26} ${x + 40},${top - 6} ${x + 58},${top - 34} ${x + 70},${top}" fill="${tone(c, t)}"/>
          <rect x="${x + 14}" y="${top}" width="6" height="${h}" fill="#2a2228"/><rect x="${x + 44}" y="${top}" width="6" height="${h}" fill="#2a2228"/>`;
      }
      let bricks = "";
      for (let y = 200; y < 760; y += 36) for (let x = (y / 36) % 2 ? 0 : 40; x < W; x += 80) bricks += `<rect x="${x}" y="${y}" width="76" height="32" fill="#2a1e22" opacity=".5"/>`;
      return `<defs>${k.linear("wall", [[0, tone("#3a2a2e", t)], [1, tone("#1e161a", t)]])}</defs>${skyPaint(k, t)}
        ${k.glow("fire", 800, 760, 600, "#ff7a3a", 0.1 + 0.35 * k.light)}
        ${k.skyline(640, tone("#1e161a", t), "#ffa040", 80, 220, 0.04)}
        <rect y="200" width="${W}" height="520" fill="${k.url("wall")}"/>${bricks}
        ${[[260, 260], [980, 300], [1240, 240]].map(([x, y]) => `<rect x="${x}" y="${y}" width="120" height="150" fill="#1a1216"/><rect x="${x + 10}" y="${y + 10}" width="100" height="130" fill="${k.light > 0.5 ? "#ffb060" : "#7a6a64"}" opacity="${(0.25 + 0.45 * k.light).toFixed(2)}"/><path d="M${x + 60} ${y} v 150" stroke="#2a1e22" stroke-width="6"/>`).join("")}
        ${columns}<rect x="560" y="560" width="340" height="40" fill="${tone("#3a3036", t)}" transform="rotate(-8 730 580)"/>
        ${k.ridge(780, 30, 50, tone("#1e161a", t), false)}
        <rect y="800" width="${W}" height="100" fill="${tone("#140e12", t)}"/>
        ${[[120, 820], [520, 830], [1000, 840], [1480, 820]].map(([x, y]) => `<polygon points="${x},${y} ${x + 60},${y - 30} ${x + 110},${y} ${x + 80},${y + 26}" fill="#2a2228"/>`).join("")}
        ${k.drifting(34, () => `<circle r="${k.between(2, 4).toFixed(1)}" fill="#ffa040"/>`, "rise")}`;
    } },

    castle: { label: "Castle", draw(k) {
      const tower = (x, w, top, roof) => `<rect x="${x}" y="${top}" width="${w}" height="${720 - top}" fill="#120c1e"/>${roof ? `<polygon points="${x - 10},${top} ${x + w + 10},${top} ${x + w / 2},${top - roof}" fill="#120c1e"/>` : Array.from({ length: Math.floor(w / 20) }, (_, i) => `<rect x="${x + i * 20}" y="${top - 16}" width="12" height="16" fill="#120c1e"/>`).join("")}`;
      let windows = "";
      for (let i = 0; i < 14; i++) windows += `<rect x="${k.between(560, 1040).toFixed(0)}" y="${k.between(380, 640).toFixed(0)}" width="10" height="18" rx="5" fill="#ffcc6a" opacity="${k.between(0.5, 1).toFixed(2)}"/>`;
      return `<defs>${k.linear("sky", [[0, "#0b0820"], [0.7, "#3a2560"], [1, "#6a3a70"]])}</defs>${k.fill(k.url("sky"))}
        ${k.stars(120, 500)}${k.glow("moon", 1250, 220, 260, "#e8e0ff", 0.4)}<circle cx="1250" cy="220" r="90" fill="#f4f0ff"/>
        ${k.ridge(700, 40, 90, "#1e1530")}
        ${tower(560, 90, 360, 140)}${tower(650, 300, 460, 0)}${tower(760, 80, 300, 180)}${tower(950, 100, 380, 150)}${tower(1050, 70, 500, 0)}
        ${windows}<rect y="720" width="${W}" height="180" fill="#0a0612"/>`;
    } },

    classroom: { label: "Classroom", draw(k) {
      // A classroom at a time: the window shows the time's sky (the night sky with stars at night), the walls and
      // posters darken at night and the ceiling lights come on; the chalkboard, the desks in three depths and the
      // teacher's desk are in front.
      const t = k.time;
      const sky = WINDOW_SKY[t];
      let desks = "";
      for (let row = 0; row < 3; row++) {
        const s = 1 - row * 0.12, y = 700 + row * 80 - row * 30;
        for (let i = 0; i < 5; i++) {
          const x = 180 + i * 290 * s + row * 40;
          desks += `<rect x="${x.toFixed(0)}" y="${y.toFixed(0)}" width="${(200 * s).toFixed(0)}" height="${(20 * s).toFixed(0)}" rx="4" fill="${tone("#6a4a30", t)}"/><rect x="${(x + 16 * s).toFixed(0)}" y="${(y + 20 * s).toFixed(0)}" width="${(10 * s).toFixed(0)}" height="${(90 * s).toFixed(0)}" fill="#3a3a40"/><rect x="${(x + 174 * s).toFixed(0)}" y="${(y + 20 * s).toFixed(0)}" width="${(10 * s).toFixed(0)}" height="${(90 * s).toFixed(0)}" fill="#3a3a40"/>`;
        }
      }
      let chalk = "";
      for (let i = 0; i < 9; i++) chalk += `<path d="M${(560 + k.between(0, 520)).toFixed(0)} ${(260 + i * 34).toFixed(0)} q30 ${k.between(-10, 10).toFixed(0)} ${k.between(60, 240).toFixed(0)} 0" stroke="#e8f0e8" stroke-width="4" fill="none" opacity=".45"/>`;
      return `<defs>${k.linear("wall", [[0, tone("#efe4cc", t)], [1, tone("#d6c6a6", t)]])}${k.linear("win", [[0, sky[0]], [1, sky[1]]])}${k.linear("floor", [[0, tone("#b08858", t)], [1, tone("#7a5434", t)]])}</defs>${k.fill(k.url("wall"))}
        <rect x="560" y="100" width="180" height="120" fill="${tone("#e8dcc0", t)}" stroke="#c8b898" stroke-width="4"/><rect x="580" y="120" width="60" height="80" fill="#c84a3a" opacity=".5"/><rect x="660" y="120" width="60" height="80" fill="#3a6aa8" opacity=".5"/>
        <rect x="1240" y="100" width="180" height="150" fill="${tone("#ece0c6", t)}" stroke="#c8b898" stroke-width="4"/><path d="M1260 210 L1300 160 L1330 190 L1360 150 L1400 210 Z" fill="#7ab060" opacity=".7"/>
        <g><rect x="40" y="150" width="380" height="430" fill="${k.url("win")}"/>${t === 3 ? k.stars(14, 380, "#fff", 40, 420) : k.clouds(2, 260, 380, "#ffffff", 0.8, 120, 300)}${t >= 2 && t < 3 ? k.glow("sunIn", 200, 380, 260, "#ffb070", 0.3) : ""}${t === 3 ? k.glow("moonIn", 320, 240, 130, "#c8d4ff", 0.25) : ""}
          <rect x="40" y="150" width="380" height="430" fill="none" stroke="#f6f0e2" stroke-width="16"/><rect x="222" y="150" width="16" height="430" fill="#f6f0e2"/><rect x="40" y="355" width="380" height="16" fill="#f6f0e2"/></g>
        ${t < 2 ? k.shafts("sun", "#fff6d0", 2, 0.12) : ""}
        ${props.pendant(k, 500, 110, "#ffe0a8")}${props.pendant(k, 1100, 110, "#ffe0a8")}
        <rect x="520" y="210" width="620" height="330" fill="${tone("#2c4a3a", t)}"/><rect x="520" y="210" width="620" height="330" fill="none" stroke="#8a6440" stroke-width="16"/>${chalk}
        <rect x="520" y="546" width="620" height="14" fill="#8a6440"/><rect x="800" y="560" width="30" height="20" fill="#d8d0c0"/>
        <circle cx="1330" cy="230" r="54" fill="#f8f4ea" stroke="#5a4a3a" stroke-width="8"/><path d="M1330 230 V196 M1330 230 L1356 244" stroke="#3a3030" stroke-width="6" stroke-linecap="round"/>
        <rect y="620" width="${W}" height="280" fill="${k.url("floor")}"/>
        <rect x="1200" y="560" width="300" height="70" rx="6" fill="#8a5a38"/><rect x="1220" y="630" width="14" height="90" fill="#4a2e1c"/><rect x="1466" y="630" width="14" height="90" fill="#4a2e1c"/>
        ${desks}
        <rect y="860" width="${W}" height="40" fill="#4a2e1c" opacity=".6"/>`;
    } },

    cafe: { label: "Café", draw(k) {
      // A café at a time: the room darker at night and lit by its pendant lamps; the window shows the street outside
      // in the time's sky, with the lights of the shops blurred through the glass.
      const t = k.time;
      let shelf = "";
      for (let i = 0; i < 14; i++) shelf += `<rect x="${1140 + i * 30}" y="${k.between(300, 316).toFixed(0)}" width="22" height="${k.between(24, 40).toFixed(0)}" rx="4" fill="${tone(["#e8d8c0", "#8a5a3a", "#c84a3a", "#3a6a5a"][Math.floor(k.r() * 4)], t)}"/>`;
      let blur = "";
      for (let i = 0; i < 22; i++) blur += `<circle cx="${k.between(140, 860).toFixed(0)}" cy="${k.between(260, 540).toFixed(0)}" r="${k.between(10, 34).toFixed(0)}" fill="${k.r() < 0.5 ? "#ffd38a" : "#ff9a6a"}" opacity="${(0.12 + 0.3 * k.light).toFixed(2)}"/>`;
      let bands = "";
      for (let y = 0; y < 640; y += 52) bands += `<rect y="${y}" width="${W}" height="2" fill="#000" opacity=".12"/>`;
      const sky = WINDOW_SKY[t];
      return `<defs>${k.linear("wall", [[0, tone("#6a4630", t)], [1, tone("#2e1c14", t)]])}${k.linear("floor", [[0, tone("#4a2e1e", t)], [1, tone("#24160e", t)]])}</defs>${k.fill(k.url("wall"))}
        ${bands}
        <rect x="120" y="230" width="760" height="350" fill="${k.url("out")}"/>
        <defs>${k.linear("out", [[0, sky[0]], [1, sky[1]]])}</defs>${blur}${t !== 3 ? k.glow("outsideSun", 720, 260, 300, t < 2 ? "#fff2c8" : "#ff9a5a", t === 1 ? 0.35 : 0.2) : k.glow("outsideMoon", 860, 300, 160, "#c8d4ff", 0.25)}
        <rect x="120" y="230" width="760" height="350" fill="none" stroke="#2a1810" stroke-width="18"/><rect x="492" y="230" width="16" height="350" fill="#2a1810"/>
        <rect x="1120" y="356" width="440" height="12" fill="#2a1810"/>${shelf}
        <rect x="1120" y="500" width="440" height="6" fill="#2a1810"/>${props.cup(1160, 500)}${props.cup(1200, 500, "#c8a878")}${props.cup(1250, 500)}
        ${props.pendant(k, 380, 230)}${props.pendant(k, 800, 230)}${props.pendant(k, 1240, 240)}
        <rect y="640" width="${W}" height="260" fill="${k.url("floor")}"/><rect y="640" width="${W}" height="26" fill="${tone("#6a4228", t)}"/>
        ${props.table(260, 760, 260, tone("#6a4228", t))}${props.table(1000, 790, 280, tone("#6a4228", t))}
        <rect x="1000" y="580" width="40" height="60" rx="6" fill="${tone("#e8e0d0", t)}"/><rect x="1060" y="596" width="30" height="44" rx="6" fill="${tone("#e8e0d0", t)}"/>
        ${props.cup(1020, 790, tone("#f2ead8", t))}${props.cup(1220, 800, tone("#e8e0d0", t))}
        <rect y="860" width="${W}" height="40" fill="#1a100a" opacity=".6"/>`;
    } },

    library: { label: "Library", draw(k) {
      // A reading room at a time: the arched window shows the time's sky (stars and the moon at night), the shelves
      // darken at night, the lamps and the pendant light the room, the rug and the reading table are in front.
      const t = k.time;
      const sky = WINDOW_SKY[t];
      const shelves = (x0, x1, dim = 1) => {
        let out = `<rect x="${x0}" y="80" width="${x1 - x0}" height="680" fill="${tone("#2a1a12", t)}" opacity="${dim}"/>`;
        for (let y = 120; y < 740; y += 120) {
          let x = x0 + 16;
          while (x < x1 - 30) {
            const w = k.between(12, 26);
            const h = k.between(70, 100);
            out += `<rect x="${x.toFixed(0)}" y="${(y + 100 - h).toFixed(0)}" width="${(w - 2).toFixed(0)}" height="${h.toFixed(0)}" fill="${tone(["#7a2a2a", "#2a4a6a", "#3a5a3a", "#8a6a3a", "#5a3a5a", "#a08060"][Math.floor(k.r() * 6)], t)}" opacity="${dim}"/>`;
            x += w;
          }
          out += `<rect x="${x0}" y="${y + 100}" width="${x1 - x0}" height="14" fill="${tone("#4a2e1e", t)}" opacity="${dim}"/>`;
        }
        return out;
      };
      return `<defs>${k.linear("wall", [[0, tone("#2a1c16", t)], [1, tone("#140c0a", t)]])}${k.linear("win", [[0, sky[0]], [1, sky[1]]])}${k.linear("floor", [[0, tone("#3a2418", t)], [1, tone("#1e120a", t)]])}</defs>${k.fill(k.url("wall"))}
        <path d="M620 700 V260 a180 180 0 0 1 360 0 V700 Z" fill="${k.url("win")}"/>
        ${t === 3 ? k.stars(26, 500, "#fff", 640, 960) : ""}${t >= 2 ? k.glow("moon", 860, 300, 180, "#c8d4ff", t === 3 ? 0.3 : 0.12) : ""}
        <path d="M620 700 V260 a180 180 0 0 1 360 0 V700 Z M800 80 V700 M620 420 H980" fill="none" stroke="${tone("#3a2418", t)}" stroke-width="16"/>
        ${shelves(40, 560, 0.85)}${shelves(1040, 1560, 0.85)}
        <rect x="560" y="80" width="480" height="60" fill="#1e120c" opacity=".5"/>
        <line x1="1400" y1="80" x2="1420" y2="700" stroke="#4a2e1e" stroke-width="10"/><line x1="1460" y1="80" x2="1442" y2="700" stroke="#4a2e1e" stroke-width="10"/>${[160, 260, 360, 460, 560, 660].map((y) => `<rect x="1408" y="${y}" width="46" height="8" fill="#6a4228"/>`).join("")}
        ${props.pendant(k, 800, 130, "#ffc070")}
        <rect y="700" width="${W}" height="200" fill="${k.url("floor")}"/>
        <ellipse cx="800" cy="840" rx="520" ry="60" fill="${tone("#5a1e24", t)}" opacity=".55"/><ellipse cx="800" cy="840" rx="470" ry="46" fill="none" stroke="#c8a060" stroke-width="6" opacity=".5"/>
        ${shelves(-40, 0, 1)}
        <rect x="200" y="640" width="380" height="18" rx="4" fill="#6a4228"/><rect x="216" y="658" width="12" height="120" fill="#2a1a10"/><rect x="552" y="658" width="12" height="120" fill="#2a1a10"/>
        <rect x="260" y="610" width="60" height="30" rx="4" fill="#8a3a3a"/><rect x="330" y="620" width="50" height="22" rx="4" fill="#3a5a8a"/>
        ${props.lamp(k, 490, 600, 80, "#ffc070", "lib")}
        ${k.glow("lampTable", 1260, 760, 260, "#ffc070", 0.1 + 0.3 * k.light)}`;
    } },

    arena: { label: "Arena", draw(k) {
      // A duel arena: a hall with tiered stands rising on both sides and at the back. Each tier is a row of people
      // (a head and rounded shoulders), smaller and darker the further back, in a few colours. Banners hang from the
      // truss, a lit ring is the duel floor, spotlights come down from above, and phone lights glow after dark.
      const t = k.time;
      const SHIRTS = ["#2a2440", "#3a2a4e", "#1e2a3e", "#4a2e3e", "#2e3a2e"];
      // One person at (x, base), scale s, in colour c: a head and shoulders.
      const person = (x, base, s, c) => `<ellipse cx="${x.toFixed(0)}" cy="${(base - 15 * s).toFixed(0)}" rx="${(9 * s).toFixed(1)}" ry="${(10 * s).toFixed(1)}" fill="${c}"/>`
        + `<path d="M${(x - 16 * s).toFixed(1)} ${base.toFixed(0)} Q${(x - 16 * s).toFixed(1)} ${(base - 10 * s).toFixed(0)} ${x.toFixed(0)} ${(base - 10 * s).toFixed(0)} Q${(x + 16 * s).toFixed(1)} ${(base - 10 * s).toFixed(0)} ${(x + 16 * s).toFixed(1)} ${base.toFixed(0)} Z" fill="${c}"/>`;
      // A tier: a step of the stand (x0 to x1, its top at y), with a row of people along its top. far (0 to 1) is how
      // far back it is: smaller, darker and a little hazier.
      const tier = (x0, x1, y, far) => {
        const base = tone(mixHex("#2e2644", "#07060f", 0.25 + far * 0.4), t);
        let out = `<rect x="${x0}" y="${y}" width="${x1 - x0}" height="${900 - y}" fill="${base}"/>`;
        const s = 1.0 - far * 0.3;
        for (let x = x0 + 30 * s; x < x1 - 20 * s; x += 60 * s) {
          const c = mixHex(SHIRTS[Math.floor(k.r() * SHIRTS.length)], "#07060f", 0.2 + far * 0.45);
          out += person(x + k.between(-6, 6), y + 6, s, tone(c, t));
          if (t >= 2 && k.r() < 0.12) out += `<rect x="${(x + 4).toFixed(0)}" y="${(y - 14 * s).toFixed(0)}" width="5" height="8" fill="#cfe8ff" opacity="${(0.4 + 0.5 * k.light).toFixed(2)}"/>`;
        }
        return out;
      };
      let stands = "";
      // Left and right: four tiers, the top one furthest back (the widest, highest step).
      for (let i = 0; i < 4; i++) {
        const far = (3 - i) / 3, y = 300 + i * 120;
        stands += tier(0, 420 - i * 50, y, far);
        stands += tier(W - (420 - i * 50), W, y, far);
      }
      // The back: three tiers rising to the rear wall.
      for (let i = 0; i < 3; i++) {
        const far = (2 - i) / 2, y = 180 - i * 60;
        stands += tier(420 + i * 40, 1180 - i * 40, y, far);
      }
      const beam = (x, color, tilt) => `<defs>${k.linear(`b${x}`, [[0, color, 0.1 + 0.5 * k.light], [1, color, 0]])}</defs><polygon points="${x - 20},0 ${x + 20},0 ${x + tilt + 220},760 ${x + tilt - 220},760" fill="${k.url(`b${x}`)}"/>`;
      return `<defs>${k.linear("hall", [[0, tone("#1a1430", t)], [1, tone("#0c0a18", t)]])}${k.linear("floor", [[0, tone("#3a2a58", t)], [1, tone("#1a1426", t)]])}</defs>${k.fill(k.url("hall"))}
        <rect y="60" width="${W}" height="14" fill="#15101f"/>${[200, 500, 800, 1100, 1400].map((x) => `<rect x="${x}" y="60" width="6" height="90" fill="#15101f"/>`).join("")}
        <path d="M0 60 L1600 60 M0 110 L1600 110" stroke="#2a2240" stroke-width="4"/>
        <rect x="360" y="70" width="60" height="120" fill="${tone("#8a3a5a", t)}" opacity=".8"/><rect x="1180" y="70" width="60" height="120" fill="${tone("#3a6aa8", t)}" opacity=".8"/>
        ${stands}
        ${beam(300, "#7a6aff", 260)}${beam(800, "#ffffff", 0)}${beam(1300, "#ff5ab4", -260)}
        <ellipse cx="800" cy="650" rx="330" ry="78" fill="${k.url("floor")}"/>
        <ellipse cx="800" cy="650" rx="330" ry="78" fill="none" stroke="${tone("#8a7aff", t)}" stroke-width="6" opacity="${(0.4 + 0.5 * k.light).toFixed(2)}"/>
        <ellipse cx="800" cy="650" rx="260" ry="60" fill="none" stroke="${tone("#c8b8ff", t)}" stroke-width="2" opacity=".5"/>
        ${k.glow("ring", 800, 650, 380, "#c8b8ff", 0.1 + 0.25 * k.light)}`;
    } },

    cave: { label: "Crystal cave", draw(k) {
      const crystal = (x, y, h, color) => `${k.glow(`c${x}`, x, y - h / 2, h, color, 0.5)}<polygon points="${x - h * 0.18},${y} ${x},${y - h} ${x + h * 0.18},${y}" fill="${color}" opacity=".9"/><polygon points="${x},${y} ${x},${y - h} ${x + h * 0.18},${y}" fill="#ffffff" opacity=".25"/>`;
      let drips = "";
      for (let x = 0; x < W; x += k.between(60, 140)) drips += `<polygon points="${x.toFixed(0)},0 ${(x + 50).toFixed(0)},0 ${(x + 25).toFixed(0)},${k.between(60, 200).toFixed(0)}" fill="#0c0a12"/>`;
      return `<defs>${k.radial("air", [[0, "#2a2a4a"], [1, "#07060c"]], 0.5, 0.55, 0.7)}</defs>${k.fill(k.url("air"))}
        ${drips}
        <path d="M0 900 V300 Q120 160 300 200 T560 120 L0 0 Z" fill="#0c0a12"/><path d="M1600 900 V320 Q1460 180 1300 240 T1020 110 L1600 0 Z" fill="#0c0a12"/>
        <ellipse cx="800" cy="820" rx="560" ry="60" fill="#14223a"/><ellipse cx="800" cy="820" rx="420" ry="34" fill="#3a6a9a" opacity=".3"/>
        ${crystal(300, 780, 220, "#5ae0ff")}${crystal(380, 790, 140, "#a07aff")}${crystal(1220, 780, 260, "#c87aff")}${crystal(1320, 800, 150, "#5ae0ff")}${crystal(700, 800, 110, "#7affd8")}
        <rect y="840" width="${W}" height="60" fill="#0a0810"/>${k.stars(30, 800, "#a8f0ff")}`;
    } },

    desert: { label: "Desert", draw(k) {
      return `<defs>${k.linear("sky", [[0, "#f6b25a"], [0.6, "#fbe0a0"], [1, "#fff2cc"]])}</defs>${k.fill(k.url("sky"))}
        ${k.glow("sun", 1040, 330, 420, "#fff6d8", 0.9)}<circle cx="1040" cy="330" r="120" fill="#fffaf0"/>
        ${k.ridge(600, 40, 140, "#e8b878")}${k.ridge(680, 40, 120, "#d89a5a")}${k.ridge(780, 30, 110, "#b8763e")}
        <g fill="#3a4a2a"><rect x="300" y="560" width="26" height="200" rx="13"/><rect x="262" y="610" width="20" height="70" rx="10"/><rect x="262" y="664" width="50" height="18" rx="9"/><rect x="342" y="590" width="20" height="60" rx="10"/><rect x="316" y="634" width="46" height="18" rx="9"/></g>`;
    } },

    lab: { label: "Laboratory", draw(k) {
      let floor = "";
      for (let i = -10; i <= 10; i++) floor += `<line x1="${800 + i * 60}" y1="620" x2="${800 + i * 260}" y2="900" stroke="#3affd8" stroke-width="2" opacity=".25"/>`;
      for (let y = 640; y < H; y += 40 + (y - 620) * 0.25) floor += `<line x1="0" y1="${y.toFixed(0)}" x2="${W}" y2="${y.toFixed(0)}" stroke="#3affd8" stroke-width="2" opacity=".2"/>`;
      let screen = "";
      for (let i = 0; i < 8; i++) screen += `<rect x="${(170 + k.between(0, 220)).toFixed(0)}" y="${250 + i * 26}" width="${k.between(60, 200).toFixed(0)}" height="8" rx="4" fill="#5affe0" opacity=".6"/>`;
      const tube = (x, color) => `<rect x="${x}" y="300" width="110" height="300" rx="55" fill="${color}" opacity=".25"/><rect x="${x + 8}" y="380" width="94" height="212" rx="47" fill="${color}" opacity=".45"/><rect x="${x - 10}" y="280" width="130" height="26" rx="6" fill="#20283a"/><rect x="${x - 10}" y="594" width="130" height="26" rx="6" fill="#20283a"/>${k.glow(`t${x}`, x + 55, 460, 200, color, 0.35)}`;
      return `<defs>${k.linear("wall", [[0, "#0a0f1c"], [1, "#141c2e"]])}</defs>${k.fill(k.url("wall"))}
        <rect x="140" y="220" width="480" height="270" rx="10" fill="#08202a" stroke="#2affd0" stroke-width="4" opacity=".9"/>${screen}
        ${tube(1000, "#5aff8a")}${tube(1200, "#5ad8ff")}${tube(1400, "#c87aff")}
        <rect y="610" width="${W}" height="290" fill="#060a14"/>${floor}`;
    } },

    shop: { label: "Card shop", draw(k) {
      // A card shop at a time: the shop is lit by its own lamps and sign, and the room darkens outside them at night.
      // Shelves of packs both sides, a sign, a glass case with cards, a wood floor and the counter in front.
      const t = k.time;
      const FOILS = ["#d8344a", "#2a6ad8", "#e8b030", "#7a3ad0", "#20a888", "#e85aa0", "#3a3a48", "#f07a2a"];
      const shelves = (x0, x1) => {
        let out = `<rect x="${x0 - 14}" y="120" width="${x1 - x0 + 28}" height="540" rx="6" fill="${tone("#2a1c16", t)}"/>`;
        for (let y = 150; y < 560; y += 116) {
          for (let x = x0; x < x1 - 40; x += 46) {
            const foil = tone(FOILS[Math.floor(k.r() * FOILS.length)], t);
            const lean = k.between(-3, 3).toFixed(1);
            out += `<g transform="rotate(${lean} ${x + 19} ${y + 92})"><rect x="${x}" y="${y + 22}" width="38" height="70" rx="3" fill="${foil}"/>`
              + `<rect x="${x}" y="${y + 22}" width="38" height="10" rx="2" fill="#fff" opacity=".35"/>`
              + `<rect x="${x + 6}" y="${y + 44}" width="26" height="26" rx="13" fill="#fff" opacity=".18"/></g>`;
          }
          out += `<rect x="${x0 - 14}" y="${y + 92}" width="${x1 - x0 + 28}" height="14" fill="${tone("#5a3a26", t)}"/>`;
        }
        return out;
      };
      let cards = "";
      for (let x = 560; x < 1020; x += 52) cards += `<rect x="${x}" y="${k.between(688, 700).toFixed(0)}" width="40" height="56" rx="3" fill="${tone(FOILS[Math.floor(k.r() * FOILS.length)], t)}" opacity=".85"/>`;
      return `<defs>${k.linear("wall", [[0, tone("#6a4a36", t)], [1, tone("#3a281e", t)]])}${k.linear("glass", [[0, "#cfe8f0", 0.35], [1, "#8ab0c0", 0.18]])}${k.linear("floor", [[0, tone("#5a3a26", t)], [1, tone("#2a1c12", t)]])}</defs>${k.fill(k.url("wall"))}
        ${shelves(70, 470)}${shelves(1130, 1530)}
        ${k.glow("sign", 800, 190, 260, "#ff5a8a", 0.1 + 0.3 * k.light)}
        <rect x="610" y="140" width="380" height="104" rx="16" fill="#1a1016" stroke="#ff7aa8" stroke-width="5"/>
        <text x="800" y="214" text-anchor="middle" font-family="Georgia, serif" font-size="70" font-weight="700" fill="#ffd2e2" letter-spacing="10">CARDS</text>
        ${props.pendant(k, 800, 40, "#ffe2a8")}${props.pendant(k, 300, 60, "#ffe2a8")}${props.pendant(k, 1300, 60, "#ffe2a8")}
        <rect y="760" width="${W}" height="140" fill="${k.url("floor")}"/><rect y="760" width="${W}" height="14" fill="${tone("#5a3a26", t)}"/>
        <rect x="520" y="660" width="560" height="110" rx="8" fill="${tone("#3a2a22", t)}"/>${cards}
        <rect x="520" y="660" width="560" height="110" rx="8" fill="${k.url("glass")}" stroke="#d8e8f0" stroke-opacity=".5" stroke-width="3"/>
        <rect x="500" y="650" width="600" height="16" rx="6" fill="${tone("#7a5238", t)}"/>
        <rect x="1000" y="610" width="60" height="50" rx="4" fill="#2a2a34"/><rect x="1010" y="620" width="40" height="18" fill="#7fd08a" opacity=".8"/>
        <rect x="200" y="600" width="90" height="160" fill="#2a1c12" opacity=".8"/><rect x="1400" y="620" width="120" height="140" fill="#2a1c12" opacity=".75"/>`;
    } },
  };

  // The light every place shares, laid over what its scene draws: a haze where the land meets the sky (depth), a
  // vignette so the edges fall away, and, given a time of day (0 morning, 1 noon, 2 evening, 3 night, as the town
  // counts them), that time's colour over the whole picture. Noon adds no colour; it's the picture as drawn.
  const TIMES = [
    { top: "#ffd9a8", topA: 0.08, bottom: "#fff1dc", bottomA: 0.03 },
    null,
    { top: "#ff7a3c", topA: 0.1, bottom: "#5a2a6a", bottomA: 0.12 },
    { top: "#060c30", topA: 0.3, bottom: "#050818", bottomA: 0.3 },
  ];
  function finish(k, body, time) {
    const tint = Number.isInteger(time) && TIMES[time] ? TIMES[time] : null;
    let out = body;
    out += `<defs>${k.linear("haze", [[0, "#ffffff", 0], [0.5, "#dfe8ff", 0.1], [1, "#ffffff", 0]])}</defs>`;
    out += `<rect y="${Math.round(H * 0.5)}" width="${W}" height="${Math.round(H * 0.22)}" fill="${k.url("haze")}"/>`;
    out += `<defs>${k.radial("vignette", [[0.55, "#000", 0], [1, "#000", 0.45]], 0.5, 0.5, 0.75)}</defs>${k.fill(k.url("vignette"))}`;
    if (tint) {
      out += `<defs>${k.linear("timeOfDay", [[0, tint.top, tint.topA], [1, tint.bottom, tint.bottomA]])}</defs>${k.fill(k.url("timeOfDay"))}`;
    }
    return out;
  }

  window.SceneBackdrops = {
    names: Object.keys(SCENES),
    label: (name) => (SCENES[name] || SCENES.default).label,
    // The SVG for a background, as markup; an unknown name draws the default. `time` (optional, 0 to 3) is the
    // time of day the place is seen at (see TIMES above); without it, the picture is drawn as it is.
    draw(name, time) {
      const scene = SCENES[name] || SCENES.default;
      const seed = [...(SCENES[name] ? name : "default")].reduce((sum, c) => sum * 31 + c.charCodeAt(0), 7);
      const k = kit(seed);
      // Without a time (the scene player), a picture is drawn at noon.
      const t = Number.isInteger(time) && time >= 0 && time <= 3 ? time : 1;
      k.time = t;
      k.light = LIGHT[t];
      return `<svg class="vn-bg-art" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">${finish(k, scene.draw(k), t)}</svg>`;
    },
  };
})();
