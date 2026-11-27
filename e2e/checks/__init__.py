"""Browser checks: the parts of the game that only show their bugs in a real browser, kept so they can be run again.

Run them all, or some by name:
    python e2e/harness.py checks
    python e2e/harness.py checks versus ceremony

Each check drives the real pages in headless Edge (muted) against the scratch database, as a player would. A check fails
on a page error, a missing element or a broken expectation; each failure names the check, says what was wrong and
leaves a screenshot in e2e/scratch/shots/. Screenshots are also saved along the way, named check-<check>-<step>, so a
run can be looked over by eye.

A check is a function taking a Run and registered with @check("name"); the modules imported at the bottom hold them.
"""
import pathlib
import subprocess
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import harness  # noqa: E402

CHECKS = {}

DESKTOP = {"width": 1280, "height": 800}
PHONE = {"width": 390, "height": 844}


def check(name):
    def register(fn):
        CHECKS[name] = fn
        return fn
    return register


class Failed(Exception):
    pass


def db(*commands):
    """Run e2e/checks/db.py's commands on the scratch database; their output's last line."""
    done = subprocess.run([sys.executable, "-I", str(HERE / "db.py"), *commands], capture_output=True, text=True,
                          cwd=harness.ROOT)
    if done.returncode:
        raise Failed(f"db.py {' '.join(commands)} failed:\n{done.stderr[-1500:]}")
    return done.stdout.strip().splitlines()[-1] if done.stdout.strip() else ""


class Run:
    """One check's run: its pages, and what went wrong on them."""

    def __init__(self, name, browser):
        self.name, self.browser, self.errors, self.pages = name, browser, [], []

    def page(self, viewport=DESKTOP, login=True, init_script=None, touch=False):
        """A logged-in page in a fresh browser context. touch: a phone's touch screen (no hover, a coarse pointer)."""
        context = self.browser.new_context(viewport=viewport, has_touch=touch, is_mobile=touch)
        page = context.new_page()
        if init_script:
            page.add_init_script(init_script)
        page.on("pageerror", lambda error: self.errors.append(f"page error: {str(error)[:300]}"))
        if login:
            harness.login(page)
        self.pages.append(page)
        return page

    def shot(self, page, step):
        return harness.shot(page, f"check-{self.name}-{step}")

    def expect(self, condition, message, page=None):
        if not condition:
            if page:
                self.shot(page, "FAILED")
            raise Failed(message)

    def visible(self, locator, what, page=None, timeout=8000):
        try:
            locator.first.wait_for(state="visible", timeout=timeout)
        except Exception:
            self.expect(False, f"not shown: {what}", page)
        return locator.first

    def no_overflow(self, page, where="the page", frame=None):
        """Nothing makes the page scroll sideways (a phone layout's commonest break)."""
        target = frame or page
        wide = target.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        self.expect(wide <= 1, f"{where} scrolls sideways by {wide}px", page)


def town_url(slot=1):
    return f"{harness.BASE}/dashboard/weiss/world/{slot}/town/"


def open_duel_in_town(run, page):
    """From the town, open the waiting duel in the play layer. Returns the duel's frame."""
    page.goto(town_url())
    link = run.visible(page.locator("a[data-play='duel']"), "the town's link to the waiting duel", page)
    link.click()
    run.visible(page.frame_locator(".town-play-frame").locator("#play"), "the duel inside the town's play layer", page, 12000)
    for _ in range(40):
        frame = next((f for f in page.frames if "/play/" in f.url), None)
        if frame:
            return frame
        page.wait_for_timeout(250)
    raise Failed("the play layer's frame never loaded a duel")


def main(names):
    unknown = [name for name in names if name not in CHECKS]
    if unknown:
        raise SystemExit(f"no such check: {', '.join(unknown)}. There are: {', '.join(CHECKS)}")
    chosen = names or list(CHECKS)
    with one_run_at_a_time():
        return run_checks(chosen)


LOCK = harness.SCRATCH / "checks.lock"


class one_run_at_a_time:
    """Two runs at once share the port and the scratch database (one's set-up deletes the other's duel): the second waits."""

    def __enter__(self):
        import os
        for waited in range(600):
            try:
                self.fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, str(os.getpid()).encode())
                return self
            except FileExistsError:
                if time.time() - LOCK.stat().st_mtime > 1800:  # left by a run that was killed
                    LOCK.unlink(missing_ok=True)
                    continue
                if waited == 0:
                    print("Another check run is going (e2e/scratch/checks.lock): waiting for it to finish...", flush=True)
                time.sleep(2)
        raise SystemExit("Gave up waiting for the other check run. If none is running, delete e2e/scratch/checks.lock.")

    def __exit__(self, *exc):
        import os
        os.close(self.fd)
        LOCK.unlink(missing_ok=True)


def run_checks(chosen):
    print("scratch database:", db("migrate"))
    from playwright.sync_api import sync_playwright
    server = harness.server()
    results = []
    try:
        with sync_playwright() as playwright:
            browser = harness.browser(playwright)
            for name in chosen:
                run, started = Run(name, browser), time.time()
                try:
                    CHECKS[name](run)
                    if run.errors:
                        raise Failed("; ".join(run.errors[:3]))
                    results.append((name, None))
                except Failed as failure:
                    results.append((name, str(failure)))
                except Exception:
                    for page in run.pages[-1:]:
                        try:
                            run.shot(page, "FAILED")
                        except Exception:
                            pass
                    results.append((name, traceback.format_exc(limit=4)))
                finally:
                    for page in run.pages:
                        page.context.close()
                print(f"{'PASS' if results[-1][1] is None else 'FAIL'}  {name}  ({time.time() - started:.0f} s)", flush=True)
                if results[-1][1]:
                    print("      " + results[-1][1].replace("\n", "\n      "), flush=True)
            browser.close()
    finally:
        server.terminate()
    failed = [name for name, problem in results if problem]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed." + (f" Failed: {', '.join(failed)}." if failed else ""))
    print(f"Screenshots: {harness.SHOTS}")
    if failed:
        warnings = [line.rstrip() for line in harness.SERVER_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
                    if "WARNING" in line or "ERROR" in line or "Traceback" in line]
        print(f"Server log: {harness.SERVER_LOG}" + (f" ({len(warnings)} warnings or errors; the last: {warnings[-1][:200]})" if warnings else ""))
    return 1 if failed else 0


from . import app, arrivals, board, duel, minigames, people, player, recap, report, theme  # noqa: E402,F401  (they register their checks)
