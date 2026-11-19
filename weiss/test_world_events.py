"""World mode: the calendar, events (WorldEvent), the card shop's sales and the weekly tournament."""
import datetime

from django.test import TestCase
from django.urls import reverse

from . import world, world_calendar as calendar, world_events as events
from .models import CpuSchedule, WorldEvent, WorldPlace
from .test_world import SET, everywhere_rule, give_cpu, make_set, staff_user

MONDAY, WEDNESDAY, FRIDAY, SATURDAY, SUNDAY = 0, 2, 4, 5, 6
MORNING, NOON, EVENING, NIGHT = 0, 1, 2, 3


def turn_of(day, time=MORNING):
    return day * 4 + time


class CalendarTests(TestCase):
    def test_every_save_starts_on_monday_18_november(self):
        self.assertEqual(calendar.date_label(0), "Monday 18 November")
        self.assertEqual(calendar.full_label(0), "Monday 18 November, Year 1")
        self.assertEqual(calendar.season_of(0), "Autumn")

    def test_the_weekday_is_the_one_the_town_always_used(self):
        for turn in range(0, 4 * 800, 3):
            self.assertEqual(calendar.weekday_of(turn), (turn // 4) % 7)

    def test_months_years_and_leap_years_are_real(self):
        new_year = (datetime.date(2025, 1, 1) - calendar.START).days
        self.assertEqual(calendar.date_label(turn_of(new_year - 1)), "Tuesday 31 December")
        self.assertEqual((calendar.year_of(turn_of(new_year - 1)), calendar.year_of(turn_of(new_year))), (1, 2))
        self.assertEqual(calendar.season_of(turn_of(new_year)), "Winter")
        leap = (datetime.date(2028, 2, 29) - calendar.START).days
        self.assertEqual((calendar.month_day(turn_of(leap)), calendar.year_of(turn_of(leap))), ("02-29", 5))


class EventBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cards = make_set()
        for expansion_id in range(9, 13):
            make_set(expansion_id)

    def setUp(self):
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.save.money = 50000
        self.save.save()

    def at(self, day, time=MORNING, place=None):
        """The save at this day and time (and place), as if it had got there."""
        self.save.turn = turn_of(day, time)
        self.save.flags.pop("choose", None)
        if place:
            self.save.place = place
        self.save.save()
        return self.save


class WhenEventsRunTests(EventBase):
    def test_the_first_events_and_when_they_run(self):
        featured = WorldEvent.objects.get(key="featured-set")
        happy = WorldEvent.objects.get(key="specialty-happy-hour")
        self.assertTrue(all(events.runs(featured, turn_of(WEDNESDAY, time)) for time in range(4)))
        self.assertFalse(events.runs(featured, turn_of(WEDNESDAY + 1)))
        self.assertTrue(events.runs(featured, turn_of(WEDNESDAY + 7)))  # every week
        self.assertEqual([events.runs(happy, turn_of(FRIDAY, time)) for time in range(4)], [False, False, True, False])
        self.assertTrue(events.runs(happy, turn_of(FRIDAY), all_day=True))

    def test_every_other_week_first_week_months_and_dates(self):
        event = WorldEvent(key="x", name="X", kind="sale", weekdays=[MONDAY], every=2, offset=1, first_week=2)
        self.assertEqual([events.runs(event, turn_of(7 * week)) for week in range(6)], [False, False, False, True, False, True])
        christmas = WorldEvent(key="xmas", name="Christmas", kind="sale", dates=["12-25"])
        day = (datetime.date(2024, 12, 25) - calendar.START).days
        self.assertEqual([events.runs(christmas, turn_of(d)) for d in (day - 1, day, day + 1, day + 365)], [False, True, False, True])
        winter = WorldEvent(key="w", name="W", kind="sale", months=[12, 1, 2], weekdays=[SATURDAY])
        self.assertFalse(events.runs(winter, turn_of(SATURDAY)))  # 23 November
        self.assertTrue(events.runs(winter, turn_of(SATURDAY + 14)))  # 7 December

    def test_the_notice_board_week_runs_monday_to_sunday(self):
        self.at(WEDNESDAY + 7)
        week = events.week(self.save)
        self.assertEqual([day["weekday"] for day in week], list(calendar.DAYS))
        self.assertEqual([day["today"] for day in week].index(True), WEDNESDAY)
        self.assertEqual(week[0]["label"], "25 November")
        self.assertIn("Featured set", [event["name"] for event in week[WEDNESDAY]["events"]])
        self.assertIn("The weekly tournament", [event["name"] for event in week[SUNDAY]["events"]])

    def test_switched_off_events_are_not_on(self):
        WorldEvent.objects.filter(key="featured-set").update(enabled=False)
        self.at(WEDNESDAY)
        self.assertIsNone(events.sale(self.save, "packs"))

    def test_the_town_and_its_pages_show_the_date_and_events(self):
        self.at(WEDNESDAY)
        town = world.town(self.save)
        self.assertEqual(town["date"], "Wednesday 20 November")
        self.assertEqual([event["key"] for event in town["events"]["today"]], ["featured-set"])
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("weiss:world_events", args=[1])), "Featured set")
        self.assertContains(self.client.get(reverse("weiss:world_home")), "Wednesday 20 November, Year 1")


class SaleTests(EventBase):
    def test_the_featured_set_is_on_the_shelves_at_half_price_up_to_its_limit(self):
        self.at(WEDNESDAY, place="shop")
        featured = events.featured_set(self.save)
        stock = world.shop_stock(self.save)
        self.assertIn(featured["id"], [entry["id"] for entry in stock])  # put on the shelves for the sale
        base = world.pack_price()
        self.assertEqual(events.pack_cost(self.save, featured["id"], 1)[0], base // 2)
        self.assertEqual(events.pack_cost(self.save, SET, 1)[0], base)  # only the featured set
        before = self.save.money
        world.buy_packs(self.save, featured["id"], 3)
        self.assertEqual(before - self.save.money, 3 * (base // 2))
        self.assertEqual(events.pack_cost(self.save, featured["id"], 5)[0], 2 * (base // 2) + 3 * base)  # 2 left at the sale price
        shown = next(entry for entry in world.shop(self.save)["stock"] if entry["id"] == featured["id"])
        self.assertEqual((shown["price"], shown["was"], shown["sale_left"]), (base // 2, base, 2))

    def test_the_sale_limit_is_for_the_day(self):
        self.at(WEDNESDAY, place="shop")
        featured = events.featured_set(self.save)
        world.buy_packs(self.save, featured["id"], 5)
        self.assertEqual(events.pack_cost(self.save, featured["id"], 1)[0], world.pack_price())
        self.at(WEDNESDAY + 7, place="shop")  # next week: a new featured set, a fresh limit
        self.assertEqual(events.sale_left(self.save, events.sale(self.save, "packs")), 5)

    def test_specialty_happy_hour_is_friday_evening(self):
        base = world.specialty_price()
        self.at(FRIDAY, NOON, place="shop")
        self.assertEqual(events.specialty_cost(self.save), (base, base))
        self.at(FRIDAY, EVENING, place="shop")
        self.assertEqual(events.specialty_cost(self.save), (round(base * .7), base))
        self.assertEqual(world.shop(self.save)["specialty_was"], base)

    def test_single_card_saturday(self):
        base = world.card_price()
        self.at(SATURDAY, place="shop")
        self.assertEqual(events.card_cost(self.save), (round(base * .75), base))
        cards = world.shop_cards(self.save)
        self.assertEqual(len(cards), world.SHOP_CARDS + 2)
        before = self.save.money
        world.buy_card(self.save, cards[0].pk)
        self.assertEqual(before - self.save.money, round(base * .75))


class TournamentTests(EventBase):
    def setUp(self):
        super().setUp()
        self.save.pool = {str(card.pk): 4 for card in self.cards}
        self.save.save()
        climaxes = [card for card in self.cards if card.card_type == "Climax"][:2]
        others = [card for card in self.cards if card.card_type != "Climax"][:14]
        world.save_deck(self.save, {card.pk: 4 for card in climaxes} | {card.pk: 3 for card in others})
        self.cpus = [give_cpu(f"Duelist {n}", self.cards) for n in range(9)]
        for cpu in self.cpus:
            everywhere_rule(cpu, "plaza")
        self.event = WorldEvent.objects.get(key="weekly-tournament")

    def enter(self):
        self.at(SATURDAY, NOON, place="arena")
        return events.enter(self.save)

    def play(self, won):
        """The player duels their opponent now, at the arena, and wins or loses."""
        opponent = events.opponent(self.save)
        self.assertIsNotNone(opponent)
        self.assertIn(opponent, [cpu.pk for cpu, _ in world.present(self.save)])  # there to duel
        room = world.start_duel(self.save, opponent)
        self.assertTrue(events.is_round(self.save, room))
        over = {"winner": str(room.host_id if won else room.guest_id), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over
        room.save(update_fields=["state"])
        world.game_finished(room, over)
        self.save.refresh_from_db()
        if world.choosing(self.save):
            world.travel(self.save, "arena")
        return opponent

    def points(self, cpu_id):
        return self.save.relations.get(str(cpu_id), {}).get("points", 0)

    def test_entry_is_at_the_arena_on_saturday_or_first_thing_sunday(self):
        self.at(WEDNESDAY, place="arena")
        with self.assertRaisesRegex(ValueError, "opens on Saturday"):
            events.enter(self.save)
        self.at(SATURDAY, place="plaza")
        with self.assertRaisesRegex(ValueError, "Enter at the Duel arena"):
            events.enter(self.save)
        self.at(SUNDAY, NOON, place="arena")
        with self.assertRaisesRegex(ValueError, "closed"):
            events.enter(self.save)
        self.at(SUNDAY, MORNING, place="arena")
        before = self.save.money
        found = events.enter(self.save)
        self.assertEqual(before - self.save.money, 500)
        self.assertEqual(len(found["entrants"]), events.ENTRANTS)
        self.assertEqual(len(set(found["entrants"])), events.ENTRANTS)
        with self.assertRaisesRegex(ValueError, "entered already"):
            events.enter(self.save)

    def test_the_draw_and_the_coin_flips_never_change_on_reload(self):
        found = self.enter()
        first = events.bracket(self.save, found)
        self.save.refresh_from_db()
        again = events.bracket(self.save, events.entry(self.save))
        self.assertEqual(first, again)
        cpu_matches = [match for rounds in first for match in rounds if events.PLAYER not in match[:2] and None not in match[:2]]
        self.assertTrue(all(winner in (a, b) for a, b, winner in cpu_matches))

    def test_three_wins_make_the_champion_and_only_the_beaten_get_points(self):
        self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        beaten = []
        for _ in range(3):
            before = self.save.money
            beaten.append(self.play(won=True))
        self.assertEqual(self.save.money - before, 3000)  # the champion's prize, not a duel's payout
        found = events.entry(self.save)
        self.assertTrue(found["champion"])
        self.assertTrue(any("pack" in reward.lower() for reward in self.save.flags["last_duel"]["rewards"]))  # and the lucky pack
        for cpu_id in beaten:
            self.assertEqual(self.points(cpu_id), world.gain(cpu_id, 8))
        others = set(found["entrants"]) - set(beaten)
        self.assertTrue(all(self.points(cpu_id) == 0 for cpu_id in others))
        self.assertIn("champion", self.save.flags["last_duel"]["event"])

    def test_losing_the_semi_final_pays_its_prize_and_gives_no_points(self):
        self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        self.play(won=True)
        before = self.save.money
        opponent = self.play(won=False)
        self.assertEqual(self.save.money - before, 600)
        self.assertEqual(self.points(opponent), 0)
        self.assertEqual(events.entry(self.save)["out"], 1)
        self.assertIsNone(events.opponent(self.save))

    def test_losing_round_1_pays_nothing(self):
        self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        before = self.save.money
        self.play(won=False)
        self.assertEqual(self.save.money, before)
        self.assertEqual(events.entry(self.save)["out"], 0)

    def test_a_round_missed_is_a_forfeit(self):
        self.enter()
        self.at(SUNDAY, MORNING, place="plaza")
        self.save.flags["test_mode"] = True
        world.wait(self.save, staff=True)
        found = events.entry(self.save)
        self.assertEqual((found["results"], found["out"]), ({"0": "forfeit"}, 0))

    def test_the_opponent_is_only_at_the_arena_for_their_round(self):
        found = self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        opponent = events.opponent(self.save)
        self.assertIn(opponent, found["entrants"])
        self.assertEqual(world.town(self.save)["people"][[p["id"] for p in world.town(self.save)["people"]].index(opponent)]["tournament"], "Round 1")
        self.at(SATURDAY, NOON, place="arena")
        self.assertIsNone(events.opponent(self.save))

    def test_a_round_isnt_played_for_stakes(self):
        self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        with self.assertRaisesRegex(ValueError, "stakes"):
            world.start_duel(self.save, events.opponent(self.save), high_stakes=True)

    def test_the_notice_board_shows_the_bracket_and_enters(self):
        self.at(SATURDAY, NOON, place="arena")
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_events", args=[1]))
        self.assertContains(page, "Enter · 500 coins")
        self.client.post(reverse("weiss:world_event_enter", args=[1]))
        page = self.client.get(reverse("weiss:world_events", args=[1]))
        self.assertContains(page, "Next: <strong>Round 1</strong> on Sunday morning", html=False)
        self.assertContains(page, "Semi-final")


    def test_talk_in_tournament_week_is_its_own_context(self):
        self.at(WEDNESDAY, place="plaza")
        self.assertIsNone(events.talk_context(self.save, self.cpus[0].pk))  # not the tournament's days: the usual greetings
        self.at(SATURDAY, NOON, place="plaza")
        self.assertEqual(events.talk_context(self.save, self.cpus[0].pk), "tournament_spectator")  # before entering
        found = self.enter()
        entrant, outsider = found["entrants"][0], next(cpu.pk for cpu in self.cpus if cpu.pk not in found["entrants"])
        self.assertEqual(events.talk_context(self.save, entrant), "tournament_entrant")
        self.assertEqual(events.talk_context(self.save, outsider), "tournament_spectator")
        self.at(SUNDAY, MORNING, place="arena")
        self.play(won=False)  # out in Round 1: the player's result comes first
        self.assertEqual(events.talk_context(self.save, entrant), "tournament_out")
        self.assertEqual(events.talk_context(self.save, outsider), "tournament_out")

    def test_champion_talk_once_the_player_has_won_the_tournament(self):
        self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        for _ in range(3):
            self.play(won=True)
        self.assertEqual(events.talk_context(self.save, self.cpus[0].pk), "tournament_champion")

    def test_the_round_opponents_duel_line_is_the_tournament_one(self):
        from . import chatter
        from .models import Chatter, CpuProfile
        found = self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        opponent = CpuProfile.objects.get(pk=events.opponent(self.save))
        Chatter.objects.create(cpu=opponent, context="tournament_duel", min_rank=0, script="them: Round one. Let's go.")
        Chatter.objects.create(cpu=opponent, context="before_duel", min_rank=0, script="them: Just a duel.")
        self.assertEqual(world.duel_intro(self.save, opponent), "Round one. Let's go.")
        other = CpuProfile.objects.get(pk=next(pk for pk in found["entrants"] if pk != opponent.pk))
        Chatter.objects.create(cpu=other, context="before_duel", min_rank=0, script="them: Just a duel.")
        self.assertEqual(world.duel_intro(self.save, other), "Just a duel.")  # not their round: their own line


    def test_talking_on_tournament_day_plays_the_tournament_line(self):
        from .models import Chatter
        self.at(SATURDAY, NOON, place="plaza")
        here = next(cpu for cpu, _ in world.present(self.save))  # someone who's at the plaza now
        row = Chatter.objects.create(cpu=here, context="tournament_spectator", min_rank=0, script="them: Tournament day!")
        world.talk(self.save, here.pk)
        self.assertEqual(self.save.today["talk"]["chatter"], f"db:{row.pk}")


class StaffTests(EventBase):
    def test_staff_edit_events(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("weiss:world_events_staff")), "Specialty happy hour")
        event = WorldEvent.objects.get(key="featured-set")
        form = {"event": event.pk, "name": "Featured set", "kind": "sale", "weekdays": [1, 3], "times": [], "every": 2, "offset": 0,
                "first_week": 1, "months": "", "dates": "12-25", "place": "", "enabled": "on",
                "settings": '{"what": "packs", "featured": true, "discount": 40, "limit": 3}'}
        self.client.post(reverse("weiss:world_events_staff"), form)
        event.refresh_from_db()
        self.assertEqual((event.weekdays, event.every, event.first_week, event.dates, event.settings["discount"]), ([1, 3], 2, 1, ["12-25"], 40))
        self.client.post(reverse("weiss:world_events_staff"), {**form, "settings": '{"what": "everything", "discount": 40}'})
        event.refresh_from_db()
        self.assertEqual(event.settings["what"], "packs")  # refused

    def test_test_mode_jumps_to_a_weekday(self):
        self.save.flags["test_mode"] = True
        self.save.save()
        world.jump(self.save, SATURDAY)
        self.assertEqual((calendar.weekday_of(self.save.turn), self.save.turn % 4), (SATURDAY, MORNING))
        world.jump(self.save, SATURDAY)
        self.assertEqual(self.save.turn, turn_of(SATURDAY + 7))  # the next one
        self.save.flags["test_mode"] = False
        with self.assertRaisesRegex(ValueError, "test mode"):
            world.jump(self.save, MONDAY)


from . import quests  # noqa: E402
from .models import PlayerProfile, Quest  # noqa: E402


class TimedQuestTests(EventBase):
    """Timed quests (a window) and the notice board's (board): offered while the window's open, expiring when it
    closes, done again each week."""

    def fresh(self):
        self.save.refresh_from_db()
        for attr in ("_quests", "_quest_lookup"):
            self.save.__dict__.pop(attr, None)
        return self.save

    def finish_bounty(self, key="bounty-three-duelists"):
        quest = Quest.objects.get(key=key)
        for cpu_id in (1, 2, 3):
            quests.tick(self.save, quest, "0.0", value=cpu_id)
        quests.advance(self.save)
        return quest

    def test_what_a_timed_quest_can_and_cannot_be(self):
        base = {"key": "q", "title": "Q", "about": "x", "stages": [{"text": "Go", "objectives": [{"do": "flag", "flag": "f", "text": "F"}]}],
                "endings": [{"key": "e", "title": "E"}]}
        self.assertEqual(quests.check({**base, "board": True, "window": {}})[1], [])
        problems = quests.check({**base, "board": True})[1]
        self.assertTrue(any("give it a window" in p for p in problems), problems)
        problems = quests.check({**base, "board": True, "window": {"weekdays": [9]}})[1]
        self.assertTrue(any("weekdays are a list of 0 to 6" in p for p in problems), problems)
        problems = quests.check({**base, "board": True, "window": {}, "endings": [{"key": "e", "title": "E", "locks": ["other"]}]})[1]
        self.assertTrue(any("can't close quests" in p for p in problems), problems)
        objective = {"do": "event", "event": "weekly-tournament", "result": "lose"}
        problems = quests.check({**base, "board": True, "window": {}, "stages": [{"text": "Go", "objectives": [objective]}]})[1]
        self.assertTrue(any("result is one of" in p for p in problems), problems)

    def test_a_bounty_is_taken_done_and_claimed_once_a_week(self):
        self.at(MONDAY)
        self.assertIn("bounty-three-duelists", [notice["key"] for notice in quests.board(self.save) if notice["state"] == "offered"])
        quests.accept(self.save, None, "bounty-three-duelists")
        self.assertEqual(quests.journal(self.save)["active"][0]["ends"], "Sunday night")
        self.finish_bounty()
        self.assertEqual(quests.status(self.save, "bounty-three-duelists"), "settling")
        before = self.save.money
        quests.choose(self.save, None, "bounty-three-duelists", "claim", True)
        self.assertEqual(self.save.money - before, 400)
        self.assertEqual(quests.log(self.save)["bounty-three-duelists"]["count"], 1)
        self.assertNotIn("bounty-three-duelists", [n["key"] for n in quests.board(self.save) if n["state"] == "offered"])  # not again this week
        self.at(MONDAY + 7)
        self.assertIn("bounty-three-duelists", [n["key"] for n in quests.board(self.save) if n["state"] == "offered"])  # back next week
        quests.accept(self.save, None, "bounty-three-duelists")
        self.assertEqual(quests.log(self.save)["bounty-three-duelists"]["count"], 1)  # the count's kept

    def test_a_timed_quest_expires_when_its_week_ends_and_comes_back(self):
        self.at(SATURDAY, NIGHT)
        quests.accept(self.save, None, "bounty-villain")
        self.save.save()
        self.at(SUNDAY, NIGHT)
        world.time_passed(self.save)  # into Monday: a new week
        self.assertEqual(quests.status(self.save, "bounty-villain"), "expired")
        self.assertIn("Out of time", " ".join(item["text"] for item in self.save.quests.get("news", [])))
        self.assertIn("bounty-villain", [n["key"] for n in quests.board(self.save) if n["state"] == "offered"])  # on offer again

    def test_a_quest_tied_to_an_event_is_only_on_while_it_is(self):
        self.at(FRIDAY)
        self.assertNotIn("tournament-day", [n["key"] for n in quests.board(self.save)])
        self.at(SATURDAY)
        self.assertIn("tournament-day", [n["key"] for n in quests.board(self.save)])

    def test_the_notice_board_takes_and_claims(self):
        self.at(MONDAY)
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_events", args=[1]))
        self.assertContains(page, "Bounty: three duelists")
        self.client.post(reverse("weiss:world_board", args=[1]), {"act": "take", "quest": "bounty-three-duelists"})
        self.assertEqual(quests.status(self.fresh(), "bounty-three-duelists"), "active")
        self.finish_bounty()
        self.save.save()
        before = self.save.money
        self.client.post(reverse("weiss:world_board", args=[1]), {"act": "claim", "quest": "bounty-three-duelists", "ending": "claim"})
        self.assertEqual(self.fresh().money - before, 400)

    def test_the_map_marks_places_with_an_event_on(self):
        self.at(SATURDAY)
        arena = next(place for place in world.town(self.save)["places"] if place["key"] == "arena")
        self.assertEqual([event["icon"] for event in arena["events"]], ["🏆"])
        self.at(MONDAY)
        self.assertEqual(next(place for place in world.town(self.save)["places"] if place["key"] == "arena")["events"], [])


class TournamentQuestTests(TournamentTests):
    """Event objectives and the sleeve count, through the tournament (TournamentTests' setup and helpers only: its own
    tests aren't run twice)."""

    locals().update({name: None for name in dir(TournamentTests) if name.startswith("test_")})

    def test_winning_a_round_counts_for_the_tournament_day_notice(self):
        self.at(SATURDAY, NOON, place="arena")
        quests.accept(self.save, None, "tournament-day")
        events.enter(self.save)
        self.at(SUNDAY, MORNING, place="arena")
        self.play(won=True)
        self.save.__dict__.pop("_quests", None)
        self.assertEqual(quests.status(self.save, "tournament-day"), "settling")

    def test_the_champion_counts_for_sleeves(self):
        self.enter()
        self.at(SUNDAY, MORNING, place="arena")
        for _ in range(3):
            self.play(won=True)
        self.assertEqual(PlayerProfile.objects.get(user=self.user).progress.get("world_events"), 1)
