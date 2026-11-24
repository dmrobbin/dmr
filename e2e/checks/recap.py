"""The duel recap (docs/round-two-plan.md, item 1): its moments at the top of "How the game went" after a town duel
(shown once the results ceremony is done), and the Recap disclosure on the profile's recent games."""
import harness

from . import DESKTOP, PHONE, check, db, open_duel_in_town
from .duel import MUSIC_OFF


@check("recap")
def recap(run):
    db("save", "duel", "played")
    page = run.page(DESKTOP, init_script=MUSIC_OFF)
    frame = open_duel_in_town(run, page)
    layer = page.frame_locator(".town-play-frame")
    run.visible(layer.get_by_role("button", name="Begin"), "Begin", page).click()
    page.wait_for_timeout(800)
    db("finish")
    over = run.visible(layer.locator(".game-over"), "the game-over screen", page, 15000)
    opener = layer.locator("[data-summary-open]")
    page.wait_for_timeout(300)
    run.expect(not opener.is_visible(), "'How the game went' shows while the ceremony is still playing", page)
    over.click(position={"x": 10, "y": 10})  # the ceremony, all at once
    run.visible(opener, "'How the game went' once the ceremony is done", page).click()
    panel = run.visible(layer.locator("[data-summary]"), "the summary panel", page)
    text = panel.inner_text()
    run.expect("behind" in text.lower() or "fought back" in text.lower(), f"no comeback moment in the summary: {text[:300]!r}", page)
    run.expect("Turn 4" in text and "5" in text, "no big-hit moment (turn 4, 5 damage)", page)
    run.expect(panel.locator("svg").count() >= 1, "no graph in the summary", page)
    focused = frame.evaluate("() => document.activeElement && document.activeElement.textContent.trim()")
    run.expect(focused == "Close", f"opening the summary put focus on {focused!r}", page)
    run.shot(page, "summary")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    run.expect(not panel.is_visible(), "Escape didn't close the summary", page)

    db("record")
    for viewport, tag in ((DESKTOP, "desk"), (PHONE, "phone")):
        page = run.page(viewport)
        page.goto(f"{harness.BASE}/dashboard/weiss/profile/")
        toggles = page.locator("[data-recap-toggle]")
        run.expect(toggles.count() == 1, f"{toggles.count()} Recap buttons: the game with a recap should have one, the older game none", page)
        toggle = toggles.first
        toggle.scroll_into_view_if_needed()
        toggle.click()
        run.expect(toggle.get_attribute("aria-expanded") == "true", "the Recap button doesn't say it's open", page)
        body = run.visible(page.locator(f"#{toggle.get_attribute('aria-controls')}"), "the recap under the game", page)
        run.expect(body.locator("svg").count() >= 1, "no graph in the profile's recap", page)
        run.expect("fought back" in body.inner_text().lower() or "behind" in body.inner_text().lower(), "the profile's recap has no comeback line", page)
        run.no_overflow(page, f"the profile with a recap open at {viewport['width']}px")
        run.shot(page, f"profile-{tag}")
        toggle.click()
        run.expect(body.is_hidden(), "the Recap button doesn't close it again", page)
