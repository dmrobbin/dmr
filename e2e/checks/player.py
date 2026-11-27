"""A regular player, not staff (docs/world-release-plan.md, item A): with world mode closed they see no World tab and are sent
away from it; once staff open it, they can start a save, reach the town, leave a report, and get nothing staff-only. The
on switch is set by staff, as a real release would be, and put back as it was afterwards."""
import harness

from . import DESKTOP, PHONE, check, db, town_url
from .report import open_report

PLAYER = "e2e-player"  # db.py's player command makes this user
PLAYER_PASSWORD = "e2e-player-pass"
CLOSED_MESSAGE = "World mode isn't open yet. It's coming soon!"
REPORT_TEXT = "Player check: the town's menu opened, and this report went in as a player."
STAFF_ONLY = ".town-staff:visible, [data-test-mode]:visible, [data-staff-wait]:visible, [data-jump]:visible"


def dashboard(path=""):
    return f"{harness.BASE}/dashboard/weiss/{path}"


def login_as_player(run, viewport):
    """A fresh window, signed in as the test player (not staff)."""
    page = run.page(viewport, login=False)
    page.goto(f"{harness.BASE}/login/")
    page.fill("input[name=username]", PLAYER)
    page.fill("input[name=password]", PLAYER_PASSWORD)
    page.click("button[type=submit], input[type=submit]")
    page.wait_for_load_state()
    return page


def switch_is_open(staff):
    return staff.locator("[data-open-status]").inner_text() == "Open to every player"


def set_switch(run, want_open):
    """Staff set the on switch (the CPU tab's World section) to want_open, and leave it there."""
    staff = run.page(DESKTOP)
    staff.goto(dashboard("cpu/?tab=world"))
    if switch_is_open(staff) != want_open:
        name = "Open to all players" if want_open else "Make staff only"
        staff.locator("form.world-switch").get_by_role("button", name=name).click()
        staff.wait_for_load_state()
    run.expect(switch_is_open(staff) == want_open, f"the switch didn't go {'open' if want_open else 'closed'}", staff)
    staff.close()


def no_world_tab(page):
    return page.get_by_role("link", name="World", exact=True).count() == 0


@check("player")
def player(run):
    staff = run.page(DESKTOP)
    staff.goto(dashboard("cpu/?tab=world"))
    started_open = switch_is_open(staff)
    staff.close()
    try:
        for viewport, tag in ((DESKTOP, "desk"), (PHONE, "phone")):
            db("player")  # no saves, rooms or reports from the last viewport

            # ---- World mode closed: no tab, and the world's pages send the player away ----
            set_switch(run, want_open=False)
            page = login_as_player(run, viewport)
            page.goto(dashboard())
            run.expect(no_world_tab(page), "the player sees a World tab while world mode is closed", page)
            run.no_overflow(page, f"the player's nav at {viewport['width']}px")
            run.shot(page, f"{tag}-closed-nav")
            page.goto(dashboard("world/"))
            run.visible(page.get_by_text(CLOSED_MESSAGE, exact=True), "the closed message", page)
            run.expect(page.url.rstrip("/") == dashboard().rstrip("/"), f"the closed world went to {page.url}, not the sets list", page)
            run.shot(page, f"{tag}-closed-message")
            page.close()

            # ---- World mode open: a save, the town, and no staff tools ----
            set_switch(run, want_open=True)
            page = login_as_player(run, viewport)
            page.goto(dashboard())
            world_tab = run.visible(page.get_by_role("link", name="World", exact=True), "the World tab once world mode is open", page)
            run.shot(page, f"{tag}-open-nav")
            world_tab.click()
            page.wait_for_load_state()

            page.goto(dashboard("world/1/new/"))  # a save in slot 1: the first set, then start with it
            start = run.visible(page.get_by_role("button", name="Start with this set"), "the start button", page)
            run.shot(page, f"{tag}-new-save")
            start.click()
            page.wait_for_load_state()
            run.expect("/world/1/" in page.url, f"starting a save went to {page.url}", page)

            town_errors = []
            page.on("console", lambda message: town_errors.append(message.text) if message.type == "error" else None)
            page.goto(town_url())
            run.visible(page.locator("[data-world-town]"), "the town", page, 12000)
            run.no_overflow(page, f"the town at {viewport['width']}px")
            run.shot(page, f"{tag}-town")
            # The menu holds the staff tools, so it's opened for the check (its items are hidden until then).
            run.visible(page.locator("[data-open-menu]"), "the town's Menu", page).click()
            run.expect(page.locator(STAFF_ONLY).count() == 0,
                       f"{page.locator(STAFF_ONLY).count()} staff-only control(s) on the player's town", page)
            menu = page.locator(".town-hud-menu")
            run.expect(menu.is_visible(), "the town's menu isn't shown", page)
            run.shot(page, f"{tag}-town-menu")
            if menu.evaluate("m => m.scrollHeight > m.clientHeight + 2"):
                # It scrolls here: a cue shows while there's more below, and the last items are reachable.
                run.expect(menu.evaluate("m => m.classList.contains('has-more')"), "the menu scrolls but shows no cue at the top", page)
                for _ in range(40):  # Tab from the first item to 'Report a problem', which lies below the fold
                    page.keyboard.press("Tab")
                    if "Report a problem" in page.evaluate("() => document.activeElement.textContent"):
                        break
                run.expect("Report a problem" in page.evaluate("() => document.activeElement.textContent"),
                           "Tab never reached 'Report a problem' in the menu", page)
                in_view = page.evaluate("""() => {
                  const m = document.querySelector('.town-hud-menu').getBoundingClientRect();
                  const b = document.activeElement.getBoundingClientRect();
                  return b.top >= m.top - 1 && b.bottom <= m.bottom + 1; }""")
                run.expect(in_view, "the focused 'Report a problem' isn't in view in the menu", page)
                menu.evaluate("m => { m.scrollTop = m.scrollHeight; }")  # the way a finger scrolls it to the end
                page.wait_for_timeout(200)
                run.expect(not menu.evaluate("m => m.classList.contains('has-more')"), "the cue stays at the menu's end", page)
                run.shot(page, f"{tag}-town-menu-end")
            page.keyboard.press("Escape")  # shuts the menu again
            run.expect(not town_errors, f"console errors in the town: {town_errors[:3]}", page)

            # Staff pages aren't the player's: a redirect or a refusal, never the page.
            for index, (path, heading) in enumerate((("world/reports/", "Player reports"), ("cpu/?tab=world", "CPU creation"))):
                page.goto(dashboard(path))
                run.expect(page.get_by_role("heading", name=heading, exact=True).count() == 0,
                           f"the player can see the staff page '{heading}' at {path}", page)
                run.shot(page, f"{tag}-staff-{index + 1}")

            # Report a problem, as the player: the same dialog, from the town.
            page.goto(town_url())
            report = open_report(run, page)
            report.locator("textarea").fill(REPORT_TEXT)
            report.get_by_role("button", name="Send report").click()
            run.visible(report.locator("[data-report-thanks]", has_text="Thanks"), "the thanks for the player's report", page, 10000)
            run.shot(page, f"{tag}-report-sent")
            page.wait_for_function("() => !document.getElementById('town-report').open", timeout=6000)
            page.close()

            # ---- Closed again: shut out once more ----
            set_switch(run, want_open=False)
            page = login_as_player(run, viewport)
            page.goto(dashboard())
            run.expect(no_world_tab(page), "the World tab stays after the switch is closed again", page)
            page.close()
    finally:
        set_switch(run, want_open=started_open)
