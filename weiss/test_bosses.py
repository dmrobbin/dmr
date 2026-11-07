"""The infinite challenge's bosses (see docs/infinite-bosses.md)."""
import random
from types import SimpleNamespace
from unittest import mock

from django.urls import reverse

from . import augments, buffs, challenge, coop, cpu, game, play
from .models import Card, CardListEntry, ChallengeRun, ChallengeSettings, CoopRun, GameRoom, Scene
from .test_challenge import ArcadeSetup
from .test_coop import PlayingSetup
from .test_packs import make_set, run_with_climaxes


def settings(**fields):
    ChallengeSettings.objects.update_or_create(pk=1, defaults=fields)


class SoloSetup(ArcadeSetup):
    """A solo infinite challenge of the staff user's, with a deck."""

    def setUp(self):
        super().setUp()
        make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4)
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "infinite"})
        self.run = challenge.current(self.staff)
        challenge.open_packs(self.run, 7, 2)
        challenge.save_deck(self.run, {pk: 1 for pk in self.run.pool})
        self.run = run_with_climaxes(self.run)

    def path(self):
        self.run.refresh_from_db()
        return challenge.path_of(self.run, random.Random(4))

    def climb(self, floors):
        """Up the path this many floors, as if each were won, laying it as it goes."""
        for _ in range(floors):
            path = self.path()
            at = path["done"]
            path["picks"] = path["picks"][:at] + [challenge.choices(path, at)[0]]
            path["done"] = at + 1
            self.run.path = path
            self.run.save()
        return self.path()

    def fight(self, node=None):
        if node is None:
            node = challenge.choices(self.path(), challenge.floor_at(self.run))[0]
        return self.client.post(reverse("weiss:arcade_challenge_fight"), {"node": node})


class BossPathTests(SoloSetup):
    def test_every_fifth_floor_is_a_boss(self):
        path = self.climb(7)
        self.assertEqual(path["bosses"], [4, 9])
        for f in path["bosses"]:
            self.assertEqual(path["floors"][f][0::2], [None, None])  # one, in the middle
            self.assertIsNotNone(path["floors"][f][1])
        self.assertEqual(challenge.choices(path, 4), [1])  # every way leads to it

    def test_staff_set_how_far_apart_they_are_or_none(self):
        settings(boss_every=2)
        self.assertEqual(self.climb(3)["bosses"], [1, 3, 5])
        self.run.path = {}
        self.run.save()
        settings(boss_every=0)
        self.assertNotIn("bosses", self.climb(8))

    def test_a_boss_laid_stays_one(self):
        self.assertNotIn("bosses", self.path())  # floors 0 to 3: none yet
        self.climb(1)
        self.assertEqual(self.path()["bosses"], [4])
        settings(boss_every=0)
        self.assertEqual(self.climb(4)["bosses"], [4])  # laid before the change

    def test_marked_bosses_are_only_fought_as_bosses(self):
        type(self.anchor).objects.filter(pk=self.anchor.pk).update(boss=True)
        path = self.climb(12)
        for f, floor in enumerate(path["floors"]):
            if f in path["bosses"]:
                self.assertEqual(floor[1], self.anchor.pk)
            else:
                self.assertNotIn(self.anchor.pk, floor)

    def test_without_marked_bosses_any_cpu_can_be_one(self):
        path = self.climb(25)
        met = {path["floors"][f][1] for f in path["bosses"]}
        self.assertEqual(met, {self.opener.pk, self.filler.pk, self.anchor.pk})

    def test_bosses_come_in_turn_before_one_comes_again(self):
        type(self.anchor).objects.update(boss=True)
        path = self.climb(12)
        firsts = [path["floors"][f][1] for f in path["bosses"][:3]]
        self.assertEqual(len(set(firsts)), 3)

    def test_a_boss_floor_never_has_an_event(self):
        Scene.objects.create(name="Deal", script="narrator: Hi.\ngive extra_packs", infinite_event=True)
        settings(event_percent=100)
        path = self.climb(7)
        for f in path["bosses"]:
            self.assertNotIn(challenge.EVENT, path["floors"][f])
        self.assertIn(challenge.EVENT, path["floors"][5])

    def test_a_boss_gone_is_replaced_by_another(self):
        type(self.anchor).objects.update(boss=True)
        self.climb(1)
        boss = self.path()["floors"][4][1]
        type(self.anchor).objects.filter(pk=boss).update(finalized=False)
        path = self.path()
        self.assertEqual(path["bosses"], [4])
        self.assertNotIn(path["floors"][4][1], (None, boss))

    def test_the_path_shows_the_boss(self):
        self.climb(2)
        page = self.client.get(reverse("weiss:arcade_challenge")).content.decode()
        self.assertIn('class="spire-boss-tag"', page)
        self.assertIn("<span>Boss</span>", page)
        self.assertIn("the path narrows to a <strong>boss</strong>", page)
        settings(boss_every=0)
        self.run.path = {}
        self.run.save()
        page = self.client.get(reverse("weiss:arcade_challenge")).content.decode()
        self.assertNotIn("spire-boss-tag", page)
        self.assertNotIn("narrows to a", page)


class BossFightTests(SoloSetup):
    def setUp(self):
        super().setUp()
        self.climb(4)  # on floor 5: the first boss

    def test_the_boss_plays_at_its_hardest_and_starts_with_stock(self):
        CardListEntry.objects.filter(card_list__reserved_for_cpu=True).update(quantity=20)
        self.fight()
        room = self.room()
        self.assertEqual((room.state["floor"], room.state["boss"]), (4, True))
        self.assertEqual(len(room.state["players"][str(room.guest_id)]["zones"]["stock"]), challenge.BOSS_STOCK)
        self.assertEqual(len(room.state["players"][str(room.host_id)]["zones"]["stock"]), 0)
        room.state.pop("cpu_intro", None)
        room.save()
        with mock.patch.object(play.cpu, "next_action", return_value=None) as chooser:
            play.cpu_step(GameRoom.objects.get(pk=room.pk), wait=False)
        self.assertEqual((chooser.call_args.kwargs["model"], chooser.call_args.args[3]), ("hard", cpu.MAX_AGGRESSION))
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertIn("boss", data["arcade"])

    def test_other_fights_are_stamped_with_their_floor_only(self):
        self.run.path = {}
        self.run.save()
        self.fight()
        room = self.room()
        self.assertEqual(room.state["floor"], 0)
        self.assertNotIn("boss", room.state)
        self.assertNotIn("boss", self.client.get(reverse("weiss:play_state", args=[room.pk])).json()["arcade"])

    def test_beating_it_brings_more_packs(self):
        self.fight()
        packs = self.run.packs
        self.end_fight("me")
        self.run.refresh_from_db()
        self.assertEqual(self.run.packs, packs + challenge.INFINITE_WIN_PACKS + challenge.BOSS_PACKS)
        self.assertEqual(challenge.floor_at(self.run), 5)

    def test_losing_to_it_is_a_loss_like_any(self):
        self.fight()
        self.end_fight("cpu")
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, "lost")

    def test_the_game_is_stamped_for_its_floor(self):
        self.fight()
        self.assertEqual(challenge.fought(self.room()), {"floor": 4, "boss": True})
        room = self.room()
        self.assertNotIn("shared_health", room.state["players"][str(room.guest_id)])  # a solo boss loses at level 4


class CoopBossSetup(PlayingSetup):
    """Both players on the floor of the first boss, with decks."""

    def setUp(self):
        super().setUp()
        CardListEntry.objects.filter(card_list__reserved_for_cpu=True).update(quantity=20)
        for _ in range(4):
            self.climb_both()

    def climb_both(self, users=None):
        """These players (both, if not given) finish the floor they're on, as if they'd fought it."""
        run = self.fresh(self.staff)
        path = challenge.path_of(run)
        progress = path.setdefault("progress", {})
        for user in users or (self.staff, self.bo):
            at = coop.floor_of(path, user.pk)
            if at >= len(path["picks"]):
                path["picks"].append(challenge.choices(path, at)[0])
            progress[str(user.pk)] = at + 1
        path["done"] = min(coop.floor_of(path, user.pk) for user in (self.staff, self.bo))
        CoopRun.objects.filter(pk=self.pair.pk).update(path=path)

    def fight(self, user):
        return self.as_(user).client.post(reverse("weiss:arcade_challenge_fight"), {"node": 1}, follow=True)

    def hit(self, user, damage, lost=False):
        """An action in this player's game: this much damage lands on the boss, and with `lost`, the player has lost."""
        room = self.room_of(user)
        room.state.pop("cpu_intro", None)

        def acts(state, *args, **kwargs):
            side = state["players"][str(room.guest_id)]
            side["damage_taken"] = side.get("damage_taken", 0) + damage
            if lost:
                state["game_over"] = {"winner": str(room.guest_id), "loser": str(room.host_id), "reason": "level", "rematch": []}
            return {}
        with mock.patch.object(play.game, "apply", side_effect=acts):
            play.play_action(room, room.host_id, {"type": "x"}, lookups={"info": None})
        return self.room_of(user)

    def poll(self, user):
        self.as_(user).client.get(reverse("weiss:play_state", args=[self.room_of(user).pk]))
        return self.room_of(user)

    def boss(self):
        return self.fresh(self.staff).path.get("boss")


class CoopBossTests(CoopBossSetup):
    def test_both_go_straight_to_the_boss_with_no_vote(self):
        self.fight(self.staff)
        room = self.room_of(self.staff)
        self.assertEqual((room.state["floor"], room.state["boss"], room.state["shared_boss"]), (4, True, True))
        self.assertTrue(room.state["players"][str(room.guest_id)]["shared_health"])
        self.fight(self.bo)
        self.assertEqual(self.room_of(self.bo).cpu_profile_id, room.cpu_profile_id)

    def test_the_boss_waits_for_both_players(self):
        self.pair.refresh_from_db()
        path = self.pair.path
        path["progress"][str(self.bo.pk)] = 3
        path["done"] = 3
        CoopRun.objects.filter(pk=self.pair.pk).update(path=path)
        page = self.fight(self.staff)
        self.assertContains(page, "The boss waits for you both: bo is still on fight 4.")
        self.assertFalse(GameRoom.objects.filter(host=self.staff).exists())

    def test_damage_comes_off_as_it_lands_in_either_game(self):
        self.fight(self.staff)
        self.fight(self.bo)
        self.assertNotIn("game_over", self.hit(self.staff, 3).state)
        self.assertEqual((self.boss()["health"], self.boss()["dealt"]), (39, {str(self.staff.pk): 3}))
        self.hit(self.bo, 4)
        self.hit(self.staff, 2)
        self.hit(self.staff, 0)  # nothing landed: nothing changes
        self.assertEqual((self.boss()["health"], self.boss()["dealt"]), (33, {str(self.staff.pk): 5, str(self.bo.pk): 4}))

    def test_a_loss_keeps_the_damage_it_dealt_and_counts(self):
        self.fight(self.staff)
        self.hit(self.staff, 6, lost=True)
        self.pair.refresh_from_db()
        self.assertEqual((self.boss()["health"], self.pair.losses), (36, 1))
        self.assertEqual(challenge.floor_at(self.fresh(self.staff)), 4)  # not done with it yet
        self.fight(self.staff)  # again, from a fresh count
        self.assertNotIn("game_over", self.room_of(self.staff).state)
        self.hit(self.staff, 2)
        self.assertEqual(self.boss()["dealt"], {str(self.staff.pk): 8})

    def test_emptying_its_health_wins_both_games(self):
        settings(coop_boss_health=20)
        packs = {user: self.fresh(user).packs for user in (self.staff, self.bo)}
        self.fight(self.staff)
        self.fight(self.bo)
        self.hit(self.bo, 5)
        room = self.hit(self.staff, 16)
        self.assertEqual((room.state["game_over"]["winner"], room.state["game_over"]["reason"]), (str(self.staff.pk), "boss"))
        boss = self.boss()
        self.assertEqual((boss["health"], boss["down"]), (0, True))
        for user in (self.staff, self.bo):
            self.assertEqual(challenge.floor_at(self.fresh(user)), 5)
        self.assertEqual(self.fresh(self.staff).packs, packs[self.staff] + challenge.INFINITE_WIN_PACKS + challenge.BOSS_PACKS)
        self.assertNotIn("game_over", self.room_of(self.bo).state)  # until bo's page next asks
        room = self.poll(self.bo)
        self.assertEqual((room.state["game_over"]["winner"], room.state["game_over"]["reason"]), (str(self.bo.pk), "boss"))
        self.assertEqual(self.fresh(self.bo).packs, packs[self.bo] + challenge.INFINITE_WIN_PACKS + challenge.BOSS_PACKS)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.losses, 0)

    def test_a_player_not_in_a_game_still_beats_it(self):
        settings(coop_boss_health=10)
        packs = self.fresh(self.bo).packs
        self.fight(self.staff)
        self.hit(self.staff, 10)
        bo = self.fresh(self.bo)
        self.assertEqual((challenge.floor_at(bo), bo.packs), (5, packs + challenge.BOSS_PACKS))

    def test_a_loss_whose_last_damage_takes_it_down_isnt_one(self):
        settings(coop_boss_health=10)
        self.fight(self.staff)
        self.hit(self.staff, 10, lost=True)
        self.pair.refresh_from_db()
        self.assertEqual((self.boss()["down"], self.pair.losses, challenge.floor_at(self.fresh(self.staff))), (True, 0, 5))

    def test_a_win_with_its_health_left_doesnt_count(self):
        self.fight(self.staff)
        room = self.room_of(self.staff)
        room.state.pop("cpu_intro", None)

        def decks_out(state, *args, **kwargs):
            state["game_over"] = {"winner": str(room.host_id), "loser": str(room.guest_id), "reason": "deck", "rematch": []}
            return {}
        packs = self.fresh(self.staff).packs
        with mock.patch.object(play.game, "apply", side_effect=decks_out):
            play.play_action(room, room.host_id, {"type": "x"}, lookups={"info": None})
        staff = self.fresh(self.staff)
        self.assertEqual((challenge.floor_at(staff), staff.packs), (4, packs))

    def test_the_last_loss_still_ends_it(self):
        CoopRun.objects.filter(pk=self.pair.pk).update(loss_limit=1)
        self.fight(self.staff)
        self.hit(self.staff, 2, lost=True)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.status, CoopRun.Status.LOST)

    def test_the_next_boss_starts_at_full_health(self):
        settings(coop_boss_health=10)
        self.fight(self.staff)
        self.hit(self.staff, 12)
        for _ in range(4):
            self.climb_both()
        self.fight(self.staff)
        self.assertEqual(self.room_of(self.staff).state["floor"], 9)
        self.hit(self.staff, 4)
        self.assertEqual((self.boss()["floor"], self.boss()["health"]), (9, 6))

    def test_the_pages_show_how_worn_down_it_is(self):
        self.fight(self.staff)
        self.fight(self.bo)
        page = self.as_(self.staff).client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "wear it down together")
        self.assertContains(page, "42 / 42")
        self.hit(self.staff, 5)
        page = self.as_(self.bo).client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "37 / 42")
        self.assertContains(page, "Damage dealt: you 0 · staff 5")
        data = self.as_(self.bo).client.get(reverse("weiss:play_state", args=[self.room_of(self.bo).pk])).json()
        boss = data["arcade"]["boss"]
        self.assertEqual((boss["health"], boss["max"], boss["down"], boss["dealt"]), (37, 42, False, {str(self.staff.pk): 5}))
        self.hit(self.bo, 40)
        page = self.as_(self.staff).client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "The boss is down!")
        self.assertTrue(self.as_(self.staff).client.get(reverse("weiss:play_state", args=[self.room_of(self.staff).pk])).json()["arcade"]["boss"]["down"])


class BossDamageTests(SoloSetup):
    """What the game itself counts of the damage a co-op boss takes, and how it loses."""

    def state(self):
        return game.new_game([(1, "me", [1] * 20), (2, "boss", [1] * 20)])

    def test_damage_that_lands_is_counted(self):
        state = self.state()
        game.deal_damage(state, "2", 3, 3, [], str, lambda pk: False)
        self.assertEqual(state["players"]["2"]["damage_taken"], 3)

    def test_a_cancelled_damage_isnt(self):
        state = self.state()
        state["players"]["2"]["zones"]["deck"][-2]["card"] = 9  # the second card down: a climax
        game.deal_damage(state, "2", 3, 3, [], str, lambda pk: pk == 9)
        self.assertEqual(state["players"]["2"].get("damage_taken", 0), 0)

    def test_refresh_damage_is(self):
        state = self.state()
        game.refresh(state, "2", str, lambda cards: None)
        self.assertEqual(state["players"]["2"]["damage_taken"], 1)

    def test_a_coop_boss_doesnt_lose_at_level_4(self):
        state = self.state()
        side = state["players"]["2"]
        side["zones"]["level"] = [game.new_card(1) for _ in range(game.LOSING_LEVEL)]
        side["shared_health"] = True
        game.check_game_over(state)
        self.assertNotIn("game_over", state)
        side.pop("shared_health")
        game.check_game_over(state)
        self.assertEqual(state["game_over"]["loser"], "2")

    def test_it_doesnt_hold_back_for_fear_of_losing(self):
        state = self.state()
        side = state["players"]["2"]
        side["zones"]["level"] = [game.new_card(1) for _ in range(3)]
        mind = cpu.Mind(state, "2", lambda pk: {}, None, random.Random(1))
        self.assertTrue(mind.would_lose(7))
        side["shared_health"] = True
        self.assertFalse(mind.would_lose(7))


class SoloBossPageTests(SoloSetup):
    def test_the_game_page_says_what_beating_it_brings(self):
        self.climb(4)
        self.fight()
        boss = self.client.get(reverse("weiss:play_state", args=[self.room().pk])).json()["arcade"]["boss"]
        self.assertEqual(boss, {"reward": challenge.boss_reward_text(self.run)})


class AugmentPickTests(SoloSetup):
    def setUp(self):
        super().setUp()
        self.climb(4)
        self.fight()
        self.end_fight("me")  # the first boss, beaten
        self.run.refresh_from_db()

    def pick(self):
        return next(r for r in self.run.rewards if r["buff"] == "augment")

    def test_beating_a_boss_offers_three_augments(self):
        reward = self.pick()
        self.assertEqual((reward["source"], len(reward["options"])), ("Boss", augments.OFFER))
        self.assertNotIn("lifeline", reward["options"])  # co-op only
        page = self.client.get(reverse("weiss:arcade_challenge"))
        for option in reward["options"]:
            self.assertContains(page, f'value="{option}"')
            self.assertContains(page, augments.AUGMENTS[option].name)

    def test_picking_one_keeps_it_for_the_run(self):
        reward = self.pick()
        chosen = reward["options"][1]
        response = self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": reward["key"], "augment": "lifeline"}, follow=True)
        self.assertContains(response, "Choose one of the augments offered.")
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": reward["key"], "augment": chosen})
        self.run.refresh_from_db()
        self.assertEqual(self.run.augments, [chosen])
        self.assertFalse(any(r["buff"] == "augment" for r in self.run.rewards))
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Your augments")
        self.assertNotIn(chosen, augments.offer(self.run, random.Random(1)))  # not offered again

    def test_never_given_at_random(self):
        rng = random.Random(2)
        self.assertNotIn("augment", {buff for _ in range(80) for buff in buffs.roll(4, rng)})

    def test_with_every_augment_already_packs_instead(self):
        self.run.augments = [a for a in augments.AUGMENTS if not augments.AUGMENTS[a].coop_only]
        self.run.rewards = []
        self.run.save()
        packs = self.run.packs
        said = buffs.grant(self.run, ["augment"], "Boss")
        self.assertEqual((self.run.packs, self.run.rewards), (packs + buffs.EXTRA_PACKS, []))
        self.assertIn("every augment", said[0])


class RunAugmentTests(SoloSetup):
    def augment(self, *ids, run=None):
        run = run or self.run
        ChallengeRun.objects.filter(pk=run.pk).update(augments=list(ids))
        run.refresh_from_db()

    def test_highlander_holds_the_deck_to_two_copies_and_wins_bring_more(self):
        pk = int(next(iter(self.run.pool)))
        self.run.pool[str(pk)] = 3
        self.run.save()
        self.assertIsNone(challenge.save_deck(self.run, {pk: 3}))  # the rules only warn about copies
        self.augment("highlander")
        self.assertIn("at most 2 copies", challenge.save_deck(self.run, {pk: 3}))
        page = self.fight()
        self.assertFalse(GameRoom.objects.filter(host=self.staff).exists())  # the deck still has 3
        self.assertIn("Change your deck to fight on", [m.message for m in page.wsgi_request._messages][0])
        self.assertIsNone(challenge.save_deck(self.run, {pk: 2}))
        self.run = run_with_climaxes(self.run)
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge_deck")), 'data-copy-limit="2"')
        self.fight()
        packs = self.run.packs
        self.end_fight("me")
        self.run.refresh_from_db()
        self.assertEqual(self.run.packs, packs + challenge.INFINITE_WIN_PACKS + augments.HIGHLANDER_PACKS)

    def test_a_deck_needs_its_8_climaxes_to_fight_and_holds_no_more(self):
        spare = Card.objects.create(serial_number="TEST/SPARE", name="Spare climax", expansion="Test", expansion_id=999, card_type="Climax", rarity="CC")
        self.run.pool[str(spare.pk)] = 3
        self.run.save()
        deck = dict(self.run.deck.entries.values_list("card_id", "quantity"))
        self.assertIn("exactly 8 climaxes, and this one has 9", challenge.save_deck(self.run, {**deck, spare.pk: 1}))
        some = Card.objects.get(serial_number="TEST/CX1").pk
        self.assertIsNone(challenge.save_deck(self.run, {**deck, some: deck[some] - 1}))
        page = self.fight()
        self.assertFalse(GameRoom.objects.filter(host=self.staff).exists())
        self.assertIn("exactly 8 climaxes, and this one has 7. Change your deck", [m.message for m in page.wsgi_request._messages][0])
        self.augment("climax_overload")
        self.assertIn("8 to 10 climaxes, and this one has 11", challenge.save_deck(self.run, {**deck, spare.pk: 3}))
        self.assertIsNone(challenge.save_deck(self.run, {**deck, spare.pk: 2}))
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge_deck")), 'data-climax-min="8"')
        self.fight()
        self.assertTrue(GameRoom.objects.filter(host=self.staff).exists())

    def test_climax_overload_raises_the_climax_target_and_wins_bring_a_climax_pick(self):
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge_deck")), 'data-climaxes="8"')
        self.augment("climax_overload")
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge_deck")), 'data-climaxes="10"')
        self.fight()
        self.end_fight("me")
        self.run.refresh_from_db()
        self.assertIn("climax_pick", [r["buff"] for r in self.run.rewards])

    def test_glass_cannon_losses_count_twice(self):
        self.augment("glass_cannon")
        ChallengeRun.objects.filter(pk=self.run.pk).update(lives=3)
        self.fight()
        self.end_fight("cpu")
        self.run.refresh_from_db()
        self.assertEqual((self.run.lives, self.run.status), (1, "active"))
        self.fight()
        self.end_fight("cpu")
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, "lost")  # one second chance isn't enough

    def test_devotion_makes_a_color_pack_likelier(self):
        self.assertEqual(augments.prizes(self.run, challenge.INFINITE_PRIZES), challenge.INFINITE_PRIZES)
        self.augment("devotion")
        prizes = augments.prizes(self.run, challenge.INFINITE_PRIZES)
        self.assertEqual(prizes.count("color_pack"), 2)


class CoopRunAugmentTests(CoopBossSetup):
    def test_lifeline_raises_the_pairs_loss_limit(self):
        run = self.fresh(self.staff)
        buffs.grant(run, ["augment"], "Boss", random.Random(1))
        reward = next(r for r in self.fresh(self.staff).rewards if r["buff"] == "augment")
        while "lifeline" not in reward["options"]:  # the pick that offers it
            run = self.fresh(self.staff)
            run.rewards = []
            run.save()
            buffs.grant(run, ["augment"], "Boss")
            reward = next(r for r in self.fresh(self.staff).rewards if r["buff"] == "augment")
        self.as_(self.staff).client.post(reverse("weiss:arcade_challenge_claim"), {"key": reward["key"], "augment": "lifeline"})
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.loss_limit, coop.LOSS_LIMIT + 1)
        self.assertIn("lifeline", augments.offer(self.fresh(self.staff), random.Random(3)) + ["lifeline"])  # it stacks
        page = self.as_(self.bo).client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "staff's augments:")
        self.assertContains(page, "Lifeline")

    def test_glass_cannon_puts_two_on_the_counter(self):
        ChallengeRun.objects.filter(user=self.bo).update(augments=["glass_cannon"])
        self.fight(self.bo)
        self.finish(self.bo, won=False)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.losses, 2)


class GameAugmentTests(SoloSetup):
    """The augments that change a game: on the player's side when it's dealt, and read by the rules."""

    CARDS = {1: {"name": "Low", "card_type": "Character", "level": 0, "power": 3000, "soul": 1, "color": "Red", "text": ""},
             2: {"name": "High", "card_type": "Character", "level": 2, "power": 8000, "soul": 2, "color": "Red", "text": ""},
             3: {"name": "Block", "card_type": "Event", "level": 0, "cost": 1, "color": "Red", "text": "【COUNTER】 Choose a character."}}

    def env(self):
        info = lambda pk: self.CARDS.get(pk, {})
        return SimpleNamespace(info=info, name=lambda pk: info(pk).get("name", "?"), shuffle=lambda cards: None,
                               is_climax=lambda pk: False, trigger=lambda pk: "", cost=lambda pk: info(pk).get("cost", 0))

    def table(self, *augment_ids):
        state = game.new_game([(1, "me", [1] * 20), (2, "cpu", [1] * 20)], shuffle=lambda cards: None)
        state["players"]["1"]["augments"] = list(augment_ids)
        for slot, pk in (("C1", 1), ("C2", 2)):
            state["players"]["1"]["stage"][slot] = game.new_card(pk)
            state["players"]["2"]["stage"][slot] = game.new_card(pk)
        return state

    def stats(self, state, side="1"):
        stats, _ = game.compute_stats(state, self.env())
        return [(stats[card["uid"]]["power"], stats[card["uid"]]["soul"]) for card in (state["players"][side]["stage"][s] for s in ("C1", "C2"))]

    def test_their_power_and_soul(self):
        self.assertEqual(self.stats(self.table()), [(3000, 1), (8000, 2)])
        self.assertEqual(self.stats(self.table("devotion")), [(4000, 1), (9000, 2)])
        self.assertEqual(self.stats(self.table("low_level_army")), [(4500, 1), (8000, 2)])
        self.assertEqual(self.stats(self.table("glass_cannon")), [(3000, 2), (8000, 3)])
        self.assertEqual(self.stats(self.table("devotion", "low_level_army", "glass_cannon"), side="2"), [(3000, 1), (8000, 2)])  # only the player's

    def test_clean_refresh_spares_the_first_refresh_only(self):
        state = self.table("clean_refresh")
        zones = state["players"]["1"]["zones"]
        for _ in range(2):
            zones["waiting"], zones["deck"] = zones["deck"], []
            game.refresh(state, "1", self.env().name, lambda cards: None)
        self.assertEqual(len(zones["clock"]), 1)  # the second one's
        self.assertIn("no refresh damage (Clean Refresh)", " ".join(entry["text"] for entry in state["log"]))

    def test_counter_specialist_counters_cost_one_less(self):
        state = self.table()
        state["phase"] = "attack"
        block = game.new_card(3)
        state["players"]["1"]["zones"]["hand"].append(block)
        self.assertIsNone(game.counter_play(state, "1", block, self.env().info))  # no stock for it
        state["players"]["1"]["augments"] = ["counter_specialist"]
        self.assertEqual(game.counter_play(state, "1", block, self.env().info), (0, 0))

    def test_dealt_with_the_players_augments(self):
        CardListEntry.objects.filter(card_list__reserved_for_cpu=True).update(quantity=20)
        ChallengeRun.objects.filter(pk=self.run.pk).update(augments=["deep_reserves", "head_start", "highlander", "devotion"])
        self.fight()
        room = self.room()
        me, them = room.state["players"][str(room.host_id)], room.state["players"][str(room.guest_id)]
        colors = {card.color for card in Card.objects.filter(pk__in=[int(pk) for pk in self.run.pool])}
        mono = len(colors - {None, ""}) <= 1
        self.assertEqual(me["augments"], ["deep_reserves", "head_start", "devotion"] if mono else ["deep_reserves", "head_start"])  # not the run's
        self.assertEqual((len(me["zones"]["stock"]), len(them["zones"]["clock"])), (augments.RESERVES, augments.HEAD_START))
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual([a["name"] for a in data["arcade"]["augments"]], ["Deep Reserves", "Head Start", "Highlander", "Devotion"])

    def test_devotion_needs_one_color(self):
        self.assertTrue(augments.mono_color([{"color": "Red"}, {"color": "Red"}, {"color": ""}]))
        self.assertFalse(augments.mono_color([{"color": "Red"}, {"color": "Blue"}]))
