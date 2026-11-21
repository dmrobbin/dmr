"""The tutorial, played by clicking through the real pages in Edge, from a new save on the scratch database.

Each step is a player's action. A step that can't be done, or whose screen isn't what the tutorial says, stops the run
with the step's name, a screenshot in e2e/scratch/shots/, and the text on screen. Run: python e2e/tutorial.py
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout  # noqa: E402

import harness  # noqa: E402

SLOT = 1
DEBUG = "--probe" in sys.argv


class Stuck(Exception):
    pass


def expect_text(page, text, step):
    try:
        page.get_by_text(text).first.wait_for(timeout=8000)
    except PlaywrightTimeout as error:
        raise Stuck(f"{step}: expected on screen: {text!r}") from error


def advance_lines(page, step, limit=80):
    """Click through the guide's lines until the choices show. Stops with Stuck if they never do."""
    for _ in range(limit):
        if page.locator("[data-box]:not([hidden]) .town-option").count():
            return
        box = page.locator("[data-box]:not([hidden])")
        if box.count() == 0:
            raise Stuck(f"{step}: the message box closed before any choices showed")
        box.first.click()
        page.wait_for_timeout(250)
    raise Stuck(f"{step}: no choices after {limit} clicks")


def finish_lines(page, limit=80):
    """Click through lines until the message box closes, or until its choices show (then the box stays open)."""
    for _ in range(limit):
        if page.locator("[data-box]:not([hidden]) .town-option").count():
            return
        box = page.locator("[data-box]:not([hidden])")
        if box.count() == 0:
            return
        box.first.click()
        page.wait_for_timeout(250)


def choose(page, label, step):
    """Pick a talk option by its label, from the message box's choices."""
    option = page.locator("[data-box]:not([hidden]) .town-option", has_text=label)
    if option.count() == 0:
        shown = page.locator("[data-box]:not([hidden]) .town-option").all_inner_texts()
        raise Stuck(f"{step}: no {label!r} option; the choices are {shown}")
    option.first.click()
    page.wait_for_timeout(300)


def build_deck(page, climaxes=8, total=50):
    """Add copies with the + buttons: climaxes first, then characters, until the deck has `total` cards, at most 4 of
    any card. Stops with Stuck if the pool runs out."""
    def in_deck(kind):
        return sum(int(card.get_attribute("data-in-deck") or 0) for card in page.locator(f".pool-card[data-type='{kind}']").all())

    def add_one(kind):
        for card in page.locator(f".pool-card[data-type='{kind}']").all():
            pulled, used = int(card.get_attribute("data-pulled") or 0), int(card.get_attribute("data-in-deck") or 0)
            if pulled > used and used < 4:
                card.locator("button[data-delta='1']").click()
                page.wait_for_timeout(60)
                return True
        return False

    while in_deck("climax") < climaxes:
        if not add_one("climax"):
            raise Stuck(f"deck: only {in_deck('climax')} climaxes in the pool, {climaxes} needed")
    while in_deck("character") + in_deck("climax") < total:
        if not add_one("character"):
            raise Stuck(f"deck: only {in_deck('character') + in_deck('climax')} cards in the pool, {total} needed")

def open_packs(page):
    """Open every pack on the deck page, in the pack panel: the reveal, then its results. The reveal's animations are
    shortened (the site's reduced-motion setting) because the headless browser crashes under the full set."""
    page.emulate_media(reduced_motion="reduce")
    values = [int(v) for v in page.locator("[data-open-packs] select option").evaluate_all("els => els.map(e => e.value)")]
    # Eight packs (64 cards) is enough for a legal deck and light enough to animate: the smallest count of 8 or more.
    pick = min((v for v in values if v >= 8), default=max(values))
    page.locator("[data-open-packs] select").select_option(str(pick))
    page.locator("[data-open-packs] button[type=submit]").click()
    page.locator("[data-pack-sheet]:not([hidden])").wait_for(timeout=15000)
    for _ in range(400):  # 20 packs: each takes a click and a skip
        if page.locator("[data-pack-results]:not([hidden])").count():
            break
        skip = page.get_by_role("button", name="Skip to the end")
        if skip.count() and skip.first.is_visible():
            skip.first.click()
            page.wait_for_timeout(400)
            continue
        pack = page.locator("[data-pack-sheet] .pack-button:not([disabled])")
        if pack.count() == 0:
            page.wait_for_timeout(400)
            continue
        pack.first.click()
        page.wait_for_timeout(400)
    harness.shot(page, "12-packs-opened")
    print("opened packs in the panel")
    if page.locator("[data-pack-sheet] button", has_text="Close").count():
        page.locator("[data-pack-sheet] button", has_text="Close").first.click()


def play_memory(page, limit=120):
    """Play memory by clicks, as a player does: turn two tiles, keep a matching pair, and turn the rest back over when
    they don't match. Stops when the game's end screen shows (the result posts, and the page goes back to the town)."""
    def face_down():
        return page.locator(".minigame-tile[aria-label$='face down']")

    for _ in range(limit):
        if page.locator("text=You win!").count() or page.locator("text=wins").count() or page.url.endswith("/town/"):
            return
        tiles = face_down()
        if tiles.count() < 2:
            page.wait_for_timeout(400)
            continue
        first = tiles.nth(0)
        if DEBUG:
            print("probe", page.evaluate("() => ({nodes: document.getElementsByTagName('*').length, heap: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1e6) : null, face_down: document.querySelectorAll(\".minigame-tile[aria-label$='face down']\").length})"), flush=True)
        if DEBUG and tiles.count() == 2:
            print("last pair: clicking", flush=True)
        first.click()
        page.wait_for_timeout(500)
        remaining = face_down()  # after the first flip the second is picked again: on the last pair only one is left
        if remaining.count() == 0:
            page.wait_for_timeout(400)
            continue
        remaining.first.click()
        if DEBUG and tiles.count() <= 2:
            for tick in range(10):
                page.wait_for_timeout(400)
                print("after last pair", tick, page.url[-60:], flush=True)
        page.wait_for_timeout(900)
    raise Stuck("memory: the game didn't end")


def run(page):
    page.goto(f"{harness.BASE}/dashboard/weiss/world/{SLOT}/new/")
    page.get_by_role("button", name="Start with this set").click()
    page.wait_for_url(f"**/dashboard/weiss/world/{SLOT}/")
    harness.shot(page, "01-save-page")
    # The save page's way into the town: the link the tutorial highlights.
    page.get_by_role("link", name="Go to the town").click()
    page.wait_for_url(f"**/dashboard/weiss/world/{SLOT}/town/")
    harness.shot(page, "02-town-arrive")
    print("reached the town at the arrive step")
    # Arrive: the player approaches someone in the town to ask where they are (they become the guide).
    people = page.locator("[data-people] [data-cpu]")
    if people.count() == 0:
        raise Stuck("arrive: nobody to approach in the town")
    people.first.click()
    harness.shot(page, "03-approach")
    page.wait_for_timeout(3000)
    harness.shot(page, "04-after-approach")
    advance_lines(page, "approach")
    harness.shot(page, "05-guide-choices")
    choose(page, "Talk", "talk")
    advance_lines(page, "talk")
    harness.shot(page, "06-after-talk")
    print("talked to the guide")
    # Gift: give the guide a gift (the tutorial gives the player a starter gift to give).
    choose(page, "Give a gift", "gift")
    page.wait_for_timeout(300)
    gift = page.locator("[data-tutorial='gift-item']")
    if gift.count() == 0:
        raise Stuck("gift: no gift to give is highlighted")
    gift.first.click()
    finish_lines(page)
    harness.shot(page, "07-after-gift")
    print("gave a gift")
    # Map: open the map from the menu and go to the card shop.
    page.locator("[data-open-menu]").click()
    page.locator("[data-open-map]").click()
    shop = page.locator("[data-places] .town-place", has_text=re.compile("shop", re.I))
    if shop.count() == 0:
        shown = page.locator("[data-places] .town-place").all_inner_texts()
        raise Stuck(f"map: no card shop on the map ({shown})")
    shop.first.click()
    page.wait_for_timeout(500)
    harness.shot(page, "08-after-map")
    print("went to the map and the card shop")
    # Shop: open the counter, add a pack to the basket, check out.
    page.locator("[data-open-shop]").first.wait_for(state="visible", timeout=10000)
    # The counter's middle is under the guide's figure (FINDINGS.md 1): click its clear left side, as a player can.
    page.locator("[data-open-shop]").first.click(position={"x": 30, "y": 40})
    page.wait_for_timeout(400)
    add = page.locator("[data-tutorial='add-pack']")
    if add.count() == 0:
        raise Stuck("shop: no pack to add is highlighted")
    add.first.click()
    page.wait_for_timeout(300)
    page.locator("[data-checkout]").first.click()
    page.wait_for_timeout(1200)
    harness.shot(page, "09-after-checkout")
    print("bought a pack at the shop")
    # Back to the town, the quest log, then pass time.
    page.goto(f"{harness.BASE}/dashboard/weiss/world/{SLOT}/town/")
    page.locator("[data-open-menu]").click()
    page.locator("[data-quests]").click()
    page.wait_for_timeout(800)
    harness.shot(page, "10-quests")
    page.goto(f"{harness.BASE}/dashboard/weiss/world/{SLOT}/town/")
    page.locator("[data-wait]").first.click()
    page.wait_for_timeout(600)
    harness.shot(page, "11-after-wait")
    print("looked at the quests and passed time")
    # After passing time the tutorial asks where to go: the map, any place (staying put is an answer too).
    page.wait_for_timeout(500)
    chooser = page.locator("[data-places] .town-place:not([disabled])")
    if chooser.count() and chooser.first.is_visible():
        chooser.first.click()  # the chooser opens by itself after passing time
        page.wait_for_timeout(800)
    elif page.locator("[data-open-menu]").count():
        try:
            page.locator("[data-open-menu]").click(timeout=8000)
        except PlaywrightTimeout as error:
            harness.shot(page, "stuck-where-menu")
            on_top = page.locator("[data-open-menu]").evaluate("e => { const r = e.getBoundingClientRect(); const t = document.elementFromPoint(r.x + r.width/2, r.y + r.height/2); return t ? (t.tagName + '.' + t.className + ' ' + (t.innerText || '').slice(0, 60)) : 'nothing' }")
            raise Stuck(f"where to go: the Menu button can't be clicked; on top of it: {on_top}") from error
        page.locator("[data-open-map]").click()
        places = page.locator("[data-places] .town-place:not([disabled])")
        if places.count():
            places.first.click()
            page.wait_for_timeout(800)
    harness.shot(page, "11b-after-choosing-where")
    print("chose where to go")
    # Packs: open them on the save's page, in the pack panel.
    page.goto(f"{harness.BASE}/dashboard/weiss/world/{SLOT}/deck/")
    if page.locator("[data-open-packs]").count() == 0:
        print("no packs to open on the deck page: an earlier run opened them")
    else:
        open_packs(page)
    # Deck: 8 climaxes, then characters up to 50, at most 4 of any card. Each pool card's + adds one copy.
    build_deck(page)
    page.get_by_role("button", name="Save deck").click()
    page.wait_for_timeout(1200)
    harness.shot(page, "13-deck-saved")
    print("deck built and saved:", page.locator("[data-deck-total]").inner_text())
    # Back to the town: the guide should now ask the player to play a game (the step after the deck).
    page.goto(f"{harness.BASE}/dashboard/weiss/world/{SLOT}/town/")
    page.wait_for_timeout(800)
    harness.shot(page, "14-town-after-deck")
    print("tutorial goal now:", page.locator("[data-world-town]").inner_text()[:160].replace(chr(10), " | "))
    guide = page.locator("[data-people] [data-cpu]", has_text="Aang")
    if guide.count() == 0:
        raise Stuck("minigame: the guide isn't in the town")
    guide.first.click()
    page.wait_for_timeout(400)
    finish_lines(page)
    harness.shot(page, "15-guide-choices")
    options = page.locator("[data-box]:not([hidden]) .town-option").all_inner_texts()
    print("the guide's choices:", options)
    if any("Play a game" in text for text in options):
        if page.locator("[data-box]:not([hidden]) .town-option", has_text="Play a game").first.is_disabled():
            state = page.evaluate("""() => {
                const town = JSON.parse(document.getElementById('town-state').textContent);
                const guide = (town.people || []).find(p => p.name === 'Aang') || {};
                return {choose: town.choose, can_wait: town.can_wait, step: town.tutorial && town.tutorial.step, minigame: guide.minigame, hint: document.querySelector('[data-box]') && document.querySelector('[data-box]').innerText.slice(0, 120)};
            }""")
            raise Stuck(f"minigame: 'Play a game' is shown but disabled. Server says: {state}")
        choose(page, "Play a game", "minigame")
        page.wait_for_timeout(400)
        page.locator("input[name=game][value=memory]").first.click()
        page.locator("[data-pick-play]").first.click()
        page.wait_for_url("**/minigame/**", timeout=20000)
        page.locator(".minigame-tile").first.wait_for(timeout=20000)
        harness.shot(page, "16-memory-start")
        # A game counts only after 20 seconds (the server's minimum): a player takes at least that long, so the script does.
        page.wait_for_timeout(22000)
        play_memory(page)
        try:
            page.wait_for_url(f"**/dashboard/weiss/world/{SLOT}/town/**", timeout=30000)
        except PlaywrightTimeout as error:
            harness.shot(page, "stuck-memory-end")
            raise Stuck("memory: the game ended but the page didn't go back to the town: " + page.locator("body").inner_text()[:300].replace(chr(10), " | ")) from error
        page.wait_for_timeout(800)
        harness.shot(page, "17-after-minigame")
        print("played the minigame; back in the town")
        # The duel comes after the map: answer where to go (staying put is an answer), then challenge Aang.
        page.wait_for_timeout(800)
        chooser = page.locator("[data-places] .town-place:not([disabled])")
        if chooser.count() and chooser.first.is_visible():
            chooser.first.click()
            page.wait_for_timeout(800)
        guide = page.locator("[data-people] [data-cpu]", has_text="Aang")
        guide.first.click()
        page.wait_for_timeout(400)
        finish_lines(page)
        if not any("Duel" in text for text in page.locator("[data-box]:not([hidden]) .town-option").all_inner_texts()):
            raise Stuck("duel: no Duel choice from the guide: " + str(page.locator("[data-box]:not([hidden]) .town-option").all_inner_texts()))
        choose(page, "Duel", "duel")
        page.wait_for_timeout(1500)
        harness.shot(page, "18-duel-started")
        print("duel started: now at", page.url)
        return
    if not any("Play a game" in text for text in options):
        state = page.evaluate("""() => {
            const town = JSON.parse(document.getElementById('town-state').textContent);
            const guide = (town.people || []).find(p => p.name === 'Aang') || {};
            return {tutorial: town.tutorial, guide_minigame: guide.minigame, choose: town.choose, can_wait: town.can_wait};
        }""")
        raise Stuck(f"minigame: the guide's click plays the greeting and closes with no choices. Server says: {state}")
    return
    values = [int(v) for v in page.locator("[data-open-packs] select option").evaluate_all("els => els.map(e => e.value)")]
    # Eight packs (64 cards) is enough for a legal deck and light enough to animate: the smallest count of 8 or more.
    pick = min((v for v in values if v >= 8), default=max(values))
    page.locator("[data-open-packs] select").select_option(str(pick))
    page.locator("[data-open-packs] button[type=submit]").click()
    sheet = page.locator("[data-pack-sheet]:not([hidden])")
    sheet.wait_for(timeout=15000)
    page.wait_for_timeout(300)
    # Each click opens the next pack; the results show once they're all open.
    for _ in range(40):
        if page.locator("[data-pack-results]:not([hidden])").count():
            break
        skip = page.get_by_role("button", name="Skip to the end")
        if skip.count() and skip.first.is_visible():
            skip.first.click()  # the reveal's own skip: the rest of the packs open at once
            page.wait_for_timeout(600)
            continue
        pack = page.locator("[data-pack-sheet] .pack-button:not([disabled])")
        if pack.count() == 0:
            page.wait_for_timeout(600)
            continue
        pack.first.click()
        page.wait_for_timeout(900)
    try:
        page.locator("[data-pack-results]:not([hidden])").wait_for(timeout=30000)
    except PlaywrightTimeout as error:
        harness.shot(page, "stuck-packs")
        raise Stuck("packs: the pack didn't reveal its cards: " + page.locator("[data-pack-sheet]").inner_text()[:300].replace(chr(10), " | ")) from error
    harness.shot(page, "12-packs-opened")
    print("opened packs in the panel")
    # Deck: 8 climaxes, then characters up to 50, at most 4 of any card. Each pool card's + adds one copy.
    page.locator("[data-pack-sheet] button", has_text="Close").first.click()
    page.wait_for_timeout(300)
    build_deck(page)
    page.get_by_role("button", name="Save deck").click()
    page.wait_for_timeout(1200)
    harness.shot(page, "13-deck-saved")
    print("deck built and saved:", page.locator("[data-deck-total]").inner_text())


def main():
    harness.reset_saves()
    server = harness.server()
    try:
        with sync_playwright() as playwright:
            browser = harness.browser(playwright)
            page = browser.new_page(viewport={"width": 1100, "height": 800})
            page.on("pageerror", lambda error: print("PAGE ERROR:", str(error)[:300], flush=True))
            page.on("console", lambda message: print("CONSOLE", message.type, message.text[:200], flush=True) if message.type in ("error", "warning") else None)
            page.on("crash", lambda _: print("PAGE CRASHED", flush=True))
            page.on("response", lambda r: print("NOT FOUND", r.url[-30:], "on", r.frame.url[-50:], flush=True) if r.status == 404 else None)
            harness.login(page)
            try:
                run(page)
                print("PASS so far")
            except Stuck as stuck:
                harness.shot(page, "stuck")
                print("STUCK:", stuck)
                print("on screen:", page.url)
            finally:
                browser.close()
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
