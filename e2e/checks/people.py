"""World mode's people journal (docs/round-two-plan.md, item 4): the grid, one person's entry, and opening it from the
town's menu."""
import harness

from . import DESKTOP, PHONE, check, db, town_url


def people_url(slot=1):
    return f"{harness.BASE}/dashboard/weiss/world/{slot}/people/"


@check("people")
def people(run):
    db("packs")  # the journal entries come from the world pack's lines
    db("save")
    friend = db("people")
    for viewport, tag in ((DESKTOP, "desk"), (PHONE, "phone")):
        page = run.page(viewport)
        page.goto(people_url())
        run.visible(page.get_by_role("heading", name="People", exact=True), "the People heading", page)
        count = page.locator("[data-people-count]").inner_text()
        run.expect(count.startswith("3 of "), f"the count reads {count!r}, with 3 people met", page)
        cards = page.locator("a.people-card")
        run.expect(cards.count() == 3, f"{cards.count()} met people shown, not 3", page)
        unmet = page.get_by_role("img", name="Someone you haven't met")
        run.expect(unmet.count() >= 1, "the unmet people aren't shown as locked", page)
        run.expect(not page.locator("[data-people-empty]").count(), "the 'met no one yet' message shows with people met", page)
        run.no_overflow(page, f"the people grid at {viewport['width']}px")
        run.shot(page, f"{tag}-grid")

        page.locator(f"a.people-card[href='?cpu={friend}']").click()
        entry = run.visible(page.locator("[data-people-entry]"), "the chosen person's entry", page)
        text = entry.inner_text()
        run.expect("Friend" in text and "Next: Good friend" in text, "the entry's rank and next rank are wrong", page)
        run.expect("Duels: 2 won · 1 lost" in text, "the entry's record is wrong", page)
        run.expect("Loved" in text, "the gift they loved isn't listed", page)
        entries = entry.locator(".people-journal li")
        locked = entry.locator(".people-journal li", has_text="to learn more")
        run.expect(entries.count() == 4, f"{entries.count()} journal entries, not 4", page)
        run.expect(locked.count() == 2, f"at Friend, {locked.count()} entries locked, not 2 (ranks 4 and 5)", page)
        run.expect(page.locator("a.people-card[aria-current='true']").count() == (1 if viewport is DESKTOP else page.locator("a.people-card[aria-current='true']").count()),
                   "the chosen card isn't marked", page)
        run.no_overflow(page, f"an entry at {viewport['width']}px")
        run.shot(page, f"{tag}-entry")

    # From the town: its menu opens the journal in a sheet.
    page = run.page(DESKTOP)
    page.goto(town_url())
    opener = page.locator("[data-people-link]")
    if not opener.is_visible():  # it's in the town's menu
        menu = page.locator("[data-hud-menu-toggle], .town-hud-menu-toggle, button[aria-controls*='menu']").first
        if menu.count():
            menu.click()
    run.visible(opener, "the town's People link", page).click()
    sheet = page.frame_locator("iframe").get_by_role("heading", name="People", exact=True)
    run.visible(sheet, "the people journal opened from the town", page, 10000)
    run.shot(page, "from-town")
