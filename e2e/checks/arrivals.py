"""A newcomer in town (docs/world-arrivals-plan.md, "Pacing change"): marked as new, and meeting them plays their arrival
scene, by itself and only theirs. Arrivals used to play a whole week's worth back to back as the week began."""
from . import DESKTOP, PHONE, check, db, town_url


@check("arrivals")
def arrivals(run):
    for viewport, tag in ((DESKTOP, "desk"), (PHONE, "phone")):
        db("save")
        name = db("newcomer")
        page = run.page(viewport)
        page.goto(town_url())
        person = run.visible(page.locator(".town-person", has=page.locator(".town-new-mark")), f"{name} marked as new", page)
        label = person.get_attribute("aria-label") or ""
        run.expect(name in label and "new in town" in label, f"the newcomer's label is {label!r}", page)
        others = page.locator(".town-person .town-new-mark").count()
        run.expect(others == 1, f"{others} people marked as new, not 1", page)
        run.expect(not page.locator(".town-play-frame").count() or page.locator("[data-play-layer]").is_hidden(),
                   "a scene started by itself before the newcomer was met", page)
        run.shot(page, f"{tag}-new")
        person.click()
        run.visible(page.frame_locator(".town-play-frame").get_by_text("I've only just got here", exact=False),
                    "the newcomer's arrival scene, after clicking them", page, 10000)
        run.shot(page, f"{tag}-scene")
