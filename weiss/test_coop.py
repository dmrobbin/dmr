import json
import random
from unittest import mock

from django.contrib.auth.models import Group, User
from django.urls import reverse

from core.access import WEISS_GROUP

from . import buffs, challenge, coop, play
from .models import ArcadeRun, CardList, ChallengeRun, ChallengeSettings, CoopRun, GameRoom, Scene
from .test_arcade import player
from .test_challenge import ArcadeSetup
from .test_events import EVENT_SCRIPT
from .test_packs import make_set, run_with_climaxes


def staff_player(name):
    """Challenge mode is staff only for now."""
    user = User.objects.create_user(name, password="x", is_staff=True)
    Group.objects.get_or_create(name=WEISS_GROUP)[0].user_set.add(user)
    return user


class CoopSetup(ArcadeSetup):
    """A co-op challenge started by staff and joined by bo, with a set to open packs from."""

    def setUp(self):
        super().setUp()
        self.cards = make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4)
        self.bo = staff_player("bo")
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "coop"})
        self.host = challenge.current(self.staff)
        self.pair = self.host.coop

    def join(self):
        self.client.force_login(self.bo)
        self.client.post(reverse("weiss:arcade_coop_join", args=[self.pair.invite_token]))
        self.client.force_login(self.staff)
        self.pair.refresh_from_db()
        return challenge.current(self.bo)

    def fresh(self, user):
        return challenge.current(user)


class StartingTests(CoopSetup):
    def test_the_host_waits_for_a_partner_with_an_invite_link(self):
        self.assertEqual((self.pair.status, self.pair.host, self.pair.guest, self.pair.loss_limit), (CoopRun.Status.WAITING, self.staff, None, coop.LOSS_LIMIT))
        self.assertEqual((self.host.kind, self.host.name, self.host.packs), (ChallengeRun.Kind.INFINITE, coop.NAME, coop.START_PACKS))
        page = self.client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "Waiting for your partner")
        self.assertContains(page, reverse("weiss:arcade_coop_join", args=[self.pair.invite_token]))
        self.assertNotContains(page, "Reset challenge")

    def test_joining_by_the_link(self):
        self.client.force_login(self.bo)
        page = self.client.get(reverse("weiss:arcade_coop_join", args=[self.pair.invite_token]))
        self.assertContains(page, "Join as staff's partner")
        guest = self.join()
        self.assertEqual((self.pair.status, self.pair.guest), (CoopRun.Status.ACTIVE, self.bo))
        self.assertEqual((guest.coop, guest.packs, guest.user), (self.pair, coop.START_PACKS, self.bo))
        self.assertNotEqual(guest.deck, self.host.deck)
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Playing with <strong>bo</strong>")
        third = staff_player("cy")
        self.assertRaisesMessage(ValueError, "joined this co-op challenge already", coop.join, self.pair, third)

    def test_any_player_can_start_or_join_one(self):
        self.client.force_login(self.alice)  # not staff
        self.client.post(reverse("weiss:arcade_coop_join", args=[self.pair.invite_token]))
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.guest, self.alice)
        ann = player("ann")
        self.client.force_login(ann)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "coop"})
        self.assertEqual(challenge.current(ann).coop.host, ann)

    def test_not_while_busy_with_a_challenge_or_your_own(self):
        challenge.start(self.bo, ChallengeRun.Kind.INFINITE, None)
        self.client.force_login(self.bo)
        self.assertContains(self.client.get(reverse("weiss:arcade_coop_join", args=[self.pair.invite_token])), "You have a challenge of your own under way")
        self.assertRaisesMessage(ValueError, "Finish your own challenge first", coop.join, self.pair, self.bo)
        self.assertRaisesMessage(ValueError, "your own co-op challenge", coop.join, self.pair, self.staff)
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.status, CoopRun.Status.WAITING)

    def test_the_host_can_call_it_off_before_anyone_joins(self):
        deck = self.host.deck
        self.client.post(reverse("weiss:arcade_coop_cancel"))
        self.assertFalse(CoopRun.objects.exists())
        self.assertFalse(CardList.objects.filter(pk=deck.pk).exists())
        self.assertIsNone(challenge.current(self.staff))

    def test_each_player_starts_with_the_coop_settings(self):
        ChallengeSettings.objects.create(pk=1, coop_loss_limit=5, coop_start_packs=4, coop_loadout={"climax_pick": 1}, start_packs=9)
        self.client.post(reverse("weiss:arcade_coop_cancel"))
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "coop"})
        host = challenge.current(self.staff)
        self.pair = host.coop
        guest = self.join()
        self.assertEqual(self.pair.loss_limit, 5)
        for run in (host, guest):
            self.assertEqual((run.packs, [r["buff"] for r in run.rewards]), (4, ["climax_pick"]))


class SharedPoolTests(CoopSetup):
    def setUp(self):
        super().setUp()
        self.guest = self.join()

    def test_both_players_packs_open_into_one_pool(self):
        challenge.open_packs(self.host, 7, 2, random.Random(1))
        challenge.open_packs(self.guest, 7, 1, random.Random(2))  # its pool was loaded before the host's packs
        self.pair.refresh_from_db()
        self.assertEqual(sum(self.pair.pool.values()), 3 * 8)
        self.assertEqual((self.fresh(self.staff).packs, self.fresh(self.bo).packs), (coop.START_PACKS - 2, coop.START_PACKS - 1))
        self.assertEqual(self.fresh(self.staff).pool, self.fresh(self.bo).pool)

    def test_a_copy_in_one_deck_cant_go_in_the_other(self):
        card = self.cards[0].pk
        self.pair.pool = {str(card): 3}
        self.pair.save()
        self.assertIsNone(challenge.save_deck(self.fresh(self.staff), {card: 2}))
        guest = self.fresh(self.bo)
        self.assertEqual(challenge.pool_cards(guest)[0][1:], (1, 0))  # one copy left for bo
        self.assertIn("Your partner's deck has those copies", challenge.save_deck(guest, {card: 2}))
        self.assertIsNone(challenge.save_deck(guest, {card: 1}))
        self.assertIn("Your partner's deck", challenge.save_deck(self.fresh(self.staff), {card: 3}))

    def test_both_see_the_whole_pool_with_the_partners_copies_shown(self):
        card, other = self.cards[0], self.cards[1]
        self.pair.pool = {str(card.pk): 2, str(other.pk): 3}
        self.pair.save()
        challenge.save_deck(self.fresh(self.staff), {card.pk: 2, other.pk: 1})
        self.assertEqual(challenge.deck_pool(self.fresh(self.bo)), [(card, 0, 0, 2), (other, 2, 0, 1)])
        self.client.force_login(self.bo)
        page = self.client.get(reverse("weiss:arcade_challenge_deck"))
        self.assertContains(page, f'data-card="{card.pk}" data-name="{card.name}" data-pulled="0" data-in-deck="0" data-theirs="2"')  # still shown, greyed
        self.assertContains(page, "<strong>2</strong> in staff's deck · 2 in the pool")
        self.assertContains(page, "<strong>1</strong> in staff's deck · 3 in the pool")
        self.assertContains(page, "See staff's deck")

    def test_each_change_is_saved_and_the_partners_page_catches_up(self):
        card, other = self.cards[0], self.cards[1]
        self.pair.pool = {str(card.pk): 3, str(other.pk): 1}
        self.pair.save()
        self.client.force_login(self.staff)
        page = self.client.get(reverse("weiss:arcade_challenge_deck"))
        self.assertContains(page, "data-live")
        self.assertContains(page, "bo's deck")  # on the left
        self.assertContains(page, "Your deck")  # on the right
        self.assertNotContains(page, "Save deck")  # each change is saved as it's made
        saved = self.client.post(reverse("weiss:arcade_challenge_deck"), {"deck": json.dumps({card.pk: 2})}, HTTP_ACCEPT="application/json").json()
        self.assertEqual(saved, {"error": None, "mine": {str(card.pk): 2}, "theirs": {}, "pool": {str(card.pk): 3, str(other.pk): 1}})
        self.client.force_login(self.bo)
        state = self.client.get(reverse("weiss:arcade_challenge_deck_state")).json()
        self.assertEqual((state["mine"], state["theirs"]), ({}, {str(card.pk): 2}))
        refused = self.client.post(reverse("weiss:arcade_challenge_deck"), {"deck": json.dumps({card.pk: 2})}, HTTP_ACCEPT="application/json").json()
        self.assertIn("Your partner's deck has those copies", refused["error"])
        self.assertEqual(refused["mine"], {})  # the page goes back to what's saved

    def test_a_solo_deck_builder_lists_the_deck_on_the_right_and_saves_on_request(self):
        run = challenge.start(self.alice, ChallengeRun.Kind.INFINITE, None)
        run.pool = {str(self.cards[0].pk): 2}
        run.save()
        self.client.force_login(self.alice)
        page = self.client.get(reverse("weiss:arcade_challenge_deck"))
        self.assertContains(page, "Your deck")
        self.assertContains(page, "Save deck")
        self.assertNotContains(page, "data-live")
        self.assertNotContains(page, "partner-side")

    def test_each_can_look_at_the_partners_deck_but_not_change_it(self):
        card = self.cards[0]
        self.pair.pool = {str(card.pk): 3}
        self.pair.save()
        challenge.save_deck(self.fresh(self.staff), {card.pk: 3})
        self.client.force_login(self.bo)
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "See their deck")
        page = self.client.get(reverse("weiss:arcade_coop_partner_deck"))
        self.assertContains(page, "staff's deck")
        self.assertContains(page, f"{card.name} <strong>×3</strong>")
        self.assertNotContains(page, "Save deck")
        self.client.post(reverse("weiss:arcade_coop_partner_deck"), {"deck": "{}"})
        self.assertEqual(self.fresh(self.staff).deck.entries.get().quantity, 3)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("weiss:arcade_coop_partner_deck")), "Their deck is empty so far.")

    def test_taking_from_the_pool_trims_the_decks_own_first(self):
        card = self.cards[0].pk
        self.pair.pool = {str(card): 4}
        self.pair.save()
        challenge.save_deck(self.fresh(self.staff), {card: 2})
        challenge.save_deck(self.fresh(self.bo), {card: 2})
        host = self.fresh(self.staff)
        buffs.take_from_pool(host, {card: 3})
        self.assertEqual(host.deck.entries.count(), 0)
        self.assertEqual(self.fresh(self.bo).deck.entries.get().quantity, 1)

    def test_rewards_claimed_go_in_the_pool_too(self):
        host = self.fresh(self.staff)
        buffs.grant(host, ["climax_pick"])
        climax = next(card for card in self.cards if card.card_type == "Climax")
        buffs.claim(self.fresh(self.staff), self.fresh(self.staff).rewards[0]["key"], {"card": str(climax.pk)})
        self.assertEqual(self.fresh(self.bo).pool, {str(climax.pk): buffs.CLIMAX_COPIES})
        self.assertEqual(self.fresh(self.bo).rewards, [])  # the reward was the host's

    def test_a_trade_in_only_gives_up_what_the_partner_isnt_using(self):
        card, other = self.cards[0].pk, self.cards[1].pk
        self.pair.pool = {str(card): 4, str(other): 1}
        self.pair.save()
        challenge.save_deck(self.fresh(self.bo), {card: 4})
        buffs.grant(self.fresh(self.staff), ["trade_in"])
        host = self.fresh(self.staff)
        with self.assertRaisesMessage(ValueError, "Choose 5 cards"):
            buffs.claim(host, host.rewards[0]["key"], {f"trade-{card}": "4", f"trade-{other}": "1"})


class PlayingSetup(CoopSetup):
    """Both players in, with decks."""

    def setUp(self):
        super().setUp()
        self.guest = self.join()
        challenge.open_packs(self.fresh(self.staff), 7, 2, random.Random(1))
        pool = self.fresh(self.staff).pool
        half = dict(list(pool.items())[: len(pool) // 2])
        challenge.save_deck(self.fresh(self.staff), {pk: n for pk, n in half.items()})
        challenge.save_deck(self.fresh(self.bo), {pk: n for pk, n in pool.items() if pk not in half})
        for user in (self.staff, self.bo):
            run_with_climaxes(self.fresh(user))

    def as_(self, user):
        self.client.force_login(user)
        return self

    def path(self, user):
        return challenge.path_of(self.fresh(user))

    def vote(self, user, node):
        return self.as_(user).client.post(reverse("weiss:arcade_challenge_fight"), {"node": node})

    def room_of(self, user):
        return GameRoom.objects.get(host=user, coop_duel=None)  # their fight, not a vs. battle

    def finish(self, user, won):
        """End this player's game, as if the last move had just been made."""
        room = self.room_of(user)
        room.state.pop("cpu_intro", None)
        room.state.pop("scenes", None)
        who = room.host_id if won else room.guest_id

        def ends(state, *args, **kwargs):
            state["game_over"] = {"winner": str(who), "reason": "level", "rematch": []}
            return {}
        with mock.patch.object(play.game, "apply", side_effect=ends):
            play.play_action(room, room.host_id, {"type": "x"}, lookups={"info": None})

    def both_vote_and_fight(self, mine=None, theirs=None):
        at = challenge.floor_at(self.fresh(self.staff))
        options = challenge.choices(self.path(self.staff), at)
        self.vote(self.staff, options[0] if mine is None else mine)
        self.vote(self.bo, options[0] if theirs is None else theirs)
        self.vote(self.staff, options[0])  # the host's page: on to the fight decided


class PlayingTests(PlayingSetup):
    def test_the_floor_waits_for_both_votes(self):
        options = challenge.choices(self.path(self.staff), 0)
        page = self.as_(self.staff).client.post(reverse("weiss:arcade_challenge_fight"), {"node": options[0]}, follow=True)
        self.assertFalse(GameRoom.objects.exists())
        self.assertContains(page, "Your vote is in")
        self.assertContains(self.as_(self.staff).client.get(reverse("weiss:arcade_challenge")), "Your vote")
        self.assertContains(self.as_(self.bo).client.get(reverse("weiss:arcade_challenge")), "staff's vote")
        self.vote(self.bo, options[0])
        self.assertEqual(GameRoom.objects.get().host, self.bo)  # decided: the second voter goes straight to it
        self.assertEqual(self.path(self.staff)["picks"], [options[0]])
        self.vote(self.staff, options[0])
        self.assertEqual(GameRoom.objects.filter(host=self.staff).count(), 1)
        self.assertEqual(self.room_of(self.staff).cpu_profile_id, self.room_of(self.bo).cpu_profile_id)

    def test_a_disagreement_is_settled_by_a_coin_flip(self):
        options = challenge.choices(self.path(self.staff), 0)
        self.assertGreater(len(options), 1)
        self.vote(self.staff, options[0])
        with mock.patch("weiss.challenge.random.choice", side_effect=lambda seq: seq[-1]):
            self.vote(self.bo, options[1])
        path = self.path(self.staff)
        self.assertEqual(path["picks"], [options[1]])  # bo's: the coin's side
        self.assertTrue(path["decided"]["flip"])
        page = self.as_(self.staff).client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "The coin flip went to")

    def test_no_voting_before_a_partner_joins(self):
        pair = CoopRun.objects.create(host=staff_player("cy"))
        run = coop.new_half(pair.host, pair)
        self.client.force_login(pair.host)
        self.client.post(reverse("weiss:arcade_challenge_fight"), {"node": 1})
        self.assertFalse(GameRoom.objects.filter(host=pair.host).exists())

    def test_a_player_who_finishes_first_votes_on_and_waits(self):
        self.both_vote_and_fight()
        self.finish(self.staff, won=True)
        host = self.fresh(self.staff)
        self.assertEqual((challenge.floor_at(host), coop.pair_floor(host), challenge.floor_at(self.fresh(self.bo))), (1, 0, 0))
        self.assertEqual(host.packs, coop.START_PACKS - 2 + challenge.INFINITE_WIN_PACKS)
        self.assertEqual(len(host.rewards), 1)  # the prize
        self.assertContains(self.as_(self.staff).client.get(reverse("weiss:arcade_challenge")), "still on fight 1")
        self.pair.refresh_from_db()
        path = self.pair.path
        cpu_pk = next(pk for pk in path["floors"][1] if pk is not None)
        path["floors"][1] = [cpu_pk] * len(path["floors"][1])  # a full floor: more than one way on, so a vote
        CoopRun.objects.filter(pk=self.pair.pk).update(path=path)
        options = challenge.choices(self.path(self.staff), 1)
        self.assertGreater(len(options), 1)
        self.vote(self.staff, options[0])
        self.assertEqual(GameRoom.objects.filter(host=self.staff).get().state["game_over"]["winner"], str(self.staff.pk))  # no new fight yet
        self.finish(self.bo, won=False)
        self.pair.refresh_from_db()
        self.assertEqual((self.pair.losses, coop.pair_floor(self.fresh(self.bo))), (1, 1))
        self.vote(self.bo, options[0])
        self.assertEqual(self.path(self.bo)["picks"][1], options[0])

    def test_every_loss_counts_until_the_limit_ends_it_for_both(self):
        self.pair.loss_limit = 2
        self.pair.save()
        self.both_vote_and_fight()
        self.finish(self.staff, won=False)
        self.finish(self.bo, won=False)
        self.pair.refresh_from_db()
        self.assertEqual((self.pair.losses, self.pair.status), (2, CoopRun.Status.LOST))
        for user in (self.staff, self.bo):
            run = ChallengeRun.objects.get(user=user)
            self.assertEqual(run.status, ChallengeRun.Status.LOST)
            self.assertTrue(run.deck_snapshot)

    def test_a_second_chance_covers_a_loss(self):
        buffs.grant(self.fresh(self.bo), ["second_chance"])
        self.both_vote_and_fight()
        self.finish(self.bo, won=False)
        self.pair.refresh_from_db()
        self.assertEqual((self.pair.losses, self.fresh(self.bo).lives, challenge.floor_at(self.fresh(self.bo))), (0, 0, 1))

    def test_next_fight_pacts_last_until_both_finish_the_floor(self):
        buffs.grant(self.fresh(self.staff), ["war_chest"])
        self.assertEqual(buffs.fight_mods(self.fresh(self.bo)), ["war_chest"])  # the pair's
        self.both_vote_and_fight()
        self.finish(self.staff, won=True)
        self.assertEqual(buffs.fight_mods(self.fresh(self.bo)), ["war_chest"])
        self.finish(self.bo, won=True)
        self.assertEqual(buffs.fight_mods(self.fresh(self.bo)), [])

    def test_the_game_page_shows_the_pairs_lost_games_and_no_retry(self):
        self.both_vote_and_fight()
        self.finish(self.bo, won=False)
        room = self.room_of(self.bo)
        data = self.as_(self.bo).client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual(data["arcade"]["coop"], {"losses": 1, "limit": coop.LOSS_LIMIT, "partner": "staff"})
        response = self.client.post(reverse("weiss:play_action", args=[room.pk]), json.dumps({"type": "arcade_retry"}), content_type="application/json")
        self.assertEqual(response.status_code, 400)


class EventTests(PlayingSetup):
    def setUp(self):
        super().setUp()
        Scene.objects.create(name="Deal", script=EVENT_SCRIPT, infinite_event=True)
        self.pair.refresh_from_db()
        self.pair.path = {"floors": [[challenge.EVENT, self.opener.pk, None], [self.filler.pk, self.anchor.pk, None]], "picks": [], "done": 0}
        self.pair.save()
        self.vote(self.staff, 0)
        self.vote(self.bo, 0)
        self.payload = self.fresh(self.staff).path["event"]
        self.choice = next(i for i, step in enumerate(self.payload["steps"]) if step["do"] == "choice")
        self.give = next(i for i, step in enumerate(self.payload["steps"]) if step["do"] == "give")

    def event_vote(self, user, option, method="post"):
        data = {"key": self.payload["key"], "step": self.choice, "visit": 1}
        if method == "post":
            data["option"] = option
        return getattr(self.as_(user).client, method)(reverse("weiss:arcade_coop_event_vote"), data).json()

    def test_both_players_go_to_the_event_and_vote_on_its_choices(self):
        page = self.as_(self.bo).client.get(reverse("weiss:arcade_challenge_event"))
        self.assertContains(page, "every choice is a vote")
        self.assertNotContains(page, "Walk away")
        self.assertContains(self.as_(self.staff).client.get(reverse("weiss:arcade_challenge")), "at an event together")
        self.assertEqual(self.event_vote(self.staff, 0), {"decided": None, "flip": False})
        self.assertEqual(self.event_vote(self.staff, None, "get"), {"decided": None, "flip": False})
        self.assertEqual(self.event_vote(self.bo, 0), {"decided": 0, "flip": False})
        self.assertEqual(self.event_vote(self.staff, None, "get")["decided"], 0)

    def test_what_the_event_gives_goes_to_both_and_both_move_on(self):
        self.event_vote(self.staff, 0)
        self.event_vote(self.bo, 0)
        before = {user: self.fresh(user).packs for user in (self.staff, self.bo)}
        picks = [[self.give, None], [self.choice, 0]]
        self.as_(self.bo).client.post(reverse("weiss:arcade_challenge_event_done"), {"key": self.payload["key"], "buffs": json.dumps(picks)})
        for user in (self.staff, self.bo):
            run = self.fresh(user)
            self.assertEqual(run.packs, before[user] + buffs.EXTRA_PACKS)
            self.assertEqual(challenge.floor_at(run), 1)
        self.assertEqual(buffs.fight_mods(self.fresh(self.staff)), ["ambush"])  # once, for the pair
        self.assertNotIn("event", self.fresh(self.staff).path)
        # The other page, ending a moment later, finds it over: nothing more is given.
        self.as_(self.staff).client.post(reverse("weiss:arcade_challenge_event_done"), {"key": self.payload["key"], "buffs": json.dumps(picks)})
        self.assertEqual(self.fresh(self.staff).packs, before[self.staff] + buffs.EXTRA_PACKS)

    def test_a_choice_the_pair_didnt_decide_gives_nothing(self):
        self.event_vote(self.staff, 1)
        self.event_vote(self.bo, 1)
        self.as_(self.bo).client.post(reverse("weiss:arcade_challenge_event_done"),
                                      {"key": self.payload["key"], "buffs": json.dumps([[self.choice, 0]])})
        self.assertEqual(buffs.fight_mods(self.fresh(self.staff)), [])


class EndingTests(PlayingSetup):
    def test_either_player_ends_it_for_both_and_each_keeps_their_own_deck(self):
        self.as_(self.bo).client.post(reverse("weiss:arcade_challenge_end"))
        self.pair.refresh_from_db()
        self.assertEqual(self.pair.status, CoopRun.Status.LOST)
        for user in (self.staff, self.bo):
            self.assertEqual(self.fresh(user).status, ChallengeRun.Status.LOST)
        self.as_(self.staff).client.post(reverse("weiss:arcade_challenge_close"), {"keep": "on", "name": "Ours"})
        self.assertFalse(CardList.objects.get(name="Ours").challenge)
        self.assertIsNone(challenge.current(self.staff))
        self.assertIsNotNone(challenge.current(self.bo))  # bo still decides about their own deck
        self.assertNotContains(self.as_(self.bo).client.get(reverse("weiss:arcade_challenge")), "again from the start")

    def test_no_reset_in_coop(self):
        packs = self.fresh(self.staff).packs
        self.as_(self.staff).client.post(reverse("weiss:arcade_challenge_reset"))
        self.assertEqual(self.fresh(self.staff).packs, packs)
        self.assertEqual(self.fresh(self.staff).coop, self.pair)

    def test_the_leaderboard_adds_up_both_players_scores(self):
        self.assertContains(self.client.get(reverse("weiss:arcade_coop_scores")), "No scores yet")
        self.both_vote_and_fight()
        self.finish(self.staff, won=True)
        self.finish(self.bo, won=True)
        scores = [300, 450]
        for user, score in zip((self.staff, self.bo), scores):
            ArcadeRun.objects.filter(pk=ChallengeRun.objects.get(user=user).arcade_run_id).update(score=score)
        page = self.client.get(reverse("weiss:arcade_coop_scores"))
        self.assertEqual([pair.pk for pair in page.context["pairs"]], [self.pair.pk])
        self.assertEqual((page.context["pairs"][0].score, page.context["pairs"][0].wins), (sum(scores), 2))
        self.assertContains(page, "<strong>bo</strong>")
        decks = self.client.get(reverse("weiss:arcade_coop_deck", args=[self.pair.pk]))
        self.assertContains(decks, "staff's deck")
        self.assertContains(decks, "bo's deck")
        self.assertContains(decks, "data-card-popup-dialog", count=1)
        self.assertNotIn(self.fresh(self.staff), challenge.leaderboard())  # not on the solo board


class SpectateTests(PlayingSetup):
    """A player waiting on their partner's game can watch it, seeing what's public and the partner's hand."""

    def setUp(self):
        super().setUp()
        self.both_vote_and_fight()

    def test_only_while_waiting_on_the_partner(self):
        self.assertNotContains(self.as_(self.staff).client.get(reverse("weiss:arcade_challenge")), "Watch bo")
        page = self.as_(self.staff).client.get(reverse("weiss:arcade_coop_spectate"))
        self.assertRedirects(page, reverse("weiss:play_room", args=[self.room_of(self.staff).pk]))  # their own fight first
        self.assertEqual(self.client.get(reverse("weiss:arcade_coop_status")).json()["watchable"], False)
        self.finish(self.staff, won=True)
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Watch bo's game")
        self.assertEqual(self.client.get(reverse("weiss:arcade_coop_status")).json()["watchable"], True)
        page = self.client.get(reverse("weiss:arcade_coop_spectate"))
        self.assertContains(page, "data-spectate")
        self.assertContains(page, "Watching bo's game")
        self.assertNotContains(page, "data-chat")

    def test_it_shows_the_partners_hand_and_nothing_hidden(self):
        self.finish(self.staff, won=True)
        room = self.room_of(self.bo)
        bo = room.state["players"][str(self.bo.pk)]
        face_down = bo["zones"]["hand"].pop()
        face_down.update(face_down=True)
        room.state["players"][str(self.bo.pk)]["stage"]["C1"] = face_down
        room.state["attack"] = {"step": "counter", "counters": ["x"]}
        room.save()
        data = self.as_(self.staff).client.get(reverse("weiss:arcade_coop_spectate_state")).json()
        board = data["board"]
        self.assertEqual([c["card"] for c in board["me"]["zones"]["hand"]], [c["card"] for c in bo["zones"]["hand"]])
        self.assertEqual(board["me"]["zones"]["deck"], {"count": len(bo["zones"]["deck"])})
        self.assertIsNone(board["me"]["stage"]["C1"]["card"])  # face down: not public
        self.assertIn("count", board["opponent"]["zones"]["hand"])  # the CPU's hand stays hidden
        self.assertNotIn("counters", board["attack"])
        self.assertFalse(board["damage_pending"] or board["level_up_pending"] or board["auto_next"])
        self.assertNotIn("intro", data)
        version = data["version"]
        self.assertEqual(self.client.get(reverse("weiss:arcade_coop_spectate_state"), {"v": version}).status_code, 204)

    def test_watching_cant_play(self):
        self.finish(self.staff, won=True)
        room = self.room_of(self.bo)
        response = self.as_(self.staff).client.post(reverse("weiss:play_action", args=[room.pk]), json.dumps({"type": "chat", "text": "hi"}),
                                                    content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_once_the_partner_has_left_their_game_theres_nothing_to_watch(self):
        self.finish(self.staff, won=True)
        self.room_of(self.bo).delete()
        self.assertEqual(self.as_(self.staff).client.get(reverse("weiss:arcade_coop_spectate_state")).json()["status"], "gone")
        self.assertRedirects(self.client.get(reverse("weiss:arcade_coop_spectate")), reverse("weiss:arcade_challenge"))
