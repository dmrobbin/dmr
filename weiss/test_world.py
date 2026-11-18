import json
import random
from collections import Counter

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import buffs, world, world_views
from .lists import editable_lists
from .models import Card, CardList, CpuProfile, WorldPlace, WorldSave, WorldSettings
from .test_profile import add_card, player


class TownTestPageTests(TestCase):
    def setUp(self):
        self.url = reverse("weiss:world_test")
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        deck = CardList.objects.create(user=self.staff, name="CPU deck")
        self.ready = CpuProfile.objects.create(name="Akari", finalized=True, deck=deck, avatar_card=add_card(), intro_text="Let's go!")
        self.draft = CpuProfile.objects.create(name="Draft")  # not finalized, no picture: not in town

    def test_only_staff_can_open_it(self):
        self.client.force_login(player("alice"))
        self.assertNotEqual(self.client.get(self.url).status_code, 200)

    def test_it_offers_the_finalized_cpus_with_their_pictures_and_schedules(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.context["world"]
        self.assertEqual([c["name"] for c in data["cpus"]], ["Akari"])
        akari = data["cpus"][0]
        self.assertTrue(akari["duel"])
        self.assertEqual(akari["portraits"]["kind"], "card")
        self.assertEqual(akari["intro"], "Let's go!")
        places = {p["key"] for p in data["places"]}
        for rule in akari["schedule"]:
            self.assertIn(rule["place"], places)
            self.assertTrue(set(rule["days"]) <= set(range(7)) and set(rule["slots"]) <= set(range(4)))
        self.assertTrue(all(len(p["backdrops"]) == 4 for p in data["places"]))
        self.assertContains(response, reverse("weiss:play_vs_cpu"))

    def test_a_cpus_schedule_is_the_same_every_time(self):
        self.assertEqual(world_views.schedule_for(self.ready), world_views.schedule_for(self.ready))
        self.assertEqual(world.cpu_portraits(self.draft), {"kind": "none"})


# ---------------------------------------------------------------- Saves

SET = 7
LOADOUT_FIELDS = {f"loadout_{b}": 0 for b in ("climax_pack", "level_pack", "color_pack", "lucky_pack", "wild_pack", "climax_pick")}


def make_set(expansion_id=SET, commons=60, climaxes=12, uncommons=20, rares=10, foils=10):
    """A set with every rarity a pack needs: big enough to start a save with, at the default sizes."""
    cards, n = [], 0
    for rarity, count, kind in (("C", commons, "Character"), ("CC", climaxes, "Climax"), ("U", uncommons, "Character"),
                                ("R", rares, "Character"), ("SR", foils, "Character")):
        for _ in range(count):
            n += 1
            cards.append(Card(serial_number=f"S{expansion_id}/T-{n:03}", name=f"Card {expansion_id}-{n}", expansion=f"Set {expansion_id}",
                              expansion_id=expansion_id, card_type=kind, level=None if kind == "Climax" else n % 4, rarity=rarity))
    Card.objects.bulk_create(cards)
    return list(Card.objects.filter(expansion_id=expansion_id).order_by("serial_number"))


def staff_user(name="staff"):
    return User.objects.create_user(name, password="x", is_staff=True)


class WorldSaveTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        make_set(8, commons=10, climaxes=2, uncommons=2, rares=1, foils=1)  # too small to start with
        self.user = staff_user()
        WorldSettings.objects.create(pk=1, start_packs=3, loadout={"climax_pack": 1, "climax_pick": 1}, start_money=500)

    def start(self, slot=1):
        return world.start(self.user, slot, SET, rng=random.Random(1))

    def test_only_big_enough_sets_are_offered(self):
        self.assertEqual([entry["id"] for entry in world.offered_sets()], [SET])

    def test_a_new_save_has_its_packs_coins_specialty_packs_and_an_empty_deck(self):
        save = self.start()
        self.assertEqual((save.packs, save.money, save.set_name, save.turn), (3, 500, f"Set {SET}", 0))
        self.assertEqual(sorted(r["buff"] for r in save.rewards), ["climax_pack", "climax_pick"])
        self.assertEqual(save.deck.world_save, save)
        self.assertEqual((save.day, save.weekday, save.time_of_day), (1, "Monday", "Morning"))
        self.assertEqual(world.step(save), "packs")

    def test_a_slot_takes_one_save_and_the_set_must_be_offered(self):
        self.start()
        for slot, expansion_id in ((1, SET), (4, SET), (2, 8), (2, 999)):
            with self.subTest(slot=slot, set=expansion_id):
                with self.assertRaises(ValueError):
                    world.start(self.user, slot, expansion_id)

    def test_opening_packs(self):
        save = self.start()
        opening = world.open_packs(save, 2, random.Random(2))
        self.assertEqual(len(opening["packs"]), 2)
        self.assertEqual((save.packs, save.opened, sum(save.pool.values())), (1, 2, 16))
        self.assertTrue(all(Card.objects.get(pk=pk).expansion_id == SET for pk in save.pool))
        for count in (0, 2):
            with self.subTest(count):
                with self.assertRaises(ValueError):
                    world.open_packs(save, count)

    def test_claiming_specialty_packs(self):
        save = self.start()
        pack = next(r for r in save.rewards if r["buff"] == "climax_pack")
        self.assertTrue(world.claim(save, pack["key"], {"set": str(SET)}, random.Random(3)))
        climaxes = {c.pk for c in self.cards if c.card_type == "Climax"}
        self.assertTrue(save.pool and all(int(pk) in climaxes for pk in save.pool))
        pick = next(r for r in save.rewards if r["buff"] == "climax_pick")
        with self.assertRaises(ValueError):
            world.claim(save, pick["key"], {"card": str(self.cards[0].pk)})  # not a climax
        chosen = next(c for c in self.cards if c.card_type == "Climax")
        before = save.pool.get(str(chosen.pk), 0)
        self.assertFalse(world.claim(save, pick["key"], {"card": str(chosen.pk)}))
        self.assertEqual(save.pool[str(chosen.pk)], before + buffs.CLIMAX_COPIES)
        self.assertEqual(save.rewards, [])
        with self.assertRaises(ValueError):
            world.claim(save, pick["key"], {"card": str(chosen.pk)})  # claimed already

    def legal_pool(self, save):
        """Every card of the set opened 4 times; returns a legal deck from it: 8 climaxes and 42 others."""
        save.pool = {str(c.pk): 4 for c in self.cards}
        save.packs, save.rewards = 0, []
        save.save()
        climaxes = [c for c in self.cards if c.card_type == "Climax"]
        others = [c for c in self.cards if c.card_type != "Climax"]
        return {c.pk: 4 for c in climaxes[:2]} | {c.pk: 3 for c in others[:14]}

    def test_the_deck_is_built_from_what_was_opened(self):
        save = self.start()
        legal = self.legal_pool(save)
        climax = next(c for c in self.cards if c.card_type == "Climax")
        spare = [c for c in self.cards if c.card_type != "Climax" and c.pk not in legal]
        self.assertIn("opened", world.save_deck(save, {self.cards[0].pk: 5}))  # more than opened
        self.assertIn("50", world.save_deck(save, {**legal, spare[0].pk: 1}))  # too many cards
        self.assertTrue(world.save_deck(save, {c.pk: 3 for c in self.cards if c.card_type == "Climax"}))  # too many climaxes
        self.assertIsNone(world.save_deck(save, {climax.pk: 2}))  # short of a deck while it's built: saved, but not ready
        self.assertIn("50", world.deck_problem(save))
        self.assertEqual(world.step(save), "deck")
        self.assertIsNone(world.save_deck(save, legal))
        self.assertIsNone(world.deck_problem(save))
        self.assertEqual(world.step(save), "ready")

    def test_four_copies_of_a_name_at_most_to_duel(self):
        save = self.start()
        legal = self.legal_pool(save)
        twin = next(c for c in self.cards if c.card_type != "Climax" and c.pk not in legal)
        named = next(pk for pk, n in legal.items() if n == 3)
        Card.objects.filter(pk=twin.pk).update(name=Card.objects.get(pk=named).name)
        deck = dict(legal)
        other = next(pk for pk, n in deck.items() if n == 3 and pk != named)
        deck[other] -= 2
        deck[twin.pk] = 2  # the same name as `named`: 3 + 2 copies
        self.assertIsNone(world.save_deck(save, deck))
        self.assertIn("4 copies", world.deck_problem(save))

    def test_a_pool_that_cant_make_a_deck_says_so(self):
        save = self.start()
        save.packs, save.rewards = 0, []
        save.pool = {str(c.pk): 1 for c in self.cards[:20]}
        self.assertIn("climax", world.pool_shortfall(save))
        self.legal_pool(save)
        self.assertIsNone(world.pool_shortfall(save))
        save.packs = 1
        self.assertIsNone(world.pool_shortfall(save))  # more to come

    def test_several_decks_from_the_same_cards(self):
        save = self.start()
        legal = self.legal_pool(save)
        first = save.deck
        second = world.new_deck(save, "  Second   deck ")
        self.assertEqual(second.name, "Second deck")
        self.assertEqual(save.deck, first)  # making one doesn't equip it
        for name in ("", "second DECK"):
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    world.new_deck(save, name)
        self.assertIsNone(world.save_deck(save, legal, second))  # the same cards can be in every deck
        self.assertIsNone(world.save_deck(save, legal, first))
        copy = world.new_deck(save, "Copy", copy_from=second)
        self.assertEqual(copy.card_count(), 50)
        self.assertEqual(world.decks(save)[0], first)  # the equipped one first
        world.save_deck(save, {}, first)
        self.assertEqual(world.step(save), "deck")  # the equipped deck's empty
        world.equip(save, second)
        self.assertEqual(world.step(save), "ready")
        world.delete_deck(save, second)
        self.assertIn(save.deck, (first, copy))
        world.delete_deck(save, first if save.deck != first else copy)
        with self.assertRaises(ValueError):
            world.delete_deck(save, save.deck)  # the last one stays
        while save.decks.count() < world.MAX_DECKS:
            world.new_deck(save, f"More {save.decks.count()}")
        with self.assertRaises(ValueError):
            world.new_deck(save, "Too many")

    def test_world_decks_stay_out_of_other_lists_and_go_with_the_save(self):
        save = self.start()
        mine = CardList.objects.create(user=self.user, name="Mine")
        self.assertEqual(list(CardList.objects.players(self.user)), [mine])
        self.assertNotIn(save.deck, editable_lists(self.user))
        deck_id = save.deck.pk
        save.delete()
        self.assertFalse(CardList.objects.filter(pk=deck_id).exists())


class WorldPageTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.client.force_login(self.user)
        WorldSettings.objects.create(pk=1, start_packs=2, loadout={"lucky_pack": 1})

    def test_players_cant_open_world_mode_yet(self):
        self.client.force_login(player("alice"))
        self.assertNotEqual(self.client.get(reverse("weiss:world_home")).status_code, 200)

    def test_a_new_game_from_choosing_a_set_to_building_a_deck(self):
        self.assertContains(self.client.get(reverse("weiss:world_home")), "New game", count=3)
        self.assertContains(self.client.get(reverse("weiss:world_new", args=[2])), f"Set {SET}")
        response = self.client.post(reverse("weiss:world_new", args=[2]), {"set": SET})
        self.assertRedirects(response, reverse("weiss:world_save", args=[2]))
        page = self.client.get(reverse("weiss:world_save", args=[2]))
        self.assertContains(page, "2 packs of")
        self.assertContains(page, "Lucky pack")
        response = self.client.post(reverse("weiss:world_open", args=[2]), {"count": 2})
        self.assertRedirects(response, reverse("weiss:world_opened", args=[2]))
        self.assertContains(self.client.get(reverse("weiss:world_opened", args=[2])), f"Set {SET}")
        save = WorldSave.objects.get(user=self.user, slot=2)
        response = self.client.post(reverse("weiss:world_claim", args=[2]), {"key": save.rewards[0]["key"], "set": SET})
        self.assertRedirects(response, reverse("weiss:world_opened", args=[2]))
        save.refresh_from_db()
        self.assertEqual((save.packs, save.rewards, sum(save.pool.values())), (0, [], 24))
        builder = reverse("weiss:world_deck_edit", args=[2, save.deck_id])
        self.assertRedirects(self.client.get(reverse("weiss:world_deck", args=[2])), builder)  # the equipped deck's
        self.assertContains(self.client.get(builder), "Back to your save")
        some = next(iter(save.pool))
        response = self.client.post(builder, {"deck": json.dumps({some: 1})})
        self.assertRedirects(response, builder)
        self.assertEqual(save.deck.card_count(), 1)
        self.client.post(builder, {"deck": json.dumps({some: 99})})
        self.assertEqual(save.deck.card_count(), 1)  # not saved: more than opened

    def test_decks_made_renamed_equipped_and_deleted_from_the_page(self):
        save = world.start(self.user, 1, SET)
        first = save.deck
        save_url = reverse("weiss:world_save", args=[1]) + "#decks"
        response = self.client.post(reverse("weiss:world_deck_new", args=[1]), {"name": "Aggro", "copy": ""})
        second = save.decks.get(name="Aggro")
        self.assertRedirects(response, reverse("weiss:world_deck_edit", args=[1, second.pk]))
        self.assertContains(self.client.get(reverse("weiss:world_save", args=[1])), "Aggro")
        self.assertRedirects(self.client.post(reverse("weiss:world_deck_rename", args=[1, second.pk]), {"name": "Control"}),
                             save_url, fetch_redirect_response=False)
        second.refresh_from_db()
        self.assertEqual(second.name, "Control")
        self.client.post(reverse("weiss:world_deck_equip", args=[1, second.pk]))
        save.refresh_from_db()
        self.assertEqual(save.deck, second)
        self.client.post(reverse("weiss:world_deck_delete", args=[1, second.pk]))
        save.refresh_from_db()
        self.assertEqual(save.deck, first)  # the other one, equipped instead
        self.client.post(reverse("weiss:world_deck_delete", args=[1, first.pk]))
        self.assertTrue(save.decks.filter(pk=first.pk).exists())  # a save keeps one deck

    def test_another_saves_deck_cant_be_touched(self):
        mine = world.start(self.user, 1, SET)
        theirs = world.start(staff_user("other"), 1, SET)
        for name in ("world_deck_edit", "world_deck_equip", "world_deck_delete", "world_deck_rename"):
            with self.subTest(name):
                url = reverse(f"weiss:{name}", args=[1, theirs.deck_id])
                (self.client.get if name == "world_deck_edit" else self.client.post)(url, {"name": "Mine now"})
        theirs.refresh_from_db()
        mine.refresh_from_db()
        self.assertEqual((theirs.deck.name, mine.deck_id != theirs.deck_id), ("Deck 1", True))
        self.assertTrue(CardList.objects.filter(pk=theirs.deck_id).exists())

    def test_a_slot_is_deleted_only_when_its_name_is_typed(self):
        world.start(self.user, 1, SET)
        self.client.post(reverse("weiss:world_delete", args=[1]), {"confirm": "yes"})
        self.assertTrue(WorldSave.objects.filter(user=self.user, slot=1).exists())
        self.client.post(reverse("weiss:world_delete", args=[1]), {"confirm": "slot 1"})
        self.assertFalse(WorldSave.objects.filter(user=self.user, slot=1).exists())

    def test_another_players_slot_is_theirs(self):
        world.start(staff_user("other"), 1, SET)
        self.assertRedirects(self.client.get(reverse("weiss:world_save", args=[1])), reverse("weiss:world_home"))

    def test_staff_settings(self):
        self.assertContains(self.client.get(reverse("weiss:cpu_home") + "?tab=world"), "Starting packs")
        fields = {"start_packs": 15, "start_money": 800, "pack_price": 250, "specialty_price": 900, "card_price": 5000, "win_payout": 150,
                  "first_win_bonus": 50, "ranks": "New: 0\nPal: 10", **LOADOUT_FIELDS}
        self.client.post(reverse("weiss:world_settings"), {**fields, "loadout_climax_pick": 2})
        settings = WorldSettings.current()
        self.assertEqual((settings.start_packs, settings.start_money, settings.loadout), (15, 800, {"climax_pick": 2}))
        self.assertEqual((world.specialty_price(), world.card_price()), (900, 5000))
        self.assertEqual(world.rank_names(), ["New", "Pal"])
        self.client.post(reverse("weiss:world_settings"), {**fields, "start_packs": 0})  # nothing to build from: refused
        self.assertEqual(WorldSettings.current().start_packs, 15)


class TownTests(TestCase):
    """Phase 2: places and time, kept by the server (the first places come from a migration)."""

    def setUp(self):
        make_set()
        self.user = staff_user()
        self.client.force_login(self.user)
        self.save = world.start(self.user, 1, SET)

    def test_a_new_save_starts_at_the_first_place_and_can_go_to_every_open_one(self):
        keys = [p.key for p in world.places(self.save)]
        self.assertEqual(keys[0], "plaza")
        self.assertEqual(world.place_of(self.save).key, "plaza")
        world.travel(self.save, "beach")
        self.assertEqual((self.save.place, world.place_of(self.save).key), ("beach", "beach"))
        with self.assertRaises(ValueError):
            world.travel(self.save, "the moon")

    def test_a_locked_place_opens_with_its_flag(self):
        WorldPlace.objects.filter(key="shrine").update(unlock_flag="shrine_key")
        self.assertNotIn("shrine", [p.key for p in world.places(self.save)])
        with self.assertRaises(ValueError):
            world.travel(self.save, "shrine")
        self.save.flags["shrine_key"] = True
        world.travel(self.save, "shrine")
        self.assertEqual(self.save.place, "shrine")

    def test_waiting_moves_the_day_on(self):
        self.save.today = {"talked": [1]}
        for expected in ("Noon", "Evening", "Night"):
            world.wait(self.save)
            self.assertEqual(self.save.time_of_day, expected)
        self.assertEqual(self.save.today, {"talked": [1]})
        world.wait(self.save)
        self.assertEqual((self.save.day, self.save.weekday, self.save.time_of_day, self.save.today), (2, "Tuesday", "Morning", {}))

    def test_the_town_as_the_page_gets_it(self):
        for _ in range(3):
            world.wait(self.save)  # night: the plaza is the city by night
        town = world.town(self.save)
        self.assertEqual((town["place"]["key"], town["place"]["backdrop"], town["time"], town["time_name"]), ("plaza", "city", 3, "Night"))
        self.assertEqual(len(town["places"]), 12)  # the town test's eight, the card shop, and three secluded places
        self.assertEqual([p["key"] for p in town["places"] if p["here"]], ["plaza"])
        self.assertFalse(town["deck_ready"])

    def test_the_town_page_and_its_moves(self):
        page = self.client.get(reverse("weiss:world_town", args=[1]))
        self.assertContains(page, "Plaza")
        self.assertContains(page, "isn't ready to duel")
        version = self.client.get(reverse("weiss:world_town_state", args=[1])).json()["version"]
        moved = self.client.post(reverse("weiss:world_travel", args=[1]), {"place": "cafe", "version": version}).json()
        self.assertEqual(moved["town"]["place"]["key"], "cafe")
        stale = self.client.post(reverse("weiss:world_wait", args=[1]), {"version": version})  # what another tab saw
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["town"]["time_name"], "Morning")  # nothing happened
        waited = self.client.post(reverse("weiss:world_wait", args=[1]), {"version": moved["town"]["version"]}).json()
        self.assertEqual((waited["town"]["time_name"], waited["said"]), ("Noon", "Noon."))
        bad = self.client.post(reverse("weiss:world_travel", args=[1]), {"place": "nowhere", "version": waited["town"]["version"]})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.json()["town"]["place"]["key"], "cafe")

    def test_another_players_town_isnt_reachable(self):
        self.client.force_login(staff_user("other"))
        self.assertEqual(self.client.post(reverse("weiss:world_wait", args=[1]), {"version": 0}).status_code, 404)
        self.save.refresh_from_db()
        self.assertEqual(self.save.turn, 0)


# ---------------------------------------------------------------- Phase 3: schedules, duels and the shop

from unittest import mock

from . import play
from .models import CardListEntry, CpuSchedule, GameRoom


def give_cpu(name, cards, finalized=True):
    """A CPU that can duel, with a full deck of the set's cards."""
    owner = User.objects.get_or_create(username="cpu-maker", defaults={"is_staff": True})[0]
    deck = CardList.objects.create(user=owner, name=f"{name}'s deck", reserved_for_cpu=True)
    climaxes = [c for c in cards if c.card_type == "Climax"][:2]
    others = [c for c in cards if c.card_type != "Climax"][:14]
    CardListEntry.objects.bulk_create([CardListEntry(card_list=deck, card=c, quantity=4) for c in climaxes]
                                      + [CardListEntry(card_list=deck, card=c, quantity=3) for c in others])
    return CpuProfile.objects.create(name=name, finalized=finalized, deck=deck)


def everywhere_rule(cpu, place="plaza", **fields):
    """A rule that always puts the CPU at a place, unless told otherwise."""
    return CpuSchedule.objects.create(cpu=cpu, place=WorldPlace.objects.get(key=place), days=fields.pop("days", list(range(7))),
                                      times=fields.pop("times", list(range(4))), **fields)


class WhereaboutsTests(TestCase):
    """Who's where: a fresh draw each day from the CPUs' haunts, within the town's caps."""

    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.cinder = give_cpu("Cinder", self.cards)

    def crowd(self, n, places=None):
        """n more CPUs, each haunting these places (all but the shop) every day at every time."""
        keys = places or list(WorldPlace.objects.filter(shop=False).values_list("key", flat=True))
        made = []
        for i in range(n):
            cpu = give_cpu(f"Extra {i}", self.cards)
            for key in keys:
                everywhere_rule(cpu, key)
            made.append(cpu)
        return made

    def test_a_haunt_holds_on_its_days_and_times(self):
        everywhere_rule(self.cinder, "beach", days=[1, 4], times=[3])  # Tue and Fri nights
        found = {turn for turn in range(28) if self.cinder.pk in world.whereabouts(self.save, turn)}
        self.assertEqual(found, {1 * 4 + 3, 4 * 4 + 3})
        self.assertEqual(world.whereabouts(self.save, 7)[self.cinder.pk].place.key, "beach")

    def test_never_more_than_two_at_a_place_or_ten_in_town(self):
        self.crowd(30)
        for turn in range(28):
            out = world.whereabouts(self.save, turn)
            per_place = Counter(rule.place_id for rule in out.values())
            self.assertLessEqual(max(per_place.values()), world.MAX_PER_PLACE)
            self.assertTrue(world.MIN_ON_STAGE <= len(out) <= world.MAX_ON_STAGE, len(out))
        self.crowd(5, ["plaza"])
        self.assertLessEqual(sum(rule.place.key == "plaza" for rule in world.whereabouts(self.save, 0).values()), 2)

    def test_the_draw_is_settled_for_a_save_and_fresh_each_day(self):
        self.crowd(30)
        days = [[sorted(world.whereabouts(self.save, day * 4 + time)) for time in range(4)] for day in range(7)]
        self.assertEqual(days, [[sorted(world.whereabouts(self.save, day * 4 + time)) for time in range(4)] for day in range(7)])
        self.assertEqual(len({tuple(day[0]) for day in days}), 7)  # every morning a different crowd
        other = world.start(staff_user("other"), 1, SET)
        self.assertNotEqual(days[0], [sorted(world.whereabouts(other, time)) for time in range(4)])

    def test_once_a_day_is_once_at_most(self):
        everywhere_rule(self.cinder, "cafe", times=[0, 1, 3], once_per_day=True)
        for day in range(7):
            times = [t for t in range(4) if self.cinder.pk in world.whereabouts(self.save, day * 4 + t)]
            self.assertEqual(len(times), 1)
            self.assertIn(times[0], [0, 1, 3])

    def test_a_haunt_can_wait_for_a_rank_without_moving_anyone_else(self):
        everywhere_rule(self.cinder, "plaza", min_rank=2)
        others = self.crowd(15, ["cafe"])  # two of them at the café at a time, and Cinder sure to be drawn
        before = {turn: {cpu: rule.pk for cpu, rule in world.whereabouts(self.save, turn).items()} for turn in range(8)}
        self.assertFalse(any(self.cinder.pk in out for out in before.values()))
        self.save.relations[str(self.cinder.pk)] = {"points": 45}  # a Friend
        after = {turn: {cpu: rule.pk for cpu, rule in world.whereabouts(self.save, turn).items()} for turn in range(8)}
        self.assertTrue(any(self.cinder.pk in out for out in after.values()))
        for turn in range(8):
            self.assertEqual({k: v for k, v in after[turn].items() if k != self.cinder.pk}, before[turn])
        self.assertTrue(others)

    def test_only_cpus_that_can_duel_appear(self):
        draft = give_cpu("Draft", self.cards, finalized=False)
        everywhere_rule(draft)
        everywhere_rule(self.cinder)
        self.assertEqual([cpu.name for cpu, _ in world.present(self.save)], ["Cinder"])
        self.assertEqual(world.present(self.save, "beach"), [])

    def test_starter_schedules_for_cpus_without_any(self):
        everywhere_rule(self.cinder)
        give_cpu("Katara", self.cards)
        self.assertEqual(world.starter_schedules(), 1)
        self.assertEqual(CpuSchedule.objects.filter(cpu__name="Katara").count(), 3)
        self.assertFalse(CpuSchedule.objects.filter(cpu__name="Katara", place__shop=True).exists())
        self.assertEqual(world.starter_schedules(), 0)

    def test_villains_keep_to_secluded_places_after_dark(self):
        villain = give_cpu("Makima", self.cards)
        villain.temperament = "villain"
        villain.save()
        world.starter_schedules([villain])
        haunts = list(villain.schedule.select_related("place"))
        dark = [rule for rule in haunts if not rule.min_rank]
        self.assertTrue(dark and all(rule.place.secluded and set(rule.times) <= {2, 3} for rule in dark))
        daytime = [rule for rule in haunts if rule.min_rank]
        self.assertEqual([(rule.place.secluded, rule.min_rank) for rule in daytime], [(False, 2)])


class DuelTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.save.pool = {str(c.pk): 4 for c in self.cards}
        self.save.packs, self.save.rewards = 0, []
        self.save.save()
        climaxes = [c for c in self.cards if c.card_type == "Climax"][:2]
        others = [c for c in self.cards if c.card_type != "Climax"][:14]
        world.save_deck(self.save, {c.pk: 4 for c in climaxes} | {c.pk: 3 for c in others})
        self.cinder = give_cpu("Cinder", self.cards)
        self.rule = everywhere_rule(self.cinder, stake=300)
        WorldSettings.objects.update_or_create(pk=1, defaults={"win_payout": 200, "first_win_bonus": 100})

    def finish(self, room, won):
        over = {"winner": str(room.host_id if won else room.guest_id), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over  # as the game has it when it ends
        room.save(update_fields=["state"])
        world.game_finished(room, over)
        self.save.refresh_from_db()

    def test_a_duel_is_a_game_against_someone_here(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.assertEqual((room.world_save, room.cpu_profile, room.world_stake, room.status), (self.save, self.cinder, 0, GameRoom.Status.PLAYING))
        self.assertEqual(world.live_duel(self.save), room)
        with self.assertRaises(ValueError):
            world.start_duel(self.save, self.cinder.pk)  # one at a time
        with self.assertRaises(ValueError):
            world.wait(self.save)  # time stays put until it's over

    def test_a_duel_needs_them_here_and_a_ready_deck(self):
        world.travel(self.save, "beach")
        with self.assertRaises(ValueError):
            world.start_duel(self.save, self.cinder.pk)
        world.travel(self.save, "plaza")
        world.save_deck(self.save, {})
        with self.assertRaises(ValueError):
            world.start_duel(self.save, self.cinder.pk)

    def test_a_win_pays_and_uses_up_the_time(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        self.assertEqual((self.save.money, self.save.turn), (1000 + 200 + 100, 1))
        result = world.duel_result(self.save)
        self.assertEqual((result["won"], result["coins"], result["first"]), (True, 300, True))
        self.assertIsNone(world.duel_result(self.save))  # said once
        self.finish(room, won=True)  # the same game again: nothing more
        self.assertEqual(self.save.money, 1300)
        second = world.start_duel(self.save, self.cinder.pk)
        self.finish(second, won=True)
        self.assertEqual(self.save.money, 1300 + 200)  # not the day's first win

    def test_a_loss_only_uses_up_the_time(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=False)
        self.assertEqual((self.save.money, self.save.turn, self.save.flags["last_duel"]["won"]), (1000, 1, False))

    def test_high_stakes(self):
        room = world.start_duel(self.save, self.cinder.pk, high_stakes=True)
        self.save.refresh_from_db()
        self.assertEqual((room.world_stake, self.save.money), (300, 700))  # paid up front
        self.finish(room, won=True)
        self.assertEqual(self.save.money, 700 + 200 + 100 + 600)
        lost = world.start_duel(self.save, self.cinder.pk, high_stakes=True)
        self.finish(lost, won=False)
        self.assertEqual(self.save.money, 1600 - 300)  # the fee's gone
        self.save.money = 100
        with self.assertRaises(ValueError):
            world.start_duel(self.save, self.cinder.pk, high_stakes=True)  # can't afford it
        self.rule.stake = 0
        self.rule.save()
        with self.assertRaises(ValueError):
            world.start_duel(self.save, self.cinder.pk, high_stakes=True)  # not offered

    def test_the_game_hands_its_end_to_world_mode(self):
        room = world.start_duel(self.save, self.cinder.pk)
        over = {"winner": str(room.host_id), "loser": str(room.guest_id), "reason": "level", "rematch": []}
        with mock.patch.object(world, "game_finished") as finished, mock.patch.object(play.scoring, "win_score", return_value={"total": 10}):
            play.game_ended(room, over)
        finished.assert_called_once_with(room, over)

    def test_a_town_duel_cant_be_rematched_or_reset(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.client.force_login(self.user)
        for name in ("play_start", "play_reset"):
            with self.subTest(name):
                self.client.post(reverse(f"weiss:{name}", args=[room.pk]))
                room.refresh_from_db()
                self.assertEqual(room.status, GameRoom.Status.PLAYING)

    def test_the_duel_page_flow(self):
        self.client.force_login(self.user)
        town = self.client.get(reverse("weiss:world_town_state", args=[1])).json()
        self.assertEqual([p["name"] for p in town["people"]], ["Cinder"])
        self.assertEqual(town["people"][0]["stake"], 300)
        answer = self.client.post(reverse("weiss:world_duel", args=[1]), {"cpu": self.cinder.pk, "stakes": "0", "version": town["version"]}).json()
        room = GameRoom.objects.get(world_save=self.save)
        self.assertEqual(answer["go"], reverse("weiss:play_room", args=[room.pk]))
        self.assertEqual(answer["town"]["duel"]["cpu"], "Cinder")
        self.finish(room, won=True)
        page = self.client.get(reverse("weiss:world_town", args=[1]))
        self.assertTrue(page.context["result"]["won"])
        self.assertIsNone(self.client.get(reverse("weiss:world_town", args=[1])).context["result"])  # shown once


class ShopTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        make_set(9)
        self.user = staff_user()
        self.client.force_login(self.user)
        self.save = world.start(self.user, 1, SET)
        WorldSettings.objects.update_or_create(pk=1, defaults={"pack_price": 250})

    def test_the_shelves_have_the_saves_set_and_change_by_day(self):
        stock = world.shop_stock(self.save)
        self.assertEqual(stock[0]["id"], SET)
        self.assertEqual({s["id"] for s in stock}, {SET, 9})
        self.assertEqual(stock, world.shop_stock(self.save))

    def test_buying_packs_at_the_shop(self):
        with self.assertRaises(ValueError):
            world.buy_packs(self.save, SET, 1)  # not at the shop
        world.travel(self.save, "shop")
        before = sum(self.save.pool.values())
        world.buy_packs(self.save, 9, 2)
        self.assertEqual((self.save.money, sum(self.save.pool.values()) - before), (1000 - 500, 16))
        self.assertTrue(self.save.last_opening["bought"])
        for expansion_id, count in ((SET, 5), (12345, 1), (SET, 0)):
            with self.subTest(set=expansion_id, count=count):
                with self.assertRaises(ValueError):
                    world.buy_packs(self.save, expansion_id, count)  # can't afford 5; not stocked; none

    def test_the_shop_in_the_town_and_buying_from_it(self):
        world.travel(self.save, "shop")
        town = self.client.get(reverse("weiss:world_town_state", args=[1])).json()
        self.assertTrue(town["place"]["shop"])
        self.assertEqual(town["shop"]["price"], 250)
        response = self.client.post(reverse("weiss:world_buy", args=[1]), {"set": SET, "count": 1})
        self.assertRedirects(response, reverse("weiss:world_opened", args=[1]))
        self.assertContains(self.client.get(reverse("weiss:world_opened", args=[1])), "Back to the town")


class ShopSpecialtiesAndCardsTests(TestCase):
    """The shop's specialty packs and single cards, and each set's cover."""

    def setUp(self):
        self.cards = make_set()
        make_set(9)
        self.user = staff_user()
        self.client.force_login(self.user)
        self.save = world.start(self.user, 1, SET)
        WorldSettings.objects.update_or_create(pk=1, defaults={"specialty_price": 300, "card_price": 400})
        self.save.money = 1000
        self.save.save()

    def test_a_sets_cover_is_the_lowest_number_of_its_main_print_run(self):
        Card.objects.create(serial_number="AAA/P-001", name="Promo", expansion="Set 7", expansion_id=SET, rarity="PR")
        self.assertEqual(world.set_cover(SET), self.cards[0].pk)
        self.assertIsNone(world.set_cover(12345))

    def test_the_single_cards_are_rares_and_better_and_change_by_day(self):
        offered = world.shop_cards(self.save)
        self.assertEqual(len(offered), world.SHOP_CARDS)
        self.assertTrue(all(card.rarity in ("R", "SR") for card in offered))
        self.assertEqual(offered, world.shop_cards(self.save))
        days = {tuple(card.pk for card in world.shop_cards(self.save))}
        for _ in range(3):
            self.save.turn += 4
            days.add(tuple(card.pk for card in world.shop_cards(self.save)))
        self.assertGreater(len(days), 1)

    def test_buying_a_single_card(self):
        card = world.shop_cards(self.save)[0]
        with self.assertRaises(ValueError):
            world.buy_card(self.save, card.pk)  # not at the shop
        world.travel(self.save, "shop")
        before = self.save.pool.get(str(card.pk), 0)
        world.buy_card(self.save, card.pk)
        self.assertEqual((self.save.money, self.save.pool[str(card.pk)] - before), (600, 1))
        with self.assertRaisesRegex(ValueError, "already"):
            world.buy_card(self.save, card.pk)  # one of each a day
        with self.assertRaisesRegex(ValueError, "doesn't have"):
            world.buy_card(self.save, self.cards[0].pk)  # a common: never on offer
        self.save.money = 100
        with self.assertRaisesRegex(ValueError, "costs 400"):
            world.buy_card(self.save, world.shop_cards(self.save)[1].pk)

    def test_buying_a_specialty_pack(self):
        world.travel(self.save, "shop")
        before = sum(self.save.pool.values())
        world.buy_specialty(self.save, "climax_pack", {"set": str(SET)})
        self.assertEqual(self.save.money, 700)
        self.assertEqual(sum(self.save.pool.values()) - before, 8)
        climaxes = {str(pk) for pk in Card.objects.filter(card_type="Climax").values_list("pk", flat=True)}
        self.assertTrue(self.save.last_opening["bought"])
        self.assertTrue({pull["id"] for pull in self.save.last_opening["packs"][0]} <= {int(pk) for pk in climaxes})
        world.buy_specialty(self.save, "level_pack", {"set": "9", "level": "2"})
        self.assertEqual(self.save.money, 400)
        for buff, data in (("level_pack", {"set": str(SET)}), ("color_pack", {"set": str(SET), "color": "Pink"}),
                           ("climax_pack", {"set": "12345"}), ("heal", {"set": str(SET)})):
            with self.subTest(buff=buff, data=data):
                with self.assertRaises(ValueError):
                    world.buy_specialty(self.save, buff, data)
        self.save.money = 10
        with self.assertRaisesRegex(ValueError, "costs 300"):
            world.buy_specialty(self.save, "lucky_pack", {"set": str(SET)})

    def test_the_shop_as_the_town_shows_it_and_buying_from_the_page(self):
        world.travel(self.save, "shop")
        shop = self.client.get(reverse("weiss:world_town_state", args=[1])).json()["shop"]
        self.assertEqual((shop["specialty_price"], shop["card_price"]), (300, 400))
        self.assertTrue(all(entry["cover"] for entry in shop["stock"]))
        self.assertEqual([entry["key"] for entry in shop["specials"]], list(world.SHOP_SPECIALS))
        card = shop["cards"][0]
        self.assertFalse(card["sold"])
        answer = self.client.post(reverse("weiss:world_buy_card", args=[1]), {"card": card["id"], "version": WorldSave.objects.get(pk=self.save.pk).version}).json()
        self.assertIn("is yours", answer["said"])
        self.assertTrue(answer["town"]["shop"]["cards"][0]["sold"])
        self.assertEqual(answer["town"]["money"], 600)
        response = self.client.post(reverse("weiss:world_buy", args=[1]), {"special": "color_pack", "set": SET, "color": "Red"}, follow=True)
        self.assertContains(response, "no cards like that")  # this set has no red cards: nothing spent
        self.assertEqual(WorldSave.objects.get(pk=self.save.pk).money, 600)
        response = self.client.post(reverse("weiss:world_buy", args=[1]), {"special": "climax_pack", "set": SET})
        self.assertRedirects(response, reverse("weiss:world_opened", args=[1]))
        self.assertEqual(WorldSave.objects.get(pk=self.save.pk).money, 300)


class ScheduleStaffPageTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.client.force_login(staff_user())
        self.cinder = give_cpu("Cinder", self.cards)
        self.url = reverse("weiss:world_schedules")

    def test_adding_editing_and_deleting_haunts(self):
        plaza = WorldPlace.objects.get(key="plaza")
        self.client.post(self.url, {"cpu": self.cinder.pk, "place": plaza.pk, "days": ["1", "4"], "times": ["3"], "weight": "80",
                                    "min_rank": "2", "stake": "500"})
        rule = CpuSchedule.objects.get()
        self.assertEqual((rule.days, rule.times, rule.weight, rule.min_rank, rule.stake, rule.once_per_day), ([1, 4], [3], 80, 2, 500, False))
        page = self.client.get(self.url + "?day=1&seed=1")
        self.assertContains(page, "Tue, Fri, night, weight 80, from rank 2, stakes 500 coins")
        self.assertContains(page, "rank 2+")  # in the grid, marked as waiting for a rank
        self.client.post(self.url, {"rule": rule.pk, "cpu": self.cinder.pk, "place": plaza.pk, "days": ["5", "6"], "times": ["2"], "once": "1"})
        rule.refresh_from_db()
        self.assertEqual((rule.days, rule.once_per_day, rule.weight, rule.min_rank), ([5, 6], True, 50, 0))
        self.client.post(self.url, {"cpu": self.cinder.pk, "place": plaza.pk, "times": ["2"]})  # no days: refused
        self.client.post(self.url, {"cpu": self.cinder.pk, "place": plaza.pk, "days": ["5", "6"], "times": ["2"], "once": "1"})  # the same again: refused
        self.client.post(self.url, {"cpu": self.cinder.pk, "place": plaza.pk, "days": ["1"], "times": ["2"], "weight": "0"})  # too light: refused
        self.assertEqual(CpuSchedule.objects.count(), 1)
        self.client.post(self.url, {"delete": rule.pk})
        self.assertFalse(CpuSchedule.objects.exists())

    def test_the_grid_and_starting_haunts(self):
        page = self.client.get(self.url)
        self.assertContains(page, "never appear")
        self.client.post(self.url, {"starters": "1"})
        self.assertEqual(CpuSchedule.objects.filter(cpu=self.cinder).count(), 3)
        page = self.client.get(self.url)
        self.assertContains(page, "Cinder")
        self.assertContains(page, "Out in town")


class StarterScheduleTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.client.force_login(staff_user())

    def test_cpus_are_spread_across_the_town(self):
        for n in range(9):
            give_cpu(f"CPU {n}", self.cards)
        self.assertEqual(world.starter_schedules(), 9)
        per_place = Counter(CpuSchedule.objects.filter(place__secluded=False).values_list("place__key", flat=True))
        self.assertLessEqual(max(per_place.values()) - min(per_place.values()), 1, per_place)  # spread evenly over the open places
        self.assertEqual(len(per_place), WorldPlace.objects.filter(shop=False, secluded=False).count())
        self.assertFalse(CpuSchedule.objects.filter(place__shop=True).exists())
        self.assertFalse(CpuSchedule.objects.filter(days=[0, 1, 2, 3, 4], place__secluded=True).exists())  # villains' places
        for cpu in CpuProfile.objects.all():
            places = list(cpu.schedule.values_list("place__key", flat=True))
            self.assertEqual(len(set(places)), 3)  # home, weekend and wander are three places

    def test_finalizing_a_cpu_gives_it_a_schedule_once(self):
        cpu = give_cpu("Mai", self.cards, finalized=False)
        url = reverse("weiss:cpu_profile_finalize", args=[cpu.pk])
        self.client.post(url, {"finalized": "on"})
        self.assertEqual(cpu.schedule.count(), 3)
        cpu.schedule.first().delete()  # staff changed it
        self.client.post(url, {"finalized": "off"})
        self.client.post(url, {"finalized": "on"})
        self.assertEqual(cpu.schedule.count(), 2)  # left as staff had it
        empty = give_cpu("Nobody", self.cards, finalized=False)
        empty.deck.entries.all().delete()
        self.client.post(reverse("weiss:cpu_profile_finalize", args=[empty.pk]), {"finalized": "on"})
        self.assertFalse(empty.schedule.exists())  # it couldn't be finalized


class MapTests(TestCase):
    def test_the_map_says_whos_at_each_place(self):
        cards = make_set()
        save = world.start(staff_user(), 1, SET)
        everywhere_rule(give_cpu("Cinder", cards), "beach")
        everywhere_rule(give_cpu("Katara", cards), "beach")
        everywhere_rule(give_cpu("Mai", cards), "cafe", times=[3])  # nights only
        town = world.town(save)
        who = {p["key"]: [person["name"] for person in p["who"]] for p in town["places"]}
        self.assertEqual((who["beach"], who["cafe"], who["plaza"]), (["Cinder", "Katara"], [], []))
        self.assertIn("avatar", town["places"][0]["who"][0] if town["places"][0]["who"] else {"avatar": None})
        for _ in range(3):
            world.wait(save)
        who = {p["key"]: [person["name"] for person in p["who"]] for p in world.town(save)["places"]}
        self.assertEqual(who["cafe"], ["Mai"])
