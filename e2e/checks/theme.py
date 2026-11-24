"""The light theme (docs/round-two-plan.md, item 5): the header's choice of System, Light or Dark, kept on reload with
no flash, text contrast in both themes on the site's pages, and the duel board staying dark."""
import harness

from . import DESKTOP, PHONE, check, db, open_duel_in_town, town_url
from .duel import MUSIC_OFF

PAGES = ["/dashboard/weiss/profile/", "/dashboard/weiss/lists/", "/dashboard/weiss/world/1/people/", "/dashboard/weiss/play/",
         "/dashboard/weiss/", "/dashboard/weiss/arcade/", "/dashboard/weiss/world/", "/dashboard/weiss/world/1/quests/"]

# WCAG contrast of each text's colour against the first solid background behind it; the worst few for a page.
CONTRAST = r"""() => {
  const parse = (c) => { const m = c.match(/[\d.]+/g); return m ? m.map(Number) : [0, 0, 0, 0]; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
  // The first solid background behind it; null when an image or gradient is in the way (its colour can't be judged).
  const behind = (el) => { for (; el; el = el.parentElement) { const s = getComputedStyle(el); const c = parse(s.backgroundColor);
    if (c.length < 4 || c[3] >= .95) return c; if (s.backgroundImage !== 'none') return null; }
    return parse(getComputedStyle(document.body).backgroundColor); };
  const worst = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node; (node = walker.nextNode());) {
    const el = node.parentElement; const text = node.textContent.trim();
    if (!text || !el || !el.offsetParent || el.closest('[hidden],[aria-hidden=true],.sr-only,svg,select,option')) continue;
    const s = getComputedStyle(el); if (+s.opacity < .9 || s.visibility !== 'visible') continue;
    if (el.closest('button:disabled,[aria-disabled=true]')) continue;  // disabled controls are exempt
    const fg = parse(s.color), bg = behind(el);
    if (!bg) continue;
    const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
    const ratio = (a + .05) / (b + .05);
    const large = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.6 && +s.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5)) worst.push([Math.round(ratio * 100) / 100, text.slice(0, 40), el.className.toString().slice(0, 40)]);
  }
  return worst.sort((x, y) => x[0] - y[0]).slice(0, 10);
}"""


def background(page):
    return page.evaluate("() => getComputedStyle(document.body).backgroundColor")


@check("theme")
def theme(run):
    db("save", "people")
    db("record")  # the profile's recent games, won and lost
    problems = []
    for scheme in ("light", "dark"):  # the device's setting, with no choice saved
        page = run.page(DESKTOP)
        page.emulate_media(color_scheme=scheme)
        for path in PAGES:
            page.goto(harness.BASE + path)
            low = page.evaluate(CONTRAST)
            if low:
                problems.append(f"{scheme}, {path}: {low}")
                run.shot(page, f"low-contrast-{scheme}-{path.strip('/').split('/')[-1]}")
        run.shot(page, f"system-{scheme}")
    run.expect(not problems, "text below WCAG AA contrast ([ratio, text, class]):\n" + "\n".join(problems))

    # Choosing Light on a dark device: applied at once, kept on reload, and set before the first paint.
    page = run.page(PHONE)
    page.emulate_media(color_scheme="dark")
    page.goto(harness.BASE + PAGES[0])
    dark = background(page)
    page.locator(".theme-menu summary").click()
    page.get_by_label("Light").check()
    run.expect(background(page) != dark, "choosing Light didn't change the page", page)
    page.add_init_script("document.addEventListener('DOMContentLoaded', () => { window.__themeAtReady = document.documentElement.dataset.theme; })")
    page.reload()
    run.expect(page.evaluate("() => window.__themeAtReady") == "light", "Light isn't applied before the page is ready (it would flash)", page)
    run.expect(page.get_by_label("Light").is_checked(), "the menu doesn't show Light as chosen after a reload", page)
    run.no_overflow(page, "the profile at 390px in the light theme")
    run.shot(page, "chosen-light-phone")
    page.locator(".theme-menu summary").click()
    page.get_by_label("System").check()
    run.expect(background(page) == dark and page.evaluate("() => !document.documentElement.hasAttribute('data-theme')"),
               "System didn't hand the choice back to the device", page)

    # Light everywhere around it, the duel board stays dark.
    db("duel")
    page = run.page(DESKTOP, init_script=MUSIC_OFF + "try { localStorage.setItem('site-theme', 'light'); } catch (e) {}")
    frame = open_duel_in_town(run, page)
    page.frame_locator(".town-play-frame").get_by_role("button", name="Begin").click()
    page.wait_for_timeout(1500)
    board = frame.evaluate(r"""() => { const el = document.querySelector('.play-board'); let c;
      for (let e = el; e; e = e.parentElement) { c = getComputedStyle(e).backgroundColor; if (!/rgba\(0, 0, 0, 0\)|transparent/.test(c)) break; }
      const m = c.match(/\d+/g).map(Number); return (m[0] + m[1] + m[2]) / 3; }""")
    run.expect(board < 80, f"the duel board isn't dark in the light theme (brightness {board:.0f})", page)
    low = frame.evaluate(CONTRAST)  # the board is pinned dark: the light theme's colours mustn't leak into it
    run.expect(not low, f"light theme, the duel (rock, paper, scissors): text below WCAG AA contrast: {low}", page)
    run.shot(page, "duel-light")
    page.goto(town_url())
    run.shot(page, "town-light")
