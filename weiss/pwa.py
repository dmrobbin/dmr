"""The game as an installable app: its web app manifest, its service worker and the page shown offline.

The app's scope is the game's part of the site (/dashboard/weiss/), so the service worker is served from there and
installing it leaves the rest of the site alone. None of these need a login: the browser fetches the manifest without
cookies, and there's nothing private in them. See docs/round-two-plan.md, item 6.
"""
import json

from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control

# Bump this to make every installed copy drop its cached files on its next visit.
CACHE_VERSION = 1

BACKGROUND = "#0e0f12"  # site.css --bg, so the splash screen matches the first paint


@cache_control(max_age=3600)
def manifest(request):
    scope = reverse("weiss:sets")
    data = {
        "name": "Weiss Schwarz",
        "short_name": "Weiss",
        "description": "Collect, build and duel: Weiss Schwarz cards, the arcade and the town.",
        "id": scope,
        "start_url": reverse("weiss:play_rooms") + "?source=app",
        "scope": scope,
        "display": "standalone",
        "background_color": BACKGROUND,
        "theme_color": BACKGROUND,
        "icons": [
            {"src": static("weiss/app/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("weiss/app/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("weiss/app/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Play", "url": reverse("weiss:play_rooms")},
            {"name": "World", "url": reverse("weiss:world_home")},
            {"name": "Arcade", "url": reverse("weiss:arcade")},
        ],
    }
    return HttpResponse(json.dumps(data), content_type="application/manifest+json")


# The service worker. What it caches, and why:
# - Pages and anything else that isn't a static file (state polls, actions, card art from S3): never. They go to the
#   network as if there were no worker; a page that can't load shows the offline page instead of the browser's error.
# - Scripts and styles: the network first, the cached copy only when offline. Their names don't change between
#   deploys, so serving a cached copy first would run old code against a new page.
# - Images and fonts from the static folder: the cached copy at once, refreshed in the background.
# - Audio and video: never. They're large and fetched in ranges, which a cache can't answer.
SERVICE_WORKER = """
const CACHE = "weiss-v%(version)s";
const OFFLINE = %(offline)s;
const STATIC = %(static)s;
const MAX_ENTRIES = 400;

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add(new Request(OFFLINE, { cache: "reload" })))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((key) => key.startsWith("weiss-") && key !== CACHE).map((key) => caches.delete(key))))
    .then(() => self.clients.claim()));
});

async function trim(cache) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - MAX_ENTRIES; i++) await cache.delete(keys[i]);
}

async function store(request, response) {
  if (!response || !response.ok || response.type !== "basic") return;
  const cache = await caches.open(CACHE);
  await cache.put(request, response);
  trim(cache);
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    store(request, response.clone());
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function cacheFirst(event, request) {
  const cached = await caches.match(request);
  const fresh = fetch(request).then((response) => { store(request, response.clone()); return response; });
  if (cached) { event.waitUntil(fresh.catch(() => {})); return cached; }
  return fresh;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(async () => (await caches.match(OFFLINE)) || Response.error()));
    return;
  }
  if (!url.pathname.startsWith(STATIC) || request.headers.has("range")) return;
  if (/\\.(js|css|json)$/.test(url.pathname)) event.respondWith(networkFirst(request));
  else if (/\\.(png|jpe?g|webp|gif|svg|ico|woff2?|ttf)$/.test(url.pathname)) event.respondWith(cacheFirst(event, request));
});
"""


def service_worker(request):
    body = SERVICE_WORKER % {"version": CACHE_VERSION, "offline": json.dumps(reverse("weiss:offline")),
                             "static": json.dumps(static(""))}
    response = HttpResponse(body, content_type="text/javascript")
    response["Cache-Control"] = "no-cache"  # the browser checks for a new worker on each visit
    return response


def offline(request):
    """Shown by the service worker when a page can't load. It stands alone: no login, no database, inline styles."""
    return render(request, "weiss/offline.html")
