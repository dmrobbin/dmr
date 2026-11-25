"""A town duel's presentation (docs/duel-presentation-plan.md): the versus intro in the town's play layer, rock paper
scissors, the CPU's reactions (with the board faked through the real poll path), and the results ceremony."""
import json

from . import DESKTOP, PHONE, Failed, check, db, open_duel_in_town

MUSIC_OFF = "try { localStorage.setItem('weiss-music', 'off'); } catch (e) {}"


def intro_in_town(run, viewport, tag, init_script=MUSIC_OFF):
    db("save", "duel")
    page = run.page(viewport, init_script=init_script)
    frame = open_duel_in_town(run, page)
    layer = page.frame_locator(".town-play-frame")
    intro = run.visible(layer.locator(".cpu-intro"), "the versus intro", page)
    page.wait_for_timeout(1600)  # past the impact
    run.shot(page, f"{tag}-impact")
    size = frame.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.cpu-intro-name')).fontSize)")
    run.expect(size >= 20, f"the CPU's name is {size}px: something is overriding its size again", page)
    intro.click(position={"x": 30, "y": 30})  # skips to the end
    begin = run.visible(layer.get_by_role("button", name="Begin"), "Begin", page)
    page.wait_for_timeout(300)
    focused = frame.evaluate("() => document.activeElement && document.activeElement.textContent.trim()")
    run.expect(focused == "Begin", f"after skipping, focus is on {focused!r}, not Begin", page)
    run.no_overflow(page, f"the intro at {viewport['width']}px", frame)
    run.shot(page, f"{tag}-end")
    return page, frame, layer, begin


RPS_WATCH = """() => { window.__rps = { ties: 0, result: '' }; let tie = false;
  new MutationObserver(() => { const r = document.querySelector('.rps-result');
    if (r && !window.__rps.result) window.__rps.result = r.textContent.trim();
    const now = /A tie!/.test(document.body.innerText); if (now && !tie) window.__rps.ties++; tie = now; })
  .observe(document.body, { subtree: true, childList: true, characterData: true }); }"""


def through_rps(run, page, frame, layer, picked=False):
    """Begin's been clicked: play rock, paper, scissors until someone wins. Returns the first-player banner's words.
    picked: a first pick has been made already (with RPS_WATCH installed before it)."""
    # Ties and the result are noted as they happen: the banner only stays a moment before the mulligan.
    if not picked:
        frame.evaluate(RPS_WATCH)
    for round_ in range(6):  # a tie means choosing again
        ties = frame.evaluate("() => window.__rps.ties")
        if not (picked and round_ == 0):
            run.visible(layer.locator(".rps-choices button"), "rock, paper, scissors", page)
            layer.locator(".rps-choices button").first.click()
        frame.wait_for_function(f"() => window.__rps.result || window.__rps.ties > {ties}", timeout=12000)
        if frame.evaluate("() => window.__rps.result"):
            break
    return frame.evaluate("() => window.__rps.result")


# Holds the intro's start (intro_done) back for a moment, as a slow connection would: a pick made straight after Begin
# then reaches the server first unless the page waits for it.
SLOW_BEGIN = """(() => { const real = window.fetch; window.fetch = function (url, options) {
  if (options && typeof options.body === 'string' && options.body.includes('intro_done'))
    return new Promise((resolve) => setTimeout(resolve, 800)).then(() => real.call(this, url, options));
  return real.call(this, url, options); }; })();"""


@check("versus")
def versus(run):
    page, frame, layer, begin = intro_in_town(run, DESKTOP, "desk", init_script=MUSIC_OFF + SLOW_BEGIN)
    # A quick player picks the moment Begin is pressed: the pick has to wait for the start to reach the server, not
    # be refused ("The match hasn't started yet.").
    frame.evaluate(RPS_WATCH)
    begin.click()
    layer.locator(".rps-choices button").first.click(timeout=8000)
    page.wait_for_timeout(300)
    shown = frame.evaluate("() => [...document.querySelectorAll('.panel-error')].filter(e => !e.hidden).map(e => e.innerText)")
    run.expect(not shown, f"picking straight after Begin showed an error: {shown}", page)
    banner = through_rps(run, page, frame, layer, picked=True)
    shown = frame.evaluate("() => [...document.querySelectorAll('.panel-error')].filter(e => !e.hidden).map(e => e.innerText)")
    run.expect(not shown, f"rock, paper, scissors showed an error: {shown}", page)
    run.expect("first" in banner, f"no first-player banner (saw {banner!r})", page)
    run.shot(page, "desk-rps")
    intro_in_town(run, PHONE, "phone")


class FakeBoard:
    """Answers the duel's state polls with the real payload, its board changed to show what a step wants."""

    def __init__(self):
        self.on, self.bump = False, 0
        self.turn = 3
        self.them = {"damage_taken": 0, "negated": 0, "level_ups": 0, "level": 0, "clock": 0}
        self.me = {"level": 0, "clock": 0, "damage_taken": 0}

    def handle(self, route):
        if not self.on:
            return route.continue_()
        try:  # a version the server hasn't got is answered at once, so no long poll is held open
            response = route.fetch(url=route.request.url.split("?")[0] + "?v=0", timeout=8000)
        except Exception:
            return route.abort()
        body = response.json() if response.status == 200 else None
        if not body or "board" not in body:
            return route.fulfill(response=response)
        board = body["board"]
        board.pop("rps", None)
        board.update(mulligan=None, phase="main", my_turn=True, level_up_pending=False, ability=None, attack=None, turn_number=self.turn)
        them, me = board["opponent"], board["me"]
        them.update({key: self.them[key] for key in ("damage_taken", "negated", "level_ups")})
        sample = next(card for side in (me, them) for zone in side["zones"].values() if isinstance(zone, list) for card in zone)
        pile = lambda n: [dict(sample, uid=f"fake{i}") for i in range(n)]  # noqa: E731
        them["zones"]["level"], them["zones"]["clock"] = pile(self.them["level"]), pile(self.them["clock"])
        me["zones"]["level"], me["zones"]["clock"] = pile(self.me["level"]), pile(self.me["clock"])
        me["damage_taken"] = self.me["damage_taken"]
        body["version"] = 10_000 + self.bump
        route.fulfill(response=response, body=json.dumps(body))


@check("reactions")
def reactions(run):
    page, frame, layer, begin = intro_in_town(run, DESKTOP, "reactions")
    begin.click()
    page.wait_for_timeout(1500)
    lines = json.loads(frame.evaluate("""async () => JSON.stringify((await (await fetch(
        document.querySelector('#play').dataset.stateUrl)).json()).cpu.reactions)"""))
    run.expect(all(lines.get(context) for context in ("duel_hurt", "duel_brink", "duel_winning")),
               f"the CPU has no lines for some reactions: {sorted(lines)}", page)
    fake = FakeBoard()
    page.route("**/play/*/state/**", fake.handle)

    def bubble():
        return frame.evaluate("""() => { const e = document.querySelector('.cpu-reaction');
          if (!e || e.hidden) return ''; const s = getComputedStyle(e);
          return s.display === 'none' || s.visibility === 'hidden' || +s.opacity < .1 ? '' : e.innerText.trim(); }""")

    def said(context, text):
        return any(line["text"] in text for line in lines.get(context, []))

    def step(change, wait=1600):
        change()
        fake.bump += 1
        page.wait_for_timeout(wait)
        return bubble()

    fake.on = True
    shown = step(lambda: None, 2500)
    run.expect(not shown, f"a reaction with nothing happening: {shown!r}", page)
    shown = step(lambda: fake.them.update(damage_taken=3))
    run.expect(said("duel_hurt", shown), f"a 3-damage hit: expected a duel_hurt line, got {shown!r}", page)
    run.shot(page, "reactions-hurt")
    page.wait_for_timeout(3000)
    shown = step(lambda: fake.them.update(negated=1))
    run.expect(not shown, f"a second reaction in one turn: {shown!r}", page)
    # Match point takes priority: it shows in the same turn, inside 15 s of the last.
    shown = step(lambda: fake.them.update(damage_taken=6, level=3, clock=4), 1800)
    run.expect(said("duel_brink", shown), f"at match point: expected a duel_brink line, got {shown!r}", page)
    page.wait_for_timeout(3000)
    shown = step(lambda: fake.me.update(level=3, clock=4), 1800)
    run.expect(said("duel_winning", shown), f"the player at match point: expected a duel_winning line, got {shown!r}", page)
    page.wait_for_timeout(4000)
    shown = step(lambda: (setattr(fake, "turn", 4), fake.them.update(level_ups=1)))
    run.expect(not shown, f"a reaction under 15 s after the last: {shown!r}", page)
    logged = frame.evaluate("() => document.querySelector('[data-log]') ? document.querySelector('[data-log]').innerText : ''")
    run.expect(any(line["text"] in logged for line in lines["duel_hurt"]), "the reaction isn't in the game log", page)
    fake.on = False


@check("ceremony")
def ceremony(run):
    for viewport, tag in ((DESKTOP, "desk"), (PHONE, "phone")):
        page, frame, layer, begin = intro_in_town(run, viewport, f"ceremony-{tag}")
        begin.click()
        page.wait_for_timeout(800)
        db("finish")
        over = run.visible(layer.locator(".game-over"), "the game-over screen", page, 15000)
        word = frame.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.game-over .game-over-word')).fontSize)")
        run.expect(word >= 32, f"VICTORY is {word}px", page)
        page.wait_for_timeout(700)
        run.shot(page, f"ceremony-{tag}-steps")
        over.click(position={"x": 10, "y": 10})  # finishes every step at once
        back = run.visible(layer.get_by_role("link", name="Back to the town").or_(layer.get_by_role("button", name="Back to the town")),
                           "Back to the town", page)
        page.wait_for_timeout(400)
        focused = frame.evaluate("() => document.activeElement && document.activeElement.textContent.trim()")
        run.expect(focused and "Back to the town" in focused, f"after the ceremony, focus is on {focused!r}", page)
        coins = frame.evaluate("() => (document.querySelector('.game-over').innerText.match(/[\\d,]+ coins/) || [''])[0]")
        run.expect(coins, "the ceremony shows no coins", page)
        run.no_overflow(page, f"the ceremony at {viewport['width']}px", frame)
        run.shot(page, f"ceremony-{tag}-done")
        if back.is_visible() is False:
            raise Failed("Back to the town vanished")
