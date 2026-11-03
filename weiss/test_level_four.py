import re
from collections import Counter
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import reverse

from . import challenge, game, play
from .models import GameRoom
from .test_challenge import ArcadeSetup
from .test_packs import make_set


class LevelFourTests(ArcadeSetup):
    """A challenge's fight that ends the real way: the CPU levelling up to level 4, not a game_over written in."""

    def setUp(self):
        super().setUp()
        make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4)
        self.client.force_login(self.staff)

    def cpu_reaches_level_four(self, kind):
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": kind, "scenario": self.scenario.pk})
        run = challenge.current(self.staff)
        challenge.open_packs(run, 7, 3)
        challenge.save_deck(run, {pk: min(n, 4) for pk, n in run.pool.items()})
        node = challenge.choices(challenge.path_of(run), 0)[0] if kind == "infinite" else None
        self.client.post(reverse("weiss:arcade_challenge_fight"), {"node": node} if node is not None else {})
        room = GameRoom.objects.get(host=self.staff)
        state = room.state
        state.pop("cpu_intro", None)
        state.pop("rps", None)
        state.update(phase="main", turn=str(room.host_id), turn_number=6, mulligan_done=state["order"])
        cpu_side = state["players"][str(room.guest_id)]
        cpu_side["zones"]["level"] = [game.new_card(self.card.pk) for _ in range(3)]
        cpu_side["zones"]["clock"] = [game.new_card(self.card.pk) for _ in range(7)]  # it has to level up, to 4
        room.save()
        play.cpu_step(GameRoom.objects.get(pk=room.pk), wait=False)
        room = GameRoom.objects.get(pk=room.pk)
        self.assertEqual(room.state["game_over"]["winner"], str(room.host_id))
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertTrue(data["board"]["game_over"]["won"])
        return data

    def test_a_free_challenge(self):
        self.cpu_reaches_level_four("free")

    def test_an_infinite_challenge(self):
        data = self.cpu_reaches_level_four("infinite")
        self.assertIn("prize", data)  # the Victory screen's slot machine: what play.js draws it with (prizeSlotHtml)


class ScriptNameTests(SimpleTestCase):
    def test_no_script_has_two_functions_of_one_name(self):
        # In one scope the later one silently replaces the earlier: the Victory screen's slot machine once lost
        # its function to the board's stage slots, and an infinite challenge's win froze.
        for path in (Path(__file__).parent / "static" / "weiss").glob("*.js"):
            names = Counter(re.findall(r"^\s*(?:async\s+)?function\s+(\w+)", path.read_text(encoding="utf-8"), re.M))
            self.assertEqual([name for name, n in names.items() if n > 1], [], path.name)
