from django.test import TestCase
from django.urls import reverse

from .models import MusicTrack
from .test_profile import player
from .test_world import staff_user
from .world_staff_views import MUSIC_STYLES


class MusicTrackTests(TestCase):
    def setUp(self):
        self.staff = staff_user()
        self.client.force_login(self.staff)

    def page(self):
        return self.client.get(reverse("weiss:world_music"))

    def test_the_page_seeds_each_style_once(self):
        self.page()
        self.page()
        self.assertEqual(MusicTrack.objects.count(), len(MUSIC_STYLES))
        first = MusicTrack.objects.get(key="lofi")
        self.assertEqual((first.name, first.position, first.hidden), ("Lo-fi", 0, False))

    def test_seeding_leaves_existing_rows_as_they_are(self):
        MusicTrack.objects.create(key="lofi", name="Mellow", position=7, hidden=True)
        self.page()
        track = MusicTrack.objects.get(key="lofi")
        self.assertEqual((track.name, track.position, track.hidden), ("Mellow", 7, True))

    def test_rename_saves_the_stripped_name(self):
        self.page()
        self.client.post(reverse("weiss:world_music_rename"), {"key": "jazz", "name": "  Smooth jazz  "})
        self.assertEqual(MusicTrack.objects.get(key="jazz").name, "Smooth jazz")

    def test_a_blank_or_too_long_name_is_refused(self):
        self.page()
        for bad in ("", "   ", "x" * 81):
            self.client.post(reverse("weiss:world_music_rename"), {"key": "jazz", "name": bad})
            self.assertEqual(MusicTrack.objects.get(key="jazz").name, "Jazz")
        self.client.post(reverse("weiss:world_music_rename"), {"key": "jazz", "name": "x" * 80})
        self.assertEqual(len(MusicTrack.objects.get(key="jazz").name), 80)

    def test_an_unknown_key_is_refused(self):
        response = self.client.post(reverse("weiss:world_music_rename"), {"key": "nope", "name": "X"})
        self.assertRedirects(response, reverse("weiss:world_music"))
        self.assertFalse(MusicTrack.objects.filter(key="nope").exists())

    def test_delete_hides_and_restore_brings_it_back(self):
        self.page()
        self.client.post(reverse("weiss:world_music_delete"), {"key": "funk"})
        self.assertTrue(MusicTrack.objects.get(key="funk").hidden)
        self.client.post(reverse("weiss:world_music_restore"), {"key": "funk"})
        self.assertFalse(MusicTrack.objects.get(key="funk").hidden)

    def test_non_staff_are_refused_every_action(self):
        self.page()
        self.client.force_login(player("alice"))
        for name in ("world_music_rename", "world_music_delete", "world_music_restore"):
            response = self.client.post(reverse(f"weiss:{name}"), {"key": "funk", "name": "Y"})
            self.assertEqual(response.status_code, 403, name)
        self.assertFalse(MusicTrack.objects.get(key="funk").hidden)
        self.assertEqual(MusicTrack.objects.get(key="funk").name, "Funk")

    def test_the_page_lists_only_visible_tracks_in_order(self):
        self.page()
        self.client.post(reverse("weiss:world_music_delete"), {"key": "lofi"})
        page = self.page()
        keys = [track["key"] for track in page.context["styles"]]
        self.assertNotIn("lofi", keys)
        self.assertEqual(keys, [key for key, _ in MUSIC_STYLES if key != "lofi"])
        self.assertEqual([track["key"] for track in page.context["deleted"]], ["lofi"])


class OfferedTracksTests(TestCase):
    def test_a_renamed_track_is_offered_under_its_new_name(self):
        from . import music
        music.seed_music_tracks()
        MusicTrack.objects.filter(key="jazz").update(name="Smooth jazz")
        names = {track["key"]: track["name"] for track in music.visible_tracks()}
        self.assertEqual(names["jazz"], "Smooth jazz")

    def test_a_deleted_track_is_not_offered(self):
        from . import music
        music.seed_music_tracks()
        MusicTrack.objects.filter(key="funk").update(hidden=True)
        keys = [track["key"] for track in music.visible_tracks()]
        self.assertNotIn("funk", keys)
        self.assertEqual(keys, [key for key, _ in MUSIC_STYLES if key != "funk"])
