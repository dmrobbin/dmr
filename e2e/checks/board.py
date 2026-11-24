"""The duel board itself, for splitting play.js (docs/round-two-plan.md, item 8): it has to behave the same before and
after. The mulligan, a card's menu and playing it (the card's flight to the stage), the card preview, the game log,
chat, the keyboard, and on a phone the touch tray."""
from . import DESKTOP, PHONE, check, db, open_duel_in_town
from .duel import MUSIC_OFF, through_rps

# The turn's status line ("Your turn · game 1 · turn 1 · Clock phase"), or the start of the page's text if there's none.
STATUS = r"() => { const m = document.body.innerText.match(/[^\n]*turn · game[^\n]*/); return m ? m[0] : document.body.innerText.slice(0, 300); }"
OUR_TURN = r"() => /Your turn · game/.test(document.body.innerText)"
PLAY_TO_C2 = """button[data-act*='"to":"C2"']"""  # a hand card's button to the center stage's middle
MAIN = r"() => /Your turn[^\n]*Main phase/.test(document.body.innerText)"


def to_my_main_phase(run, page, frame, layer):
    """Through rock, paper, scissors and the mulligan (keeping the hand), to the player's own main phase."""
    run.visible(layer.get_by_role("button", name="Begin"), "Begin", page).click()
    through_rps(run, page, frame, layer)
    run.visible(layer.get_by_role("button", name="Keep my hand"), "the mulligan's Keep my hand", page, 15000).click()
    try:  # the CPU may go first: its turn plays itself (the player's page polling is what drives it: play.cpu_step)
        frame.wait_for_function(OUR_TURN, timeout=90000)
    except Exception:
        polls = []
        page.on("request", lambda request: "/state/" in request.url and polls.append(request.url))
        page.wait_for_timeout(6000)
        server = frame.evaluate("""async () => { const r = await fetch(document.querySelector('#play').dataset.stateUrl + '?v=0');
          const d = await r.json(); const b = d.board || {};
          return { version: d.version, phase: b.phase, my_turn: b.my_turn, ability: b.ability, attack: b.attack && b.attack.step,
                   pending: Object.keys(b).filter(k => /pending|show|choose|pick/.test(k) && b[k]) }; }""")
        run.expect(False, f"our turn never came: {frame.evaluate(STATUS)!r}; polls in 6 s: {len(polls)}; server: {server}", page)
    # Our turn stops in the clock phase (clocking a card is a choice): go on to the main phase.
    for _ in range(4):  # the phase's banner can still be up when we first click: once it's gone, the click goes through
        if frame.evaluate(MAIN):
            break
        layer.locator("[data-phase-bar] [data-phase=main]").click()
        try:
            frame.wait_for_function(MAIN, timeout=4000)
        except Exception:
            pass
    run.expect(frame.evaluate(MAIN), f"Main didn't move us to the main phase: {frame.evaluate(STATUS)!r}", page)
    page.wait_for_timeout(800)


@check("board")
def board(run):
    db("save", "duel")
    page = run.page(DESKTOP, init_script=MUSIC_OFF)
    frame = open_duel_in_town(run, page)
    layer = page.frame_locator(".town-play-frame")
    to_my_main_phase(run, page, frame, layer)
    hand = layer.locator(".pcard[data-zone=hand]")
    before = hand.count()
    run.expect(before >= 5, f"{before} cards in hand", page)
    run.shot(page, "main-phase")

    # The preview: hovering a card shows it in the side panel.
    hand.first.hover()
    page.wait_for_timeout(400)
    preview = frame.evaluate("() => document.body.innerText.includes('Hover over a card to see it here.')")
    run.expect(not preview, "hovering a card didn't show it in the preview panel", page)

    # Playing a card: a playable character's hover buttons put it on the stage (L / M / R); it flies there.
    db("stock")  # the test deck's cheapest cards cost 1
    page.wait_for_timeout(2500)  # the next poll brings the stock
    play_buttons = layer.locator(PLAY_TO_C2)
    run.expect(play_buttons.count() >= 1, "no card in hand can be played to the stage (the test deck has level 0 characters)", page)
    uid = frame.evaluate("sel => JSON.parse(document.querySelector(sel).dataset.act).uid", PLAY_TO_C2)
    page.mouse.move(5, 5)  # off the last card: its hover actions cover its neighbours
    page.wait_for_timeout(300)
    layer.locator(f".pcard[data-zone=hand][data-uid='{uid}']").hover()
    page.wait_for_timeout(300)
    run.shot(page, "hand-actions")
    layer.locator(f"""button[data-act*='"uid":"{uid}"'][data-act*='"to":"C2"']""").click()
    try:
        frame.wait_for_function("sel => !document.querySelector(sel)", arg=f".pcard[data-zone=hand][data-uid='{uid}']", timeout=5000)
    except Exception:
        run.expect(False, "the played card is still in hand", page)
    page.wait_for_timeout(1200)  # its flight
    run.expect(hand.count() == before - 1, f"playing a card left {hand.count()} in hand, not {before - 1}", page)
    where = frame.evaluate("uid => [...document.querySelectorAll(`.pcard[data-uid='${uid}']`)].map(e => [e.dataset.zone, e.dataset.owner, e.className])", uid)
    run.expect(any(zone == "C2" for zone, owner, cls in where), f"the played card isn't in the center stage's middle: {where}", page)
    log = frame.evaluate("() => document.querySelector('[data-log]').innerText")
    run.expect("center stage" in log, f"playing a card wasn't logged: {log[-200:]!r}", page)
    run.shot(page, "played")

    # The full menu: More… on a card in hand lists what it can do; Escape puts it away.
    page.mouse.move(5, 5)
    page.wait_for_timeout(300)
    hand.first.hover()
    page.wait_for_timeout(300)
    hand.first.locator("xpath=ancestor::*[contains(@class,'hand-card')][1]").locator("[data-more]").click()
    menu = run.visible(layer.locator("[data-menu]"), "the card's menu", page)
    items = menu.locator("button").count()
    run.expect(items >= 2, f"the card's menu has {items} items", page)
    run.shot(page, "menu")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    run.expect(menu.is_hidden(), "Escape didn't close the card's menu", page)

    # The song: a dropdown of the battle music and every song. Picking one saves it (the town's key too) and it stays
    # picked as the board is drawn again; Battle music clears it.
    song = layer.locator("select[data-song]")
    run.visible(song, "the Song dropdown", page)
    options = song.locator("option").all_inner_texts()
    run.expect(options[0] == "Battle music" and len(options) > 2, f"the Song dropdown's options: {options[:4]}", page)
    song.select_option(index=2)
    picked = song.input_value()
    run.expect(frame.evaluate("() => localStorage.getItem('weiss-town-music')") == picked, "picking a song didn't save it", page)
    page.wait_for_timeout(2500)  # a poll or two: the controls are drawn again
    run.expect(song.input_value() == picked, "the picked song didn't stay picked as the board updated", page)
    run.shot(page, "song")
    song.select_option(value="")
    run.expect(frame.evaluate("() => localStorage.getItem('weiss-town-music')") is None, "Battle music didn't clear the saved song", page)

    # Chat: a message goes into the log.
    layer.get_by_placeholder("Message").fill("Good luck!")
    layer.get_by_role("button", name="Send").click()
    page.wait_for_timeout(1200)
    run.expect("Good luck!" in frame.evaluate("() => document.querySelector('[data-log]').innerText"), "the chat message isn't in the log", page)


@check("board-phone")
def board_phone(run):
    """A phone: tapping a card in hand brings up its buttons in a tray, and × puts it down."""
    db("save")
    db("duel")
    phone = run.page(PHONE, init_script=MUSIC_OFF, touch=True)
    frame = open_duel_in_town(run, phone)
    layer = phone.frame_locator(".town-play-frame")
    to_my_main_phase(run, phone, frame, layer)
    run.no_overflow(phone, "the board at 390px", frame)
    layer.locator(".pcard[data-zone=hand]").first.tap()
    tray = run.visible(layer.locator("[data-tray]"), "the touch tray for a tapped card", phone)
    run.expect(tray.locator("button").count() >= 2, "the touch tray has no buttons", phone)
    run.shot(phone, "phone-tray")
    tray.locator("[data-tray-close]").tap()
    phone.wait_for_timeout(300)
    run.expect(tray.is_hidden(), "× didn't put the card down", phone)

