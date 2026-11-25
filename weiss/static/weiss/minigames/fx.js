/* The minigames' shared effects (docs/minigames-polish-plan.md, "Shared effects"): a particle burst, a shake and a floating
   "+10" pop, drawn on the stage's effects layer. MinigameFx.create(layer) gives { burst, shake, pop, clear }; the frame
   passes it to a game as ctx.fx. Coordinates are page coordinates (what getBoundingClientRect and the pointer give), and
   everything honours reduced motion: a burst does nothing, a shake does nothing, and a pop is shown without moving. */
(() => {
  const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const DEFAULT_COLORS = ["#d4af37", "#e6c35c", "#fff4cc"];

  // A page point as a point in the layer.
  function local(layer, x, y) {
    const box = layer.getBoundingClientRect();
    return { x: x - box.left, y: y - box.top };
  }

  // Sparks fly out from (x, y) and fade. options: count (12), colors, distance (px, 70), duration (ms, 600).
  function burst(layer, x, y, options = {}) {
    if (reducedMotion()) return;
    const count = options.count ?? 12;
    const colors = options.colors?.length ? options.colors : DEFAULT_COLORS;
    const distance = options.distance ?? 70;
    const duration = options.duration ?? 600;
    const at = local(layer, x, y);
    for (let i = 0; i < count; i++) {
      const spark = document.createElement("span");
      spark.className = "minigame-spark";
      spark.style.left = `${at.x}px`;
      spark.style.top = `${at.y}px`;
      spark.style.background = colors[i % colors.length];
      layer.append(spark);
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.4;
      const reach = distance * (0.6 + Math.random() * 0.6);
      const dx = Math.cos(angle) * reach;
      const dy = Math.sin(angle) * reach;
      const animation = spark.animate(
        [
          { transform: "translate(-50%, -50%) scale(1)", opacity: 1 },
          { transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(0.2)`, opacity: 0 },
        ],
        { duration, easing: "cubic-bezier(.2,.7,.3,1)", fill: "forwards" },
      );
      animation.onfinish = () => spark.remove();
    }
  }

  // The element shakes from side to side: a miss, a hit.
  function shake(el, options = {}) {
    if (!el || reducedMotion() || !el.animate) return;
    el.animate(
      [
        { transform: "translate(0, 0)" },
        { transform: "translate(-6px, 0)" },
        { transform: "translate(5px, 0)" },
        { transform: "translate(-3px, 1px)" },
        { transform: "translate(2px, 0)" },
        { transform: "translate(0, 0)" },
      ],
      { duration: options.duration ?? 320, easing: "linear" },
    );
  }

  // A short text, such as "+10", floats up from (x, y) and fades (it just shows, with reduced motion).
  function pop(layer, x, y, text, options = {}) {
    const at = local(layer, x, y);
    const node = document.createElement("span");
    node.className = `minigame-pop${options.tone ? ` minigame-pop-${options.tone}` : ""}`;
    node.textContent = text;
    node.style.left = `${at.x}px`;
    node.style.top = `${at.y}px`;
    layer.append(node);
    const duration = options.duration ?? 800;
    if (reducedMotion() || !node.animate) {
      setTimeout(() => node.remove(), duration);
      return;
    }
    const animation = node.animate(
      [
        { transform: "translate(-50%, -50%)", opacity: 1 },
        { transform: "translate(-50%, calc(-50% - 2.4rem))", opacity: 0 },
      ],
      { duration, easing: "ease-out", fill: "forwards" },
    );
    animation.onfinish = () => node.remove();
  }

  function create(layer) {
    return {
      burst: (x, y, options) => burst(layer, x, y, options),
      shake: (el, options) => shake(el, options),
      pop: (x, y, text, options) => pop(layer, x, y, text, options),
      clear: () => layer.replaceChildren(),
    };
  }

  window.MinigameFx = { create };
})();
