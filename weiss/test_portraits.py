import json
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import portraits
from .models import PlayerProfile
from .test_profile import player


def layer(key, arts, z=1):
    return {"z": z, "key": key, "art": {k: {"src": f"x/{k or 'one'}.webp", "x": 0, "y": 0, "w": 10, "h": 10} for k in arts}}


def part(pid, base, slot, layers, colours=None):
    found = {"id": pid, "base": base, "slot": slot, "name": pid.rsplit("_", 1)[-1].title(), "layers": layers}
    if colours:
        found["colors"] = [{"key": c, "label": c.title(), "swatch": "#888888"} for c in colours]
    return found


SKIN = {"key": "skin", "label": "Skin", "kind": "swatch", "options": [{"key": k, "label": k, "swatch": "#fce4dc"} for k in ("1", "2", "deep")]}


def base(style, label, choices, slots, defaults):
    return {"label": label, "style": style, "size": [100, 120], "credit": {"author": style, "url": f"https://example.com/{style}"},
            "choices": choices, "slots": [{"key": k, "label": k.title(), "required": r} for k, r in slots],
            "always": [], "moods": {}, "defaults": defaults}


MANIFEST = {
    "version": 2,
    "bases": {
        "sutemo_female": base("Sutemo", "Feminine",
                              [SKIN, {"key": "hair", "label": "Hair colour", "kind": "swatch",
                                      "options": [{"key": c, "label": c, "swatch": "#888888"} for c in ("brown", "pink")]}],
                              [("hair_front", True), ("expression", True), ("outfit", True), ("glasses", False)],
                              {"choices": {"skin": "1", "hair": "brown"},
                               "parts": {"hair_front": {"id": "sutemo_female_hair_front_hime", "color": ""},
                                         "expression": {"id": "sutemo_female_expression_smile", "color": ""},
                                         "outfit": {"id": "sutemo_female_outfit_uniform", "color": ""}}}),
        "tainara_male": base("Tainara-P", "Masculine",
                             [SKIN, {"key": "mouth_state", "label": "Mouth", "kind": "list",
                                     "options": [{"key": s, "label": s} for s in ("Smile", "Sad")]}],
                             [("mouth", True), ("outfit", True)],
                             {"choices": {"skin": "2", "mouth_state": "Smile"},
                              "parts": {"mouth": {"id": "tainara_male_mouth_1", "color": ""},
                                        "outfit": {"id": "tainara_male_outfit_hoodie", "color": "2"}}}),
    },
    "parts": [
        part("sutemo_female_hair_front_hime", "sutemo_female", "hair_front", [layer(["hair"], ("brown", "pink"))]),
        part("sutemo_female_expression_smile", "sutemo_female", "expression", [layer(["skin"], ("1", "2", "deep"))]),
        part("sutemo_female_outfit_uniform", "sutemo_female", "outfit", [layer([], ("",))]),
        part("sutemo_female_glasses_red", "sutemo_female", "glasses", [layer([], ("",))]),
        part("tainara_male_mouth_1", "tainara_male", "mouth", [layer(["mouth_state"], ("Smile", "Sad"))]),
        part("tainara_male_outfit_hoodie", "tainara_male", "outfit", [layer(["own"], ("1", "2"))], colours=("1", "2")),
    ],
}


def recipe(**changes):
    r = portraits.default_recipe("sutemo_female")
    r["parts"].update(changes.pop("parts", {}))
    r["choices"].update(changes.pop("choices", {}))
    r.update(changes)
    return r


class FakeManifest(TestCase):
    def setUp(self):
        patcher = mock.patch.object(portraits, "manifest", return_value=MANIFEST)
        patcher.start()
        self.addCleanup(patcher.stop)


class CleanTests(FakeManifest):
    def test_defaults_are_valid_for_every_base(self):
        for key in MANIFEST["bases"]:
            with self.subTest(key):
                self.assertIsNone(portraits.clean(portraits.default_recipe(key))[1])
        self.assertEqual(portraits.default_recipe("nope")["base"], "sutemo_female")

    def test_a_portrait_is_kept_and_empty_slots_dropped(self):
        r = recipe(choices={"skin": "deep", "hair": "pink"}, parts={"glasses": {"id": "sutemo_female_glasses_red"}, "outfit": {"id": "sutemo_female_outfit_uniform", "color": "x"}})
        r["parts"]["glasses"]["color"] = ""
        r["parts"]["hair_front"] = {"id": "sutemo_female_hair_front_hime"}
        cleaned, problem = portraits.clean(r)
        self.assertIsNone(problem)
        self.assertEqual(cleaned["choices"], {"skin": "deep", "hair": "pink"})
        self.assertEqual(cleaned["parts"]["outfit"], {"id": "sutemo_female_outfit_uniform", "color": ""})  # it has no colours

    def test_a_part_in_colours_needs_one_of_them(self):
        r = portraits.default_recipe("tainara_male")
        self.assertIsNone(portraits.clean(r)[1])
        r["parts"]["outfit"]["color"] = "9"
        self.assertIsNone(portraits.clean(r)[0])

    def test_what_cant_be_drawn_is_refused(self):
        cases = {
            "not a dict": "nope",
            "old style, no choices": {"base": "sutemo_female", "parts": {}},
            "unknown base": recipe(base="dragon"),
            "skin not offered": recipe(choices={"skin": "plaid"}),
            "a choice missing": {**recipe(), "choices": {"skin": "1"}},
            "unknown slot": recipe(parts={"aura": {"id": "x"}}),
            "another base's part": recipe(parts={"outfit": {"id": "tainara_male_outfit_hoodie", "color": "1"}}),
            "part in the wrong slot": recipe(parts={"glasses": {"id": "sutemo_female_outfit_uniform"}}),
            "no expression": recipe(parts={"expression": {"id": ""}}),
            "pick not a dict": recipe(parts={"outfit": "sutemo_female_outfit_uniform"}),
        }
        for name, r in cases.items():
            with self.subTest(name):
                cleaned, problem = portraits.clean(r)
                self.assertIsNone(cleaned)
                self.assertTrue(problem)

    def test_credits_name_each_artist_once(self):
        self.assertEqual([c["author"] for c in portraits.credits()], ["Sutemo", "Tainara-P"])


class EditorTests(FakeManifest):
    def setUp(self):
        super().setUp()
        self.user = player("alice")
        self.client.force_login(self.user)
        self.url = reverse("weiss:profile_portrait")

    def test_the_page_starts_from_the_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["recipe"], portraits.default_recipe())
        self.assertContains(response, 'data-saved=""')
        self.assertContains(response, "Tainara-P")  # credited

    def test_saving_and_removing(self):
        response = self.client.post(self.url, {"recipe": json.dumps(recipe(choices={"skin": "deep"}))})
        self.assertRedirects(response, reverse("weiss:profile"), fetch_redirect_response=False)
        self.assertEqual(PlayerProfile.objects.get(user=self.user).portrait["choices"]["skin"], "deep")
        page = self.client.get(self.url)
        self.assertEqual(page.context["recipe"]["choices"]["skin"], "deep")
        self.assertContains(page, 'data-saved="1"')
        profile = self.client.get(reverse("weiss:profile"))
        self.assertContains(profile, "Change portrait")
        self.assertContains(profile, "data-portrait=")
        self.client.post(self.url, {"remove": "1"})
        self.assertEqual(PlayerProfile.objects.get(user=self.user).portrait, {})

    def test_a_bad_portrait_isnt_saved(self):
        for body in ({"recipe": "{oops"}, {"recipe": json.dumps(recipe(choices={"skin": "plaid"}))}):
            with self.subTest(body):
                response = self.client.post(self.url, body)
                self.assertRedirects(response, self.url, fetch_redirect_response=False)
                self.assertEqual(PlayerProfile.objects.get(user=self.user).portrait, {})

    def test_without_parts_the_page_says_so(self):
        with mock.patch.object(portraits, "manifest", side_effect=portraits.ManifestMissing):
            self.assertRedirects(self.client.get(self.url), reverse("weiss:profile"), fetch_redirect_response=False)
            self.assertNotContains(self.client.get(reverse("weiss:profile")), "Make your portrait")
