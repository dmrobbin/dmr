"""Browser harness for the end-to-end tests: a server on the scratch database, and Edge driven by Playwright with real
clicks. Nothing here touches the dev database (DJANGO_SQLITE_PATH is set for the server's run).

Usage: python e2e/harness.py checks [name ...]   (the browser checks: see e2e/checks/)
       python e2e/tutorial.py               (the tutorial, clicked through)
"""
import os
import pathlib
import socket
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "e2e" / "scratch"
DB = SCRATCH / "e2e.sqlite3"
SHOTS = SCRATCH / "shots"
SERVER_LOG = SCRATCH / "server.log"  # the test server's output, from the last run
PORT = int(os.environ.get("E2E_PORT", "8765"))
BASE = f"http://127.0.0.1:{PORT}"
USER, PASSWORD = "e2e", "e2e-pass"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def server():
    """Start the dev server on the scratch database and wait until it answers. Returns the process."""
    env = {**os.environ, "DJANGO_SQLITE_PATH": str(DB), "DJANGO_DEBUG": "1", "PYTHONUNBUFFERED": "1"}
    assert DB.exists(), f"no scratch database at {DB}: run e2e/seed.py first"
    # Its output (requests, and warnings such as a CPU that finds no move) goes to a log, for looking into a failure.
    SCRATCH.mkdir(parents=True, exist_ok=True)
    log = open(SERVER_LOG, "w", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
                               cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=1).close()
            return process
        except OSError:
            time.sleep(0.5)
    process.kill()
    raise SystemExit("the server didn't start")


def browser(playwright):
    """Edge, headless, with audio muted (headless runs must always mute: see the team's notes)."""
    return playwright.chromium.launch(executable_path=EDGE, headless=True, args=["--mute-audio", "--disable-gpu", "--disable-dev-shm-usage"])


def login(page):
    page.goto(f"{BASE}/login/")
    page.fill("input[name=username]", USER)
    page.fill("input[name=password]", PASSWORD)
    page.click("button[type=submit], input[type=submit]")
    page.wait_for_load_state()


def shot(page, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return path


def reset_saves():
    """Delete the test user's world saves on the scratch database, so every run starts from a new save."""
    code = ("from django.contrib.auth.models import User; from weiss.models import WorldSave; "
            "print(WorldSave.objects.filter(user__username='e2e').delete())")
    env = {**os.environ, "DJANGO_SQLITE_PATH": str(DB)}
    subprocess.run([sys.executable, "manage.py", "shell", "-c", code], cwd=ROOT, env=env, check=True, capture_output=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["checks"]:  # the browser checks: python e2e/harness.py checks [name ...]
        sys.path.insert(0, str(ROOT / "e2e"))
        import checks
        raise SystemExit(checks.main(sys.argv[2:]))
    raise SystemExit("usage: python e2e/harness.py checks [name ...]   (the tutorial run is python e2e/tutorial.py)")
