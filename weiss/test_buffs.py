import json
import random
from collections import Counter

from django.http import QueryDict
from django.urls import reverse

from . import buffs, challenge, packs, scenes
from .models import ArcadeEntry, ArcadeRun, Card, ChallengeRun, GameRoom, Scene
from .test_challenge import ArcadeSetup
from .test_packs import make_set

GIFTS = """cast rapi as Rapi
rapi enters
give extra_packs
offer 3: Take one
choice Which?
- The lucky one (set greedy, give lucky_pack)
- Nothing
give random
"""


class ScriptTests(ArcadeSetup):
    def test_buff_lines(self):
        scene, errors = scenes.compile_scene(GIFTS + "offer climax_pack, wild_pack")
        self.assertEqual(errors, [])
        steps = scene["steps"]
        self.assertEqual(steps[1], {"line": 3, "do": "give", "buff": "extra_packs"})
        self.assertEqual(steps[2], {"line": 4, "do": "offer", "prompt": "Take one", "count": 3})
        self.assertEqual(steps[3]["options"][0], {"text": "The lucky one", "goto": None, "set": "greedy", "give": "lucky_pack"})
        self.assertEqual(steps[4]["buff"], "random")
        self.assertEqual(steps[5]["choices"], ["climax_pack", "wild_pack"])

    def test_buffs_that_dont_exist(self):
        errors = dict(scenes.compile_scene("give gold\noffer gold, lucky_pack\nchoice x\n- y (give gold)\n- z (dance)")[1])
        self.assertIn("no buff called “gold”", errors[1])
        self.assertIn("no buff called “gold”", errors[2])
        self.assertIn("no buff called “gold”", errors[4])
        self.assertIn("(give buff)", errors[5])

    def test_resolved_for_a_challenge_and_left_out_otherwise(self):
        compiled = scenes.compile_scene(GIFTS)[0]
        payload = scenes.scene_payload(compiled, "Gifts", "k")
        live = buffs.resolve(payload, True, random.Random(1))
        self.assertTrue(live["buffs"])
        self.assertEqual(live["steps"][1]["name"], "Two more packs")
        self.assertEqual(len(live["steps"][2]["options"]), 3)
        self.assertEqual(len({o["buff"] for o in live["steps"][2]["options"]}), 3)
        self.assertIn(live["steps"][4]["buff"], buffs.BUFFS)  # random, settled now
        self.assertEqual(live["steps"][3]["options"][0]["give_name"], "Lucky pack")
        off = buffs.resolve(payload, False)
        self.assertEqual([s["do"] for s in off["steps"]], ["enter", "skip", "skip", "choice", "skip"])
        self.assertNotIn("give", off["steps"][3]["options"][0])
        self.assertEqual(off["steps"][3]["options"][0]["set"], "greedy")  # flags still count

    def test_what_a_page_says_was_given_is_checked(self):
        payload = buffs.resolve(scenes.scene_payload(scenes.compile_scene(GIFTS)[0], "Gifts"), True, random.Random(1))
        offered = payload["steps"][2]["options"][1]["buff"]
        self.assertEqual(buffs.given(payload, [[1, None], [2, 1], [3, 0], [4, None]]),
                         ["extra_packs", offered, "lucky_pack", payload["steps"][4]["buff"]])
        # Steps that give nothing, options that don't exist, the same step twice, and nonsense are left out.
        self.assertEqual(buffs.given(payload, [[0, None], [2, 9], [3, 1], [1, None], [1, None], "x", [99, None], [2, "0"]]), ["extra_packs"])
        self.assertEqual(buffs.given({**payload, "buffs": False}, [[1, None]]), [])


class ChallengeBuffBase(ArcadeSetup):
    def setUp(self):
        super().setUp()
        self.cards = make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=3, CR=2, R=4, RR=2, SR=4)
        for card in self.cards:
            card.level, card.color = (None, "Red") if card.card_type == "Climax" else (card.pk % 4, ("Red", "Blue")[card.pk % 2])
            card.save()
        make_set(expansion_id=8, name="Vol.8", C=8, R=2)
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "free", "scenario": self.scenario.pk})
        self.run = challenge.current(self.staff)

    def claim(self, buff, **data):
        buffs.grant(self.run, [buff])
        key = self.run.rewards[-1]["key"]
        response = self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": key, **data})
        self.run.refresh_from_db()
        return response

    def pulled(self):
        return Counter({Card.objects.get(pk=int(pk)): n for pk, n in self.run.pool.items()})


class ClaimTests(ChallengeBuffBase):
    def test_granting(self):
        buffs.grant(self.run, ["extra_packs", "second_chance", "climax_pack"], "Gifts")
        self.run.refresh_from_db()
        self.assertEqual((self.run.packs, self.run.lives), (challenge.START_PACKS + buffs.EXTRA_PACKS, 1))
        self.assertEqual([(r["buff"], r["source"]) for r in self.run.rewards], [("climax_pack", "Gifts")])
        page = self.client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "Rewards to claim")
        self.assertContains(page, "Climax pack")
        self.assertContains(page, "Second chance ×1")

    def test_a_lucky_pack(self):
        self.assertRedirects(self.claim("lucky_pack", set=7), reverse("weiss:arcade_challenge_opened"))
        slots = Counter(pull["slot"] for pull in self.run.last_opening["packs"][0])
        self.assertEqual(slots, {"Uncommon": 3, "Climax": 1, "Rare": 2, "Foil": 2})
        self.assertEqual(sum(self.run.pool.values()), 8)
        self.assertEqual(self.run.rewards, [])

    def test_themed_packs(self):
        self.claim("climax_pack", set=7)
        self.assertTrue(all(card.card_type == "Climax" for card in self.pulled()))
        ChallengeRun.objects.filter(pk=self.run.pk).update(pool={})
        self.run.refresh_from_db()
        self.claim("level_pack", set=7, level=2)
        self.assertTrue(all(card.level == 2 for card in self.pulled()))
        ChallengeRun.objects.filter(pk=self.run.pk).update(pool={})
        self.run.refresh_from_db()
        self.claim("color_pack", set=7, color="Blue")
        self.assertTrue(all(card.color == "Blue" for card in self.pulled()))
        self.assertEqual(sum(self.run.pool.values()), 8)

    def test_a_themed_pack_is_mostly_plain_cards(self):
        pool = packs.Pool([c for c in self.cards if c.rarity in ("R", "SR")])
        common = next(slot for slot in packs.PACK if slot.name == "Common")  # no commons: falls back to what there is
        odds = dict(pool.odds(common))
        self.assertEqual(odds["R"], odds["SR"] * 5)

    def test_pack_rewards_keep_to_the_challenges_sets_except_a_wild_one(self):
        self.run.sets = [8]  # a narrative challenge's
        self.run.save()
        self.claim("lucky_pack", set=7)
        self.assertEqual(len(self.run.rewards), 1)  # not claimed
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": self.run.rewards[0]["key"], "set": 8})
        self.run.refresh_from_db()
        self.assertEqual(self.run.rewards, [])
        self.assertEqual({card.expansion_id for card in self.pulled()}, {8})
        self.claim("wild_pack", set=7)
        self.assertEqual({card.expansion_id for card in self.pulled()}, {7, 8})
        self.assertEqual(self.run.rewards, [])

    def test_three_of_a_kind(self):
        card = self.cards[0]
        self.run.pool = {str(card.pk): 1}
        self.run.save()
        challenge.save_deck(self.run, {card.pk: 1})
        self.claim("copies", card=card.pk)
        self.assertEqual(self.run.pool[str(card.pk)], 4)
        self.claim("copies", card=self.cards[1].pk)  # not in the deck
        self.assertEqual(len(self.run.rewards), 1)

    def test_an_exchange(self):
        common, other = [c for c in self.cards if c.rarity == "C"][:2]
        rare = next(c for c in self.cards if c.rarity == "R")
        self.run.pool = {str(common.pk): 2}
        self.run.save()
        challenge.save_deck(self.run, {common.pk: 2})
        buffs.grant(self.run, ["exchange"])
        key = self.run.rewards[0]["key"]
        page = self.client.get(reverse("weiss:arcade_challenge_exchange"), {"key": key, "give": common.pk})
        self.assertIn(other, page.context["choices"])
        self.assertNotIn(rare, page.context["choices"])
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": key, "give": common.pk, "take": rare.pk})
        self.run.refresh_from_db()
        self.assertEqual(self.run.pool, {str(common.pk): 2})  # a different rarity: refused
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": key, "give": common.pk, "take": other.pk})
        self.run.refresh_from_db()
        self.assertEqual(self.run.pool, {str(common.pk): 1, str(other.pk): 1})
        self.assertEqual(self.run.deck.entries.get(card=common).quantity, 1)  # the deck can't keep what's gone

    def test_a_trade_in(self):
        a, b = self.cards[:2]
        self.run.pool = {str(a.pk): 3, str(b.pk): 3}
        self.run.packs = 0
        self.run.save()
        self.claim("trade_in", **{f"trade-{a.pk}": 3, f"trade-{b.pk}": 1})  # 4: not enough
        self.assertEqual((self.run.packs, len(self.run.rewards)), (0, 1))
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": self.run.rewards[0]["key"], f"trade-{a.pk}": 3, f"trade-{b.pk}": 2})
        self.run.refresh_from_db()
        self.assertEqual((self.run.packs, self.run.pool, self.run.rewards), (1, {str(b.pk): 1}, []))

    def test_a_climax_pick(self):
        climax = next(c for c in self.cards if c.card_type == "Climax")
        self.claim("climax_pick", card=self.cards[0].pk)  # not a climax
        self.assertEqual(self.run.pool, {})
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": self.run.rewards[0]["key"], "card": climax.pk})
        self.run.refresh_from_db()
        self.assertEqual(self.run.pool, {str(climax.pk): 2})

    def test_claiming_is_once(self):
        buffs.grant(self.run, ["climax_pack"])
        key = self.run.rewards[0]["key"]
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": key, "set": 7})
        self.client.post(reverse("weiss:arcade_challenge_claim"), {"key": key, "set": 7})
        self.run.refresh_from_db()
        self.assertEqual(sum(self.run.pool.values()), 8)


class SceneBuffFlowTests(ChallengeBuffBase):
    def setUp(self):
        super().setUp()
        scene = Scene.objects.create(name="Gifts", script=GIFTS)
        ArcadeEntry.objects.filter(cpu=self.opener).update(scene_before=scene)
        self.client.post(reverse("weiss:arcade_challenge_open"), {"set": 7, "count": 10})
        self.run.refresh_from_db()
        deck, room = {}, 50
        for pk, n in self.run.pool.items():
            deck[pk] = min(n, 2, room)
            room -= deck[pk]
        self.assertIsNone(challenge.save_deck(self.run, deck))

    def test_a_scenes_buffs_are_the_players_at_its_end(self):
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        scene = room.state["scenes"][0]
        self.assertTrue(scene["buffs"])
        url = reverse("weiss:play_action", args=[room.pk])
        data = self.post(url, {"type": "scene_done", "key": scene["key"], "buffs": [[1, None], [3, 0], [3, 1]]}).json()
        self.assertEqual(data["redirect"], reverse("weiss:arcade_challenge"))  # off to claim them and change the deck
        self.run.refresh_from_db()
        self.assertEqual(self.run.packs, challenge.START_PACKS - 10 + buffs.EXTRA_PACKS)  # two more packs, at once
        self.assertEqual([r["buff"] for r in self.run.rewards], ["lucky_pack"])  # the second pick of one step doesn't count
        # Back to the fight: it's dealt again, with the deck as it is now.
        card = next(iter(self.run.pool))
        challenge.save_deck(self.run, {card: 1})
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        self.assertTrue(room.state["cpu_intro"])
        me = room.state["players"][str(self.staff.pk)]
        self.assertEqual(sum(len(zone) if isinstance(zone, list) else 0 for zone in me["zones"].values()), 1)

    def test_no_buffs_outside_a_challenge(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("weiss:arcade_start"), {"scenario": self.scenario.pk, "deck": self.deck.pk})
        room = GameRoom.objects.get(host=self.alice)
        scene = room.state["scenes"][0]
        self.assertFalse(scene["buffs"])
        data = self.post(reverse("weiss:play_action", args=[room.pk]), {"type": "scene_done", "key": scene["key"], "buffs": [[1, None]]}).json()
        self.assertNotIn("redirect", data)

    def test_a_second_chance(self):
        buffs.grant(self.run, ["second_chance"])
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.end_fight("cpu")
        self.run.refresh_from_db()
        self.assertEqual((self.run.status, self.run.lives, self.run.arcade_run.status), ("active", 0, ArcadeRun.Status.ACTIVE))
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual((data["arcade"]["challenge"]["going"], data["arcade"]["challenge"]["lives"]), (True, 0))
        data = self.post(reverse("weiss:play_action", args=[room.pk]), {"type": "arcade_retry"}).json()
        self.assertTrue(data["intro"])
        self.assertNotIn("scene", data)  # a retry doesn't play the scene again
        self.end_fight("cpu")
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, "lost")
