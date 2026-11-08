"""Flash battles: fights on the infinite challenge's path that start at level 2, with stock (see game.flash_start)."""
from django.urls import reverse

from . import challenge, cpu, game
from .play import anchor_colors
from .models import Card, CardList, CardListEntry, ChallengeSettings
from .test_bosses import SoloSetup, settings

CARDS = {1: {"name": "Low", "card_type": "Character", "level": 0, "color": "Red"},
         2: {"name": "High", "card_type": "Character", "level": 2, "color": "Red"},
         3: {"name": "Off", "card_type": "Character", "level": 3, "color": "Blue"},
         4: {"name": "Boom", "card_type": "Climax", "level": 0, "color": "Red"},
         5: {"name": "Tide", "card_type": "Character", "level": 0, "color": "Blue"},
         6: {"name": "Wave", "card_type": "Climax", "level": 0, "color": "Blue"}}


def play(state, player, action):
    info = lambda pk: CARDS.get(pk, {})
    return game.apply(state, player, action, name=lambda pk: info(pk).get("name", "?"), shuffle=lambda cards: None, info=info)


def flash_table():
    state = game.new_game([(1, "me", [1] * 15 + [2] * 5), (2, "cpu", [1] * 10 + [4] * 4 + [3] * 2 + [2] * 4)], shuffle=lambda cards: None)
    game.flash_start(state)
    return state


class FlashGameTests(SoloSetup):
    def test_the_hand_goes_back_until_the_level_cards_are_chosen(self):
        state = flash_table()
        me = state["players"]["1"]["zones"]
        self.assertEqual((len(me["hand"]), len(me["deck"])), (0, 20))
        with self.assertRaisesMessage(game.GameError, "level cards first"):
            play(state, "1", {"type": "mulligan", "uids": []})
        for wrong in ([me["deck"][0]["uid"]], [me["deck"][0]["uid"], "nope"]):
            with self.assertRaises(game.GameError):
                play(state, "1", {"type": "flash_level", "uids": wrong})
        play(state, "1", {"type": "flash_level", "uids": [me["deck"][0]["uid"], me["deck"][1]["uid"]]})
        self.assertEqual((len(me["level"]), len(me["hand"]), len(me["deck"])), (2, game.STARTING_HAND, 20 - 2 - game.STARTING_HAND))
        with self.assertRaises(game.GameError):
            play(state, "1", {"type": "flash_level", "uids": [me["deck"][0]["uid"], me["deck"][1]["uid"]]})  # once only

    def test_after_both_mulligans_each_deck_puts_three_in_stock(self):
        state = flash_table()
        for player in ("1", "2"):
            deck = state["players"][player]["zones"]["deck"]
            play(state, player, {"type": "flash_level", "uids": [deck[0]["uid"], deck[1]["uid"]]})
        play(state, "1", {"type": "mulligan", "uids": []})
        self.assertEqual(state["players"]["1"]["zones"]["stock"], [])  # not until both have
        play(state, "2", {"type": "mulligan", "uids": []})
        for side in state["players"].values():
            self.assertEqual((len(side["zones"]["stock"]), len(side["zones"]["level"]), len(side["zones"]["clock"])), (game.FLASH_STOCK, 2, 0))
        self.assertNotEqual(state["phase"], "mulligan")

    def test_the_hand_drawn_again_is_the_size_it_was_dealt(self):
        state = game.new_game([(1, "me", [1] * 20), (2, "cpu", [1] * 20)], shuffle=lambda cards: None)
        state["players"]["1"]["zones"]["deck"].append(state["players"]["1"]["zones"]["hand"].pop())  # a smaller hand, say
        game.flash_start(state)
        deck = state["players"]["1"]["zones"]["deck"]
        play(state, "1", {"type": "flash_level", "uids": [deck[0]["uid"], deck[1]["uid"]]})
        self.assertEqual(len(state["players"]["1"]["zones"]["hand"]), game.STARTING_HAND - 1)

    def test_only_its_owner_sees_the_deck_to_choose_from(self):
        state = flash_table()
        mine, theirs = game.view(state, "1"), game.view(state, "2")
        self.assertEqual((len(mine["flash"]["deck"]), mine["flash"]["need"], mine["flash"]["opponent"]), (20, 2, False))
        self.assertIn(2, game.visible_cards(mine))
        self.assertNotIn(1, {c["card"] for c in theirs["opponent"]["zones"]["level"]})
        self.assertIsNone(game.spectator_view(state, "1")["flash"])
        deck = state["players"]["1"]["zones"]["deck"]
        play(state, "1", {"type": "flash_level", "uids": [deck[0]["uid"], deck[1]["uid"]]})
        self.assertIsNone(game.view(state, "1")["flash"]["deck"])
        self.assertTrue(game.view(state, "2")["flash"]["opponent"])

    def test_the_cpu_takes_its_highest_level_cards_of_its_main_color(self):
        state = flash_table()
        info = lambda pk: CARDS.get(pk, {})
        action = cpu.next_action(state, "2", info)
        self.assertEqual(action["type"], "flash_level")
        deck = {c["uid"]: c["card"] for c in state["players"]["2"]["zones"]["deck"]}
        self.assertEqual(sorted(deck[uid] for uid in action["uids"]), [3, 3])  # no anchors: level 3 beats level 2, whatever the color
        play(state, "2", action)
        self.assertEqual(cpu.next_action(state, "2", info)["type"], "mulligan")

    def picks(self, deck, colors):
        state = game.new_game([(1, "me", [1] * 20), (2, "cpu", deck)], shuffle=lambda cards: None)
        game.flash_start(state)
        state["players"]["2"]["anchor_colors"] = colors
        action = cpu.next_action(state, "2", lambda pk: CARDS.get(pk, {}))
        cards = {c["uid"]: c["card"] for c in state["players"]["2"]["zones"]["deck"]}
        return sorted(cards[uid] for uid in action["uids"])

    def test_with_anchors_the_cpu_takes_level_0_cards_of_their_colors(self):
        deck = [1] * 6 + [5] * 6 + [3] * 4 + [4] * 2 + [6] * 2
        self.assertEqual(self.picks(deck, ["Red", "Blue"]), [1, 5])
        self.assertEqual(self.picks(deck, ["Blue", "Blue"]), [5, 5])  # both anchors one color: two of it

    def test_a_climax_only_when_its_the_last_of_that_color(self):
        self.assertEqual(self.picks([1] * 10 + [6] * 2 + [3] * 8, ["Red", "Blue"]), [1, 6])

    def test_a_color_with_no_level_0_card_falls_back(self):
        self.assertEqual(self.picks([1] * 10 + [3] * 2 + [2] * 8, ["Red", "Blue"]), [1, 3])  # no Blue level 0: its best card instead


class AnchorColorTests(SoloSetup):
    def test_an_express_decks_anchor_colors_in_order(self):
        red, blue = Card.objects.filter(expansion_id=7)[:2]
        Card.objects.filter(pk=red.pk).update(color="Red")
        Card.objects.filter(pk=blue.pk).update(color="Blue")
        deck = CardList.objects.create(user=self.staff, name="Express", express={"anchors": [blue.pk, red.pk]})
        self.assertEqual(anchor_colors(deck), ["Blue", "Red"])
        self.assertEqual(anchor_colors(CardList.objects.create(user=self.staff, name="Built by hand")), [])
        self.assertEqual(anchor_colors(None), [])

    def test_a_flash_battle_gives_the_cpu_them(self):
        CardListEntry.objects.filter(card_list__reserved_for_cpu=True).update(quantity=20)
        settings(flash_percent=100)
        anchor = Card.objects.filter(expansion_id=7).first()
        Card.objects.filter(pk=anchor.pk).update(color="Green")
        CardList.objects.filter(reserved_for_cpu=True).update(express={"anchors": [anchor.pk, anchor.pk]})
        self.fight()
        room = self.room()
        self.assertEqual(room.state["players"][str(room.guest_id)]["anchor_colors"], ["Green", "Green"])


class FlashPathTests(SoloSetup):
    def test_any_fight_but_a_boss_can_be_one(self):
        settings(flash_percent=100, event_percent=0)
        path = self.climb(6)
        flash = path["flash"]
        for f, floor in enumerate(path["floors"]):
            for c, pk in enumerate(floor):
                self.assertEqual([f, c] in flash, pk is not None and not challenge.is_boss(path, f), (f, c))

    def test_none_at_zero(self):
        settings(flash_percent=0)
        self.assertFalse(self.climb(3).get("flash"))

    def test_its_fight_is_dealt_as_one_and_the_path_says_so(self):
        CardListEntry.objects.filter(card_list__reserved_for_cpu=True).update(quantity=20)
        settings(flash_percent=100)
        self.path()
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "spire-flash-tag")
        self.fight()
        room = self.room()
        me = room.state["players"][str(room.host_id)]
        self.assertEqual((room.state["flash"], me["zones"]["hand"]), ({"picked": []}, []))
        board = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()["board"]
        self.assertEqual(len(board["flash"]["deck"]), len(me["zones"]["deck"]))

    def test_an_ordinary_fight_isnt(self):
        CardListEntry.objects.filter(card_list__reserved_for_cpu=True).update(quantity=20)
        settings(flash_percent=0)
        self.fight()
        self.assertNotIn("flash", self.room().state)

    def test_staff_set_the_chance(self):
        form ={"event_percent": "60", "flash_percent": "35", "start_packs": "20", **{f"loadout_{buff}": "0" for buff in challenge.LOADOUT_BUFFS},
                **{f"coop_loadout_{buff}": "0" for buff in challenge.LOADOUT_BUFFS}, **{f"tier_{i}": "3" for i in range(len(challenge.INFINITE_TIERS))},
                "coop_loss_limit": "3", "coop_start_packs": "20", "boss_every": "5", "coop_boss_every": "5", "coop_boss_health": "42"}
        self.client.post(reverse("weiss:cpu_infinite_settings"), form)
        self.assertEqual(ChallengeSettings.current().flash_percent, 35)
        self.assertEqual(challenge.flash_chance(), .35)
