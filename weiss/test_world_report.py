from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import world
from .models import WorldReport, WorldSettings
from .test_world import SET, make_set, staff_user
from .test_world_access import AccessBase, open_world
from .world_views import REPORT_EMPTY, REPORT_LIMIT, REPORT_MAX, REPORT_SAID, REPORT_TOO_LONG, REPORT_TOO_MANY


class ReportBase(AccessBase):
    def setUp(self):
        super().setUp()
        open_world()
        self.client.force_login(self.alice)

    def send(self, text="The pack didn’t open", page="/weiss/world/1/town/", slot=1, **extra):
        return self.client.post(reverse("weiss:world_report", args=[slot]), {"text": text, "page": page, **extra})


class ReportTests(ReportBase):
    def test_a_report_keeps_the_words_and_the_save_as_it_was(self):
        response = self.send(text="  The pack didn’t open  ")
        self.assertEqual(response.json(), {"said": REPORT_SAID})
        report = WorldReport.objects.get()
        self.assertEqual((report.user, report.save_ref, report.text, report.page, report.resolved),
                         (self.alice, self.save, "The pack didn’t open", "/weiss/world/1/town/", False))
        self.assertEqual(report.state["slot"], 1)
        self.assertEqual(report.state["version"], self.save.version)
        self.assertIn("place", report.state["town"])

    def test_a_report_is_kept_even_when_the_town_cannot_be_read(self):
        with mock.patch.object(world, "town", side_effect=RuntimeError("the town is broken")), \
                self.assertLogs("weiss.world_views", level="ERROR"):
            response = self.send(text="The town is blank")
        self.assertEqual((response.status_code, response.json()), (200, {"said": REPORT_SAID}))
        report = WorldReport.objects.get()
        self.assertEqual(report.text, "The town is blank")
        self.assertEqual(report.state["slot"], 1)
        self.assertEqual(report.state["version"], self.save.version)
        self.assertEqual(report.state["town_error"], "RuntimeError: the town is broken")
        self.assertNotIn("town", report.state)

    def test_the_report_gets_through_when_the_page_is_out_of_step(self):
        self.save.version += 5
        self.save.save(update_fields=["version"])
        self.assertEqual(self.send().status_code, 200)
        self.assertEqual(WorldReport.objects.count(), 1)

    def test_empty_text_is_refused(self):
        for text in ("", "   \n\t "):
            response = self.send(text=text)
            self.assertEqual((response.status_code, response.json()), (400, {"error": REPORT_EMPTY}))
        self.assertFalse(WorldReport.objects.exists())

    def test_the_text_limit(self):
        self.assertEqual(self.send(text="x" * REPORT_MAX).status_code, 200)
        response = self.send(text="x" * (REPORT_MAX + 1))
        self.assertEqual((response.status_code, response.json()), (400, {"error": REPORT_TOO_LONG}))
        self.assertEqual(WorldReport.objects.count(), 1)

    def test_the_page_is_optional_and_kept_to_its_length(self):
        self.client.post(reverse("weiss:world_report", args=[1]), {"text": "Broken"})
        self.assertEqual(WorldReport.objects.get().page, "")
        self.send(text="Again", page="x" * 400)
        self.assertEqual(WorldReport.objects.latest("pk").page, "x" * 300)

    def test_a_player_is_limited_to_reports_an_hour(self):
        for n in range(REPORT_LIMIT):
            self.assertEqual(self.send(text=f"Problem {n}").status_code, 200)
        response = self.send(text="One more")
        self.assertEqual((response.status_code, response.json()), (429, {"error": REPORT_TOO_MANY}))
        self.assertEqual(WorldReport.objects.count(), REPORT_LIMIT)

    def test_reports_older_than_an_hour_do_not_count(self):
        for n in range(REPORT_LIMIT):
            self.send(text=f"Problem {n}")
        WorldReport.objects.update(created=timezone.now() - timedelta(hours=2))
        self.assertEqual(self.send(text="Later").status_code, 200)

    def test_the_limit_is_per_player_not_per_slot(self):
        world.start(self.alice, 2, SET)
        for n in range(REPORT_LIMIT):
            self.send(text=f"Problem {n}")
        self.assertEqual(self.send(text="Other slot", slot=2).status_code, 429)

    def test_someone_elses_slot_is_not_found(self):
        response = self.send(slot=2)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(WorldReport.objects.exists())

    def test_a_closed_world_takes_no_reports(self):
        open_world(False)
        response = self.send()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(WorldReport.objects.exists())

    def test_reports_are_posted_not_read(self):
        self.assertEqual(self.client.get(reverse("weiss:world_report", args=[1])).status_code, 405)

    def test_the_counter_reads_the_open_reports_on_staff_pages(self):
        self.send()
        self.client.force_login(staff_user("boss"))
        self.assertEqual(self.client.get(reverse("weiss:sets")).context["open_reports"], 1)
        self.client.force_login(self.alice)
        self.assertNotIn("open_reports", self.client.get(reverse("weiss:sets")).context)


class StaffReportTests(ReportBase):
    def setUp(self):
        super().setUp()
        self.send(text="First one")
        self.send(text="Second one")
        self.first = WorldReport.objects.get(text="First one")
        self.client.force_login(self.staff)

    def test_the_list_shows_open_reports_first_with_their_slot_and_state(self):
        response = self.client.get(reverse("weiss:world_reports"))
        self.assertEqual(response.status_code, 200)
        rows = response.context["reports"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["player"], "alice")
        self.assertEqual(rows[0]["slot"], 1)
        self.assertEqual(rows[0]["update_url"], reverse("weiss:world_report_update", args=[rows[0]["pk"]]))
        self.assertIn('"slot": 1', rows[0]["state_json"])
        self.assertEqual(response.context["open_count"], 2)

    def test_resolving_and_noting_a_report(self):
        response = self.client.post(reverse("weiss:world_report_update", args=[self.first.pk]), {"resolved": "1", "staff_note": "  Fixed in the pack code  "})
        self.assertRedirects(response, reverse("weiss:world_reports"))
        self.first.refresh_from_db()
        self.assertEqual((self.first.resolved, self.first.staff_note), (True, "Fixed in the pack code"))
        self.assertEqual(self.client.get(reverse("weiss:world_reports")).context["open_count"], 1)

    def test_an_unchecked_resolve_reopens_it(self):
        self.first.resolved = True
        self.first.save()
        self.client.post(reverse("weiss:world_report_update", args=[self.first.pk]), {"staff_note": "Still looking"})
        self.first.refresh_from_db()
        self.assertEqual((self.first.resolved, self.first.staff_note), (False, "Still looking"))

    def test_resolved_reports_come_after_the_open_ones(self):
        self.first.resolved = True
        self.first.save()
        rows = self.client.get(reverse("weiss:world_reports")).context["reports"]
        self.assertEqual([row["resolved"] for row in rows], [False, True])

    def test_a_player_cannot_change_a_report(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.post(reverse("weiss:world_report_update", args=[self.first.pk]), {"resolved": "1"}).status_code, 403)
        self.first.refresh_from_db()
        self.assertFalse(self.first.resolved)
