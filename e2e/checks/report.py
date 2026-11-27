"""Report a problem (docs/world-release-plan.md, item F): from the town's menu, a player sends a report; it's kept with their
save, and staff see it on the player reports page. The dialog's own states: empty, too long (the count), sending, sent,
and an error that keeps the text."""
import time

import harness

from . import DESKTOP, PHONE, check, db, town_url

THANKS = "Thanks: we've got it. We'll look into it."
DARK = "localStorage.setItem('site-theme', 'dark')"


def reports_url():
    return f"{harness.BASE}/dashboard/weiss/world/reports/"


def open_report(run, page):
    """From the town, open the menu's Report a problem. Returns the dialog's locator."""
    run.visible(page.locator("[data-open-menu]"), "the town's Menu button", page).click()
    run.visible(page.locator("[data-report-open]"), "'Report a problem' in the menu", page).click()
    dialog = page.locator("#town-report")
    run.expect(dialog.evaluate("d => d.open"), "the report dialog didn't open", page)
    return dialog


@check("report")
def report(run):
    db("save")
    db("reports")  # five an hour a player: a run starts clear
    stamp = str(int(time.time()))  # a unique marker in the text, to find this run's reports on the staff list
    for viewport, tag, theme in ((DESKTOP, "desk", None), (PHONE, "phone", None), (PHONE, "phone-dark", DARK)):
        page = run.page(viewport, init_script=theme)
        page.goto(town_url())
        dialog = open_report(run, page)
        textarea = dialog.locator("textarea")
        run.expect(textarea.evaluate("t => t === document.activeElement"), "the text box isn't focused when the dialog opens", page)
        run.no_overflow(page, f"the report dialog at {viewport['width']}px")
        run.shot(page, f"{tag}-open")

        # Empty: refused in words, and nothing sent.
        dialog.get_by_role("button", name="Send report").click()
        error = dialog.locator("[data-report-error]")
        run.visible(error, "the empty-text error", page)
        run.expect("Write a few words" in error.inner_text(), f"the empty error reads {error.inner_text()!r}", page)

        # The count starts at 1,800 characters.
        textarea.fill("x" * 1799)
        run.expect(dialog.locator("[data-report-count]").is_hidden(), "the count shows before 1,800 characters", page)
        textarea.fill("x" * 1800)
        count = run.visible(dialog.locator("[data-report-count]"), "the count from 1,800", page).inner_text()
        run.expect(count == "200 characters left", f"the count reads {count!r} at 1,800", page)
        textarea.fill("x" * 1999)
        run.expect(dialog.locator("[data-report-count]").inner_text() == "1 character left", "the singular count is wrong", page)
        textarea.fill("x" * 2001)
        run.expect(dialog.locator("[data-report-count]").inner_text() == "1 too many", "the over-limit count is wrong", page)
        run.shot(page, f"{tag}-too-long")
        dialog.get_by_role("button", name="Send report").click()
        run.visible(error, "the too-long error", page)
        run.expect("over 2,000" in error.inner_text(), f"the too-long error reads {error.inner_text()!r}", page)
        run.expect(len(textarea.input_value()) == 2001, "the text was cut short on the too-long error", page)

        # Sent: the text goes, the thanks show, the dialog closes and focus goes back to the Menu.
        message = f"Report check {stamp} {tag}: the pack button did nothing when I pressed it."
        textarea.fill(message)
        dialog.get_by_role("button", name="Send report").click()
        run.visible(dialog.locator("[data-report-thanks]", has_text=THANKS), "the thanks after sending", page, 10000)
        run.shot(page, f"{tag}-sent")
        page.wait_for_function("() => !document.getElementById('town-report').open", timeout=6000)
        run.expect(page.evaluate("() => document.activeElement && document.activeElement.hasAttribute('data-open-menu')"),
                   "focus didn't go back to the Menu button after the report", page)

        # The report is kept with the save as it was.
        staff = run.page(viewport)
        staff.goto(reports_url())
        run.visible(staff.get_by_role("heading", name="Player reports", exact=True), "the player reports heading", staff)
        mine = staff.locator("article.report", has_text=message)
        run.visible(mine, "this report on the staff list", staff)
        run.no_overflow(staff, f"the staff list at {viewport['width']}px")
        mine.locator("details summary").click()
        run.visible(mine.locator("pre.report-state"), "the save state in the report", staff)
        run.shot(staff, f"{tag}-staff")
        staff.close()
        page.close()

    # Esc closes it, with the focus back on the Menu, and a second open is empty again.
    page = run.page(PHONE)
    page.goto(town_url())
    dialog = open_report(run, page)
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.getElementById('town-report').open", timeout=4000)
    run.expect(page.evaluate("() => document.activeElement && document.activeElement.hasAttribute('data-open-menu')"),
               "Esc didn't put focus back on the Menu button", page)
    dialog = open_report(run, page)
    run.expect(dialog.locator("textarea").input_value() == "", "the text from an earlier, cancelled report is still there", page)
    dialog.get_by_role("button", name="Cancel").click()
    run.expect(page.evaluate("() => !document.getElementById('town-report').open"), "Cancel didn't close the dialog", page)

    # In full screen (the town's window, data-window), the dialog still opens over it.
    page = run.page(DESKTOP)
    page.goto(town_url())
    run.visible(page.locator("[data-fullscreen]"), "the town's full screen button", page).click()
    page.wait_for_function("() => document.fullscreenElement !== null", timeout=5000)
    dialog = open_report(run, page)
    run.expect(dialog.locator("textarea").is_visible(), "the report dialog isn't visible in full screen", page)
    run.shot(page, "desk-fullscreen")
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.getElementById('town-report').open", timeout=4000)


@check("world-switch")
def world_switch(run):
    """The CPU tab's on switch: open to every player, then staff only again. Each press saves straight away and shows its
    message; the status is the saved state. The test ends with the switch as it started."""
    OPEN_MESSAGE = "World mode is open to every player."
    CLOSED_MESSAGE = "World mode is staff only again. Players' saves are kept."
    url = f"{harness.BASE}/dashboard/weiss/cpu/?tab=world"

    def switch(page):
        return page.locator("form.world-switch")

    def status(page):
        return page.locator("[data-open-status]").inner_text()

    page = run.page(DESKTOP)
    page.goto(url)
    run.visible(switch(page), "the on switch", page)
    started_open = status(page) == "Open to every player"
    try:
        if started_open:  # the check starts from staff only
            switch(page).get_by_role("button", name="Make staff only").click()
            page.wait_for_load_state()
        run.expect(status(page) == "Staff only", f"the status reads {status(page)!r} before opening", page)
        run.expect(switch(page).get_by_role("button", name="Open to all players").count() == 1, "no 'Open to all players' button", page)
        run.shot(page, "switch-staff-only")

        switch(page).get_by_role("button", name="Open to all players").click()
        page.wait_for_load_state()
        run.visible(page.locator(".messages").get_by_text(OPEN_MESSAGE, exact=True), "the opened message", page)
        run.expect(status(page) == "Open to every player", f"the status reads {status(page)!r} after opening", page)
        run.expect(page.locator("[data-open-status].is-open").count() == 1, "the open status isn't marked live", page)
        run.expect(switch(page).get_by_role("button", name="Make staff only").count() == 1, "no 'Make staff only' button once open", page)
        run.shot(page, "switch-open")
        page.evaluate("() => document.documentElement.setAttribute('data-theme', 'dark')")  # the same state in dark
        run.shot(page, "switch-open-dark")
        page.evaluate("() => document.documentElement.setAttribute('data-theme', 'light')")

        switch(page).get_by_role("button", name="Make staff only").click()
        page.wait_for_load_state()
        run.visible(page.locator(".messages").get_by_text(CLOSED_MESSAGE, exact=True), "the closed message", page)
        run.expect(status(page) == "Staff only", f"the status reads {status(page)!r} after closing", page)
        run.expect(page.locator("[data-open-status].is-open").count() == 0, "the closed status is still marked live", page)
        run.shot(page, "switch-closed-again")
    finally:
        page.goto(url)  # put the switch back as it was
        if (status(page) == "Open to every player") != started_open:
            switch(page).get_by_role("button", name="Make staff only" if started_open is False else "Open to all players").click()
            page.wait_for_load_state()
