"""The installable app (weiss.pwa): its manifest, service worker and offline page, and the tags that link them."""
import json

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class ManifestTests(TestCase):
    def test_manifest_is_public_and_points_inside_the_game(self):
        response = self.client.get(reverse("weiss:manifest"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        data = json.loads(response.content)
        scope = reverse("weiss:sets")
        self.assertEqual(data["scope"], scope)
        self.assertTrue(data["start_url"].startswith(scope))
        for shortcut in data["shortcuts"]:
            self.assertTrue(shortcut["url"].startswith(scope))
        self.assertEqual(data["display"], "standalone")

    def test_every_icon_exists(self):
        data = json.loads(self.client.get(reverse("weiss:manifest")).content)
        purposes = {icon["purpose"] for icon in data["icons"]}
        self.assertEqual(purposes, {"any", "maskable"})
        self.assertIn("512x512", {icon["sizes"] for icon in data["icons"]})
        for icon in data["icons"]:
            path = icon["src"].split("/static/", 1)[1]
            self.assertTrue(finders.find(path), icon["src"])
        self.assertTrue(finders.find("weiss/app/icon-180.png"))


class ServiceWorkerTests(TestCase):
    def test_served_as_script_from_the_games_scope_and_never_stale(self):
        response = self.client.get(reverse("weiss:service_worker"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/javascript")
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertEqual(reverse("weiss:service_worker"), reverse("weiss:sets") + "sw.js")
        body = response.content.decode()
        self.assertIn(json.dumps(reverse("weiss:offline")), body)
        self.assertNotIn("%(", body)

    def test_it_leaves_pages_polls_and_audio_alone(self):
        body = self.client.get(reverse("weiss:service_worker")).content.decode()
        self.assertIn('request.method !== "GET"', body)  # actions
        self.assertIn('headers.has("range")', body)  # audio and video
        self.assertNotIn("mp3", body)
        self.assertIn('request.mode === "navigate"', body)  # pages: the network, the offline page if that fails


class OfflinePageTests(TestCase):
    def test_needs_no_login_and_stands_alone(self):
        response = self.client.get(reverse("weiss:offline"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("You're offline", html)
        self.assertNotIn("<link rel=\"stylesheet\"", html)  # nothing else is cached to load
        self.assertNotIn("serviceWorker", html)


class HeadTagTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("app-user", password="pw", is_staff=True)
        self.client.force_login(self.user)

    def test_game_pages_link_the_manifest_and_register_the_worker(self):
        html = self.client.get(reverse("weiss:sets")).content.decode()
        self.assertIn(f'<link rel="manifest" href="{reverse("weiss:manifest")}">', html)
        self.assertIn(reverse("weiss:service_worker"), html)
        self.assertIn("window.top === window", html)  # not from inside the town's play layer
        self.assertIn('content="#f5f2ea" media="(prefers-color-scheme: light)"', html)  # the browser's bar follows the theme

    def test_the_rest_of_the_site_does_not(self):
        html = self.client.get(reverse("dashboard")).content.decode()
        self.assertNotIn('rel="manifest"', html)
        self.assertNotIn("serviceWorker", html)
