"""The minigames (docs/minigames-polish-plan.md) on the staff page: each game's start card with its rule, a moment of
play, and the frame holding it: nothing scrolls sideways, a canvas game's screen (and its touch buttons) sits wholly
inside the stage, and the text is readable in both themes. The card art doesn't load on the scratch database (the
cards' pictures are on the publisher's site), which doesn't matter for any of this."""
import harness

from . import DESKTOP, PHONE, check
from .theme import CONTRAST

# The theme check's contrast scan, over the minigame's stage only (the staff page around it is the site's).
STAGE_CONTRAST = CONTRAST.replace("createTreeWalker(document.body,", "createTreeWalker(document.querySelector('.minigame') || document.body,")
assert STAGE_CONTRAST != CONTRAST

GAMES = ["memory", "higher_lower", "cups", "invaders", "runner"]
PAGE = f"{harness.BASE}/dashboard/weiss/world/minigames/"

# Whether an element is wholly inside the stage's game area (not cut off by it).
INSIDE = r"""sel => { const area = document.querySelector('.minigame-area'); const el = document.querySelector(sel);
  if (!area || !el || !el.offsetParent) return null; const a = area.getBoundingClientRect(), r = el.getBoundingClientRect();
  return r.top >= a.top - 1 && r.bottom <= a.bottom + 1 && r.left >= a.left - 1 && r.right <= a.right + 1; }"""


def start(run, page, game):
    page.goto(PAGE)
    page.select_option("[data-minigame-game]", game)
    page.locator("form button[type=submit]", has_text="Play").first.click()
    card = run.visible(page.get_by_role("button", name="Start", exact=True), f"{game}: the start card's Start", page)
    rule = page.evaluate("() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim() === 'Start'); "
                         "const box = b && b.closest('div'); return box ? box.innerText : ''; }")
    run.expect(len(rule.strip()) > len("Start") + 10, f"{game}: the start card has no rule line ({rule!r})", page)
    card.click()


def play_a_moment(page, game, touch):
    if game in ("runner", "invaders"):
        page.wait_for_timeout(3400)  # the countdown
        for k in range(10):
            if touch:
                key = page.locator(".run-key-jump" if game == "runner" else ".inv-key").first
                if key.is_visible():
                    key.tap()
            else:
                page.keyboard.press("Space" if game == "runner" else ("ArrowLeft" if k % 2 else "ArrowRight"))
            page.wait_for_timeout(150)
    elif game == "memory":
        page.wait_for_timeout(500)
        tiles = page.locator(".minigame-area button")
        if tiles.count() >= 2:
            tiles.nth(0).click()
            page.wait_for_timeout(250)
            tiles.nth(1).click()
        page.wait_for_timeout(800)
    elif game == "higher_lower":
        page.wait_for_timeout(500)
        higher = page.get_by_role("button", name="Higher")
        if higher.count():
            higher.first.click()
        page.wait_for_timeout(1200)
    else:
        page.wait_for_timeout(2500)


@check("minigames")
def minigames(run):
    problems = []
    for scheme in ("dark", "light"):
        for viewport, tag, touch in ((DESKTOP, "desk", False), (PHONE, "phone", True)):
            page = run.page(viewport, touch=touch)
            page.emulate_media(color_scheme=scheme)
            for game in GAMES:
                start(run, page, game)
                play_a_moment(page, game, touch)
                where = f"{scheme} {tag} {game}"
                wide = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if wide > 1:
                    problems.append(f"{where}: the page scrolls sideways by {wide}px")
                for sel, what in ((".run-screen", "the runner's screen"), (".inv-screen", "Invaders' screen"),
                                  (".run-touch", "the runner's buttons"), (".inv-touch", "Invaders' buttons")):
                    if page.evaluate(INSIDE, sel) is False:
                        problems.append(f"{where}: {what} is cut off by the stage")
                low = page.evaluate(STAGE_CONTRAST)
                if low:
                    problems.append(f"{where}: text below AA contrast: {low[:3]}")
                if scheme == "dark":
                    run.shot(page, f"{tag}-{game}")
    run.expect(not problems, "\n".join(problems))


@check("minigame-end")
def minigame_end(run):
    """Memory played to its last pair: the end card shows, and the header pill doesn't still say whose turn it is or how
    many pairs are left (the shell clears the pill when a game ends)."""
    for viewport, tag, touch in ((DESKTOP, "desk", False), (PHONE, "phone", True)):
        page = run.page(viewport, touch=touch)
        start(run, page, "memory")
        page.wait_for_timeout(500)
        pill = page.locator(".minigame-pill")
        for _ in range(12):  # each pair: two taps on the same name, found by its name in the DOM
            if page.locator(".minigame-tile:not(.is-matched)").count() == 0:
                break
            page.wait_for_function("() => { const p = document.querySelector('.minigame-pill'); return !p || p.hidden || p.textContent.includes('Your turn') || !!document.querySelector('.minigame-over:not([hidden])'); }", timeout=20000)
            if page.locator(".minigame-over:not([hidden])").count():
                break
            pair = page.evaluate("""() => {
              const open = [...document.querySelectorAll('.minigame-tile:not(.is-matched)')];
              for (const t of open) {
                const name = t.querySelector('.minigame-tile-name').textContent;
                const twin = open.find((u) => u !== t && u.querySelector('.minigame-tile-name').textContent === name);
                if (twin) return [t.dataset.index, twin.dataset.index];
              }
              return null; }""")
            if not pair:
                break
            for index in pair:
                page.locator(f".minigame-tile[data-index='{index}']").click()
                page.wait_for_timeout(250)
            page.wait_for_timeout(700)
        run.visible(page.locator(".minigame-over:not([hidden])"), "the memory end card", page, 15000)
        # The end score counts up for 700 ms: wait for its final figures (all 8 pairs are the player's) before the shot.
        end_score = page.locator(".minigame-end-score b")
        try:
            page.wait_for_function("() => [...document.querySelectorAll('.minigame-end-score b')].map(b => b.textContent).join(' ') === '8 0'",
                                   timeout=5000)
        except Exception:
            shown = end_score.all_inner_texts()
            run.expect(False, f"the end score settles at {' — '.join(shown)}, not 8 — 0", page)
        run.expect(end_score.all_inner_texts() == ["8", "0"], f"the end score reads {end_score.all_inner_texts()}, not 8 and 0", page)
        run.shot(page, f"{tag}-memory-end")
        text = pill.inner_text() if pill.count() and pill.is_visible() else ""
        run.expect(text == "", f"the header still reads {text!r} after the game ended", page)
        run.no_overflow(page, f"the memory end at {viewport['width']}px")
        page.close()
