"""The installable app (weiss.pwa): manifest and icons, the service worker taking control, and the offline page."""
import harness

from . import DESKTOP, PHONE, check

GAME = f"{harness.BASE}/dashboard/weiss/"


@check("app")
def app(run):
    page = run.page(DESKTOP)
    page.goto(GAME)
    manifest = page.evaluate("""async () => { const link = document.querySelector('link[rel=manifest]');
        const data = await (await fetch(link.href)).json();
        const icons = await Promise.all(data.icons.map(icon => new Promise(done => { const img = new Image();
          img.onload = () => done([icon.src, img.naturalWidth]); img.onerror = () => done([icon.src, 0]); img.src = icon.src; })));
        return { name: data.name, scope: data.scope, start: data.start_url, icons }; }""")
    for src, width in manifest["icons"]:
        run.expect(width >= 192, f"the manifest's icon {src} didn't load", page)
    run.expect(manifest["start"].startswith(manifest["scope"]), f"start_url {manifest['start']} is outside the scope", page)

    # The worker installs, and takes the page over once it reloads.
    scope = page.evaluate("async () => (await navigator.serviceWorker.ready).scope")
    run.expect(scope.endswith("/dashboard/weiss/"), f"the worker's scope is {scope}", page)
    page.reload()
    run.expect(page.evaluate("() => Boolean(navigator.serviceWorker.controller)"), "the worker isn't controlling the page", page)
    icon = manifest["icons"][0][0]
    page.evaluate("src => fetch(src).then(r => r.blob())", icon)  # cached now, as a static image

    # Offline: a page shows the offline page, not the browser's error; a cached image still loads.
    page.context.set_offline(True)
    try:
        page.goto(GAME + "lists/", wait_until="domcontentloaded")
        run.visible(page.get_by_role("heading", name="You're offline"), "the offline page", page)
        run.expect(page.evaluate("() => document.activeElement && document.activeElement.textContent.trim()") == "Try again",
                   "Try again doesn't have focus", page)
        run.shot(page, "offline")
        cached = page.evaluate("src => fetch(src).then(r => r.status).catch(() => 0)", icon)
        run.expect(cached == 200, f"a cached image didn't load offline ({cached})", page)
    finally:
        page.context.set_offline(False)
    # Back online, the offline page reloads by itself into the page that was asked for.
    try:
        page.get_by_text("You're offline").wait_for(state="detached", timeout=8000)
    except Exception:
        run.expect(False, "the offline page didn't reload once back online", page)
    page.wait_for_load_state()
    run.expect("lists" in page.url, f"back online, the page is {page.url}", page)

    # The town's play layer is a frame: it mustn't register a worker of its own (only the top page does).
    run.expect('window.top === window' in page.content(), "the registration isn't limited to the top page", page)

    phone = run.page(PHONE, login=False)
    phone.goto(f"{harness.BASE}/dashboard/weiss/offline/")
    run.no_overflow(phone, "the offline page at 390px")
    run.shot(phone, "offline-phone")
