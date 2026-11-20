from django.test import TestCase
from django.urls import reverse

from . import world, world_rewards
from .models import WorldSave, WorldSettings
from .test_world import SET, everywhere_rule, give_cpu, make_set, staff_user


class CardPickTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.save.pool = {str(c.pk): 4 for c in self.cards}
        self.save.packs, self.save.rewards = 0, []
        self.save.save()
        climaxes = [c for c in self.cards if c.card_type == "Climax"][:2]
        self.others = [c for c in self.cards if c.card_type != "Climax"][:14]
        world.save_deck(self.save, {c.pk: 4 for c in climaxes} | {c.pk: 3 for c in self.others})
        self.cinder = give_cpu("Cinder", self.cards)
        self.rule = everywhere_rule(self.cinder, stake=300)
        WorldSettings.objects.update_or_create(pk=1, defaults={"win_payout": 200, "first_win_bonus": 100})

    def finish(self, room, won):
        over = {"winner": str(room.host_id if won else room.guest_id), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over  # as the game has it when it ends
        room.save(update_fields=["state"])
        world.game_finished(room, over)
        self.save.refresh_from_db()
        if world.choosing(self.save):  # back in town, the player answers the map: staying put
            world.travel(self.save, world.place_of(self.save).key)

    def test_a_win_offers_the_cpus_distinct_non_climax_cards(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        offer = self.save.flags["card_pick"]
        self.assertEqual((offer["room"], offer["cpu"], offer["cpu_name"]), (room.pk, self.cinder.pk, "Cinder"))
        self.assertEqual(offer["cards"], [c.pk for c in sorted(self.others, key=lambda c: c.serial_number)])

    def test_a_loss_offers_nothing(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=False)
        self.assertIsNone(self.save.flags.get("card_pick"))

    def test_picking_adds_one_copy_and_clears_the_offer(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        card_id = self.save.flags["card_pick"]["cards"][0]
        before = self.save.pool.get(str(card_id), 0)
        card = world_rewards.pick_card(self.save, card_id)
        self.assertEqual(card.pk, card_id)
        self.assertEqual(self.save.pool[str(card_id)], before + 1)
        self.assertIsNone(self.save.flags.get("card_pick"))

    def test_a_card_thats_not_offered_is_refused(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        climax = next(c for c in self.cards if c.card_type == "Climax")
        with self.assertRaises(ValueError):
            world_rewards.pick_card(self.save, climax.pk)

    def test_picking_twice_is_refused(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        card_id = self.save.flags["card_pick"]["cards"][0]
        world_rewards.pick_card(self.save, card_id)
        with self.assertRaises(ValueError):
            world_rewards.pick_card(self.save, card_id)

    def test_a_second_win_replaces_the_offer(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        first_room = self.save.flags["card_pick"]["room"]
        second = world.start_duel(self.save, self.cinder.pk)
        self.finish(second, won=True)
        self.assertEqual(self.save.flags["card_pick"]["room"], second.pk)
        self.assertNotEqual(second.pk, first_room)

    def test_the_towns_card_pick_shows_the_cards(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        view = world.town(self.save)["card_pick"]
        self.assertEqual(view["cpu"], "Cinder")
        self.assertEqual(len(view["cards"]), 14)
        first = view["cards"][0]
        self.assertEqual(set(first), {"id", "name", "image", "url", "rarity", "color", "level", "type"})

    def test_the_view_answers_with_is_yours(self):
        self.client.force_login(self.user)
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        card_id = self.save.flags["card_pick"]["cards"][0]
        version = WorldSave.objects.get(pk=self.save.pk).version
        answer = self.client.post(reverse("weiss:world_pick_card", args=[1]), {"card": card_id, "version": version}).json()
        self.assertIn("is yours", answer["said"])
        self.assertIsNone(answer["town"]["card_pick"])
