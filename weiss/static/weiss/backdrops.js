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
      return `<defs>${k.linear("sky", [[0, "#3c5e3e"], [0.5, "#1d3a24"], [1, "#0a160d"]])}</defs>${k.fill(k.url("sky"))}
        ${k.shafts("light", "#f0ffd0", 5, 0.14)}
        ${k.pines(520, "#264a30", 30, 220, 340)}${k.pines(620, "#1a3622", 26, 260, 400)}${k.pines(740, "#0f2215", 20, 320, 520)}
        <rect y="800" width="${W}" height="100" fill="#08120a"/>
        ${k.stars(30, 820, "#f6ff9a")}`;
    } },

    void: { label: "Void", draw(k) {
      return `${k.fill("#000")}${k.glow("n1", 520, 380, 420, "#3a1a5a", 0.35)}${k.glow("n2", 1150, 560, 380, "#102a4a", 0.3)}${k.stars(60, H, "#b9a8ff")}`;
    } },

    city: { label: "City night", draw(k) {
      return `<defs>${k.linear("sky", [[0, "#05071a"], [0.6, "#1c1f4a"], [1, "#4a2a5e"]])}</defs>${k.fill(k.url("sky"))}
        ${k.stars(60, 300)}
        ${k.skyline(700, "#1e2148", "#7a86c8", 160, 380, 0.12)}
        ${k.glow("haze", 800, 760, 900, "#ff6ab4", 0.25)}
        ${k.skyline(820, "#0b0c1c", "#ffd889", 140, 470, 0.32)}
        <rect x="260" y="540" width="120" height="14" rx="7" fill="#ff4fa8" opacity=".85"/><rect x="1180" y="480" width="16" height="140" rx="8" fill="#4fe0ff" opacity=".8"/>
        <rect y="820" width="${W}" height="80" fill="#07070f"/>`;
    } },

    rooftop: { label: "Rooftop", draw(k) {
      let rail = "";
      for (let x = 0; x <= W; x += 46) rail += `<rect x="${x}" y="610" width="6" height="140" fill="#1a1520"/>`;
      return `<defs>${k.linear("sky", [[0, "#2a2350"], [0.55, "#a65a78"], [0.8, "#f2a36e"]])}</defs>${k.fill(k.url("sky"))}
        ${k.glow("sun", 520, 560, 300, "#ffc77a", 0.6)}
        ${k.skyline(640, "#4a2f52", "#ffd99a", 80, 300, 0.12)}
        <rect y="740" width="${W}" height="160" fill="#2a2430"/><rect y="740" width="${W}" height="6" fill="#3d3545"/>
        ${rail}<rect y="602" width="${W}" height="12" fill="#1a1520"/><rect y="672" width="${W}" height="6" fill="#1a1520"/>
        <g fill="#1a1520"><rect x="1240" y="380" width="170" height="150" rx="10"/><polygon points="1225,380 1425,380 1325,320"/><rect x="1258" y="530" width="10" height="210"/><rect x="1382" y="530" width="10" height="210"/><rect x="1258" y="600" width="134" height="8"/></g>`;
    } },

    rain: { label: "Rainy street", draw(k) {
      let reflections = "";
      for (let i = 0; i < 40; i++) {
        const x = k.between(0, W);
        reflections += `<rect x="${x.toFixed(0)}" y="${k.between(770, 800).toFixed(0)}" width="${k.between(6, 14).toFixed(0)}" height="${k.between(40, 110).toFixed(0)}" fill="${k.r() < 0.6 ? "#ffd889" : "#7fd0ff"}" opacity=".18"/>`;
      }
      return `<defs>${k.linear("sky", [[0, "#1a2130"], [1, "#3a4558"]])}${k.linear("street", [[0, "#2a3242"], [1, "#0e1118"]])}</defs>${k.fill(k.url("sky"))}
        ${k.skyline(760, "#232a3a", "#e8c880", 220, 520, 0.28)}
        <rect y="760" width="${W}" height="140" fill="${k.url("street")}"/>${reflections}
        <g fill="#10131a"><rect x="1150" y="380" width="12" height="390"/><path d="M1156 386 q70 -40 120 10" stroke="#10131a" stroke-width="10" fill="none"/><rect x="1252" y="392" width="44" height="18" rx="6"/></g>
        ${k.glow("lamp", 1274, 430, 200, "#ffdc9a", 0.55)}
        ${k.rain(220)}`;
    } },

    sakura: { label: "Cherry blossoms", draw(k) {
      let blossoms = "";
      const clusters = [[180, 140], [320, 90], [470, 160], [260, 260], [600, 110], [720, 190], [90, 300], [420, 300]];
      for (const [cx, cy] of clusters) {
        for (let i = 0; i < 26; i++) blossoms += `<circle cx="${(cx + k.between(-80, 80)).toFixed(0)}" cy="${(cy + k.between(-50, 50)).toFixed(0)}" r="${k.between(14, 34).toFixed(0)}" fill="${["#ffc4d6", "#ffb0c8", "#ffd8e4", "#f79ab8"][Math.floor(k.r() * 4)]}" opacity=".9"/>`;
      }
      return `<defs>${k.linear("sky", [[0, "#9ec8ec"], [0.7, "#f6dcea"], [1, "#fbe9ef"]])}</defs>${k.fill(k.url("sky"))}
        ${k.clouds(4, 120, 300, "#ffffff", 0.6)}
        ${k.ridge(620, 30, 90, "#c6b4d0")}${k.ridge(700, 25, 80, "#a7c49a")}<rect y="760" width="${W}" height="140" fill="#8fb37f"/>
        <path d="M-20 900 C 60 700, 60 520, 140 420 S 300 220, 520 150 M140 420 C 220 380, 300 360, 420 300 M90 560 C 40 480, 10 420, -20 380" stroke="#4a2f2a" stroke-width="34" fill="none" stroke-linecap="round"/>
        ${blossoms}
        ${k.drifting(60, () => `<ellipse rx="7" ry="4" fill="${k.r() < 0.5 ? "#ffb7cc" : "#ffd3df"}" transform="rotate(${k.between(0, 180).toFixed(0)})"/>`, "fall")}`;
    } },

    shrine: { label: "Shrine", draw(k) {
      const lantern = (x) => `${k.glow(`l${x}`, x, 600, 110, "#ffb35a", 0.55)}<rect x="${x - 18}" y="572" width="36" height="56" rx="10" fill="#ffcf7a"/><rect x="${x - 22}" y="566" width="44" height="8" fill="#3a1e14"/><rect x="${x - 4}" y="628" width="8" height="150" fill="#3a2a24"/>`;
      return `<defs>${k.linear("sky", [[0, "#271c4a"], [0.55, "#8a4a6c"], [0.85, "#f0a070"]])}${k.linear("path", [[0, "#5a4a52"], [1, "#2a2026"]])}</defs>${k.fill(k.url("sky"))}
        ${k.stars(40, 240)}${k.pines(640, "#2a1a2e", 24, 260, 420)}
        <rect y="720" width="${W}" height="180" fill="#21161e"/><polygon points="700,720 900,720 1100,900 500,900" fill="${k.url("path")}"/>
        <g fill="#c8322a"><rect x="610" y="300" width="36" height="430"/><rect x="954" y="300" width="36" height="430"/><rect x="560" y="360" width="480" height="26"/>
          <path d="M520 262 Q800 300 1080 262 L1092 236 Q800 274 508 236 Z"/></g><rect x="508" y="226" width="584" height="14" fill="#1e1012" rx="4"/>
        <rect x="770" y="386" width="60" height="70" fill="#1e1012"/>
        ${lantern(470)}${lantern(1130)}
        ${k.stars(26, 700, "#ffe08a")}`;
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
      return `<defs>${k.linear("sky", [[0, "#3aa0e8"], [1, "#c9ecff"]])}${k.linear("sea", [[0, "#22a8c8"], [1, "#0a6a9a"]])}${k.linear("sand", [[0, "#f6e2b0"], [1, "#e2c48a"]])}</defs>
        ${k.fill(k.url("sky"))}${k.glow("sun", 360, 150, 220, "#fffbe0", 0.85)}<circle cx="360" cy="150" r="60" fill="#fffde8"/>
        ${k.clouds(5, 160, 360, "#ffffff", 0.85)}
        <rect y="500" width="${W}" height="220" fill="${k.url("sea")}"/>
        <path d="M0 700 Q200 680 400 700 T800 700 T1200 700 T1600 700 L1600 900 L0 900 Z" fill="${k.url("sand")}"/>
        <path d="M0 704 Q200 684 400 704 T800 704 T1200 704 T1600 704" stroke="#ffffff" stroke-width="6" fill="none" opacity=".8"/>
        <g fill="#2f4a2a"><path d="M1290 900 C1300 760, 1320 620, 1370 470" stroke="#5a4030" stroke-width="22" fill="none"/>
          <path d="M1370 470 q-120 -40 -220 40 q110 -20 220 -40"/><path d="M1370 470 q100 -70 220 -20 q-110 -10 -220 20"/><path d="M1370 470 q-40 -110 -150 -130 q80 40 150 130"/><path d="M1370 470 q60 -110 160 -110 q-90 30 -160 110"/><path d="M1370 470 q-130 30 -170 140 q50 -90 170 -140"/></g>`;
    } },

    space: { label: "Space", draw(k) {
      return `${k.fill("#03030a")}${k.glow("n1", 420, 300, 520, "#6a2a8a", 0.4)}${k.glow("n2", 1100, 220, 460, "#1a6a8a", 0.35)}${k.glow("n3", 800, 700, 500, "#8a2a5a", 0.25)}
        ${k.stars(260, H)}
        <defs>${k.radial("planet", [[0, "#f0b878"], [0.6, "#b0603a"], [1, "#3a1a1a"]], 0.35, 0.3, 0.8)}</defs>
        <ellipse cx="1220" cy="640" rx="330" ry="60" fill="none" stroke="#e8c8a0" stroke-width="10" opacity=".5" transform="rotate(-14 1220 640)"/>
        <circle cx="1220" cy="640" r="190" fill="${k.url("planet")}"/>
        <path d="M 900 720 A 330 60 -14 0 0 1540 560" fill="none" stroke="#f2d8b8" stroke-width="10" opacity=".75" transform="rotate(0)"/>
        <circle cx="380" cy="180" r="34" fill="#c8ccd8"/><circle cx="372" cy="172" r="34" fill="#03030a" opacity=".55"/>`;
    } },

    ruins: { label: "Ruins", draw(k) {
      let columns = "";
      for (const [x, h] of [[220, 380], [420, 250], [1100, 330], [1320, 420], [760, 160]]) {
        const top = 760 - h;
        columns += `<rect x="${x}" y="${top}" width="70" height="${h}" fill="#3a3036"/><polygon points="${x},${top} ${x + 22},${top - 26} ${x + 40},${top - 6} ${x + 58},${top - 34} ${x + 70},${top}" fill="#3a3036"/>
          <rect x="${x + 14}" y="${top}" width="6" height="${h}" fill="#2a2228"/><rect x="${x + 44}" y="${top}" width="6" height="${h}" fill="#2a2228"/>`;
      }
      return `<defs>${k.linear("sky", [[0, "#2a1a20"], [0.6, "#7a3a2a"], [1, "#c8603a"]])}</defs>${k.fill(k.url("sky"))}
        ${k.clouds(8, 100, 500, "#1a1014", 0.5)}${k.glow("fire", 800, 760, 600, "#ff7a3a", 0.35)}
        ${columns}<rect x="560" y="560" width="340" height="40" fill="#3a3036" transform="rotate(-8 730 580)"/>
        ${k.ridge(780, 30, 50, "#1e161a", false)}
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
      let desks = "";
      for (let row = 0; row < 2; row++) {
        for (let i = 0; i < 5; i++) {
          const x = 120 + i * 300 + row * 60;
          const y = 720 + row * 90;
          desks += `<rect x="${x}" y="${y}" width="200" height="22" rx="4" fill="#6a4a30"/><rect x="${x + 16}" y="${y + 22}" width="10" height="90" fill="#3a3a40"/><rect x="${x + 174}" y="${y + 22}" width="10" height="90" fill="#3a3a40"/>`;
        }
      }
      let chalk = "";
      for (let i = 0; i < 9; i++) chalk += `<path d="M${(560 + k.between(0, 520)).toFixed(0)} ${(260 + i * 34).toFixed(0)} q30 ${k.between(-10, 10).toFixed(0)} ${k.between(60, 240).toFixed(0)} 0" stroke="#e8f0e8" stroke-width="4" fill="none" opacity=".45" stroke-linecap="round"/>`;
      return `<defs>${k.linear("wall", [[0, "#efe4cc"], [1, "#d6c6a6"]])}${k.linear("sky", [[0, "#7ab8e8"], [1, "#d8eefa"]])}</defs>${k.fill(k.url("wall"))}
        <rect y="660" width="${W}" height="240" fill="#a4774a"/><rect y="660" width="${W}" height="10" fill="#7a5434"/>
        <g><rect x="40" y="150" width="380" height="430" fill="${k.url("sky")}"/>${k.clouds(2, 260, 380, "#ffffff", 0.8, 120, 300)}
          <rect x="40" y="150" width="380" height="430" fill="none" stroke="#f6f0e2" stroke-width="16"/><rect x="222" y="150" width="16" height="430" fill="#f6f0e2"/><rect x="40" y="355" width="380" height="16" fill="#f6f0e2"/></g>
        ${k.shafts("sun", "#fff6d0", 2, 0.16)}
        <rect x="520" y="210" width="620" height="330" fill="#2c4a3a"/><rect x="520" y="210" width="620" height="330" fill="none" stroke="#8a6440" stroke-width="16"/>${chalk}
        <rect x="520" y="546" width="620" height="14" fill="#8a6440"/>
        <circle cx="1330" cy="230" r="54" fill="#f8f4ea" stroke="#5a4a3a" stroke-width="8"/><path d="M1330 230 V196 M1330 230 L1356 244" stroke="#3a3030" stroke-width="6" stroke-linecap="round"/>
        ${desks}`;
    } },

    cafe: { label: "Café", draw(k) {
      let shelf = "";
      for (let i = 0; i < 14; i++) shelf += `<rect x="${1140 + i * 30}" y="${k.between(300, 316).toFixed(0)}" width="22" height="${k.between(24, 40).toFixed(0)}" rx="4" fill="${["#e8d8c0", "#8a5a3a", "#c84a3a", "#3a6a5a"][Math.floor(k.r() * 4)]}"/>`;
      let blur = "";
      for (let i = 0; i < 18; i++) blur += `<circle cx="${k.between(140, 860).toFixed(0)}" cy="${k.between(260, 540).toFixed(0)}" r="${k.between(10, 34).toFixed(0)}" fill="${k.r() < 0.5 ? "#ffd38a" : "#ff9a6a"}" opacity=".35"/>`;
      const lamp = (x) => `<line x1="${x}" y1="0" x2="${x}" y2="170" stroke="#2a1a12" stroke-width="4"/><path d="M${x - 46} 220 q46 -60 92 0 Z" fill="#3a2218"/>${k.glow(`lamp${x}`, x, 230, 170, "#ffcf8a", 0.6)}<circle cx="${x}" cy="226" r="14" fill="#fff0c0"/>`;
      return `<defs>${k.linear("wall", [[0, "#5a3a28"], [1, "#2e1c14"]])}${k.linear("out", [[0, "#2a2a4a"], [1, "#5a4a5a"]])}</defs>${k.fill(k.url("wall"))}
        <rect x="120" y="230" width="760" height="350" fill="${k.url("out")}"/>${blur}
        <rect x="120" y="230" width="760" height="350" fill="none" stroke="#2a1810" stroke-width="18"/><rect x="492" y="230" width="16" height="350" fill="#2a1810"/>
        <rect x="1120" y="356" width="440" height="12" fill="#2a1810"/>${shelf}
        ${lamp(380)}${lamp(800)}${lamp(1240)}
        <rect y="640" width="${W}" height="260" fill="#3a2418"/><rect y="640" width="${W}" height="26" fill="#6a4228"/>
        <rect x="1000" y="580" width="40" height="60" rx="6" fill="#e8e0d0"/><rect x="1060" y="596" width="30" height="44" rx="6" fill="#e8e0d0"/>`;
    } },

    library: { label: "Library", draw(k) {
      const shelves = (x0, x1) => {
        let out = `<rect x="${x0}" y="80" width="${x1 - x0}" height="680" fill="#2a1a12"/>`;
        for (let y = 120; y < 740; y += 120) {
          let x = x0 + 16;
          while (x < x1 - 30) {
            const w = k.between(12, 26);
            const h = k.between(70, 100);
            out += `<rect x="${x.toFixed(0)}" y="${(y + 100 - h).toFixed(0)}" width="${(w - 2).toFixed(0)}" height="${h.toFixed(0)}" fill="${["#7a2a2a", "#2a4a6a", "#3a5a3a", "#8a6a3a", "#5a3a5a", "#a08060"][Math.floor(k.r() * 6)]}"/>`;
            x += w;
          }
          out += `<rect x="${x0}" y="${y + 100}" width="${x1 - x0}" height="14" fill="#4a2e1e"/>`;
        }
        return out;
      };
      return `<defs>${k.linear("wall", [[0, "#2a1c16"], [1, "#140c0a"]])}${k.linear("win", [[0, "#1a2a5a"], [1, "#4a5a8a"]])}</defs>${k.fill(k.url("wall"))}
        <path d="M620 700 V260 a180 180 0 0 1 360 0 V700 Z" fill="${k.url("win")}"/>${k.stars(20, 500, "#fff", 640, 960)}
        <path d="M620 700 V260 a180 180 0 0 1 360 0 V700 Z M800 80 V700 M620 420 H980" fill="none" stroke="#3a2418" stroke-width="16"/>
        ${k.shafts("moon", "#c8d4ff", 1, 0.1)}
        ${shelves(40, 560)}${shelves(1040, 1560)}
        <rect y="760" width="${W}" height="140" fill="#3a2418"/>${k.glow("lamp", 330, 800, 300, "#ffc070", 0.35)}`;
    } },

    arena: { label: "Arena", draw(k) {
      const beam = (x, color, tilt) => `<defs>${k.linear(`b${x}`, [[0, color, 0.55], [1, color, 0]])}</defs><polygon points="${x - 20},0 ${x + 20},0 ${x + tilt + 220},760 ${x + tilt - 220},760" fill="${k.url(`b${x}`)}"/>`;
      let crowd = "";
      for (let x = -20; x < W + 40; x += 34) crowd += `<circle cx="${(x + k.between(-6, 6)).toFixed(0)}" cy="${(800 + k.between(-14, 10)).toFixed(0)}" r="${k.between(18, 24).toFixed(0)}" fill="#07060c"/>`;
      return `<defs>${k.linear("sky", [[0, "#05040c"], [1, "#1a1030"]])}</defs>${k.fill(k.url("sky"))}
        ${k.stars(80, 560, "#ffffff")}
        ${beam(300, "#7a6aff", 260)}${beam(800, "#ffffff", 0)}${beam(1300, "#ff5ab4", -260)}
        <rect x="200" y="620" width="1200" height="40" fill="#2a2440"/><rect x="200" y="620" width="1200" height="6" fill="#8a7aff" opacity=".7"/>
        ${k.glow("stage", 800, 640, 520, "#c8b8ff", 0.3)}
        ${crowd}<rect y="810" width="${W}" height="90" fill="#07060c"/>`;
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
  };

  window.SceneBackdrops = {
    names: Object.keys(SCENES),
    label: (name) => (SCENES[name] || SCENES.default).label,
    // The SVG for a background, as markup; an unknown name draws the default.
    draw(name) {
      const scene = SCENES[name] || SCENES.default;
      const seed = [...(SCENES[name] ? name : "default")].reduce((sum, c) => sum * 31 + c.charCodeAt(0), 7);
      return `<svg class="vn-bg-art" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">${scene.draw(kit(seed))}</svg>`;
    },
  };
})();
