from unittest.mock import MagicMock, patch

from io import StringIO

from botocore.exceptions import ClientError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from django.contrib.auth.models import User

from .job_sources import JSearch, SerpApi
from .models import Document, JobLead, JobSearch


class DocumentTests(TestCase):
    def test_file_type_is_text_after_last_dot(self):
        self.assertEqual(Document(s3_key="docs/report.v2.PDF").file_type, "pdf")

    def test_file_type_ignores_dots_in_folder_names(self):
        self.assertEqual(Document(s3_key="v1.0/readme").file_type, "")


class HomeTests(TestCase):
    def test_home_without_documents_shows_message(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No documents are available")

    def test_home_shows_a_button_per_active_document(self):
        guide = Document.objects.create(title="Guide", s3_key="docs/guide.pdf")
        resume = Document.objects.create(title="Resume", s3_key="docs/resume.docx")
        hidden = Document.objects.create(title="Old", s3_key="old.pdf", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Guide (.pdf)")
        self.assertContains(response, "Resume (.docx)")
        self.assertContains(response, reverse("download", args=[guide.pk]))
        self.assertContains(response, reverse("download", args=[resume.pk]))
        self.assertNotContains(response, reverse("download", args=[hidden.pk]))


class FeaturedDocumentTests(TestCase):
    def test_home_embeds_document_1_instead_of_welcome_text(self):
        document = Document.objects.create(pk=1, title="Resume", s3_key="docs/resume.pdf")
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'<iframe class="featured-viewer" src="{reverse("view_document", args=[document.pk])}#toolbar=0')
        self.assertNotContains(response, "Hi, I'm Daryl.")

    def test_home_falls_back_to_welcome_text_without_document_1(self):
        Document.objects.create(pk=1, title="Resume", s3_key="docs/resume.pdf", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "<iframe")
        self.assertContains(response, "Hi, I'm Daryl.")

    @override_settings(AWS_S3_BUCKET="my-bucket")
    def test_view_document_presigns_inline_pdf_and_allows_same_origin_framing(self):
        document = Document.objects.create(title="Resume", s3_key="docs/resume.pdf")
        fake_s3 = MagicMock()
        fake_s3.generate_presigned_url.return_value = "https://example.com/signed"
        with patch("core.s3.boto3.client", return_value=fake_s3):
            response = self.client.get(reverse("view_document", args=[document.pk]))
        self.assertRedirects(response, "https://example.com/signed", fetch_redirect_response=False)
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        params = fake_s3.generate_presigned_url.call_args.kwargs["Params"]
        self.assertTrue(params["ResponseContentDisposition"].startswith("inline;"))
        self.assertEqual(params["ResponseContentType"], "application/pdf")


class DownloadTests(TestCase):
    def test_download_404_for_missing_document(self):
        self.assertEqual(self.client.get(reverse("download", args=[999])).status_code, 404)

    @override_settings(AWS_S3_BUCKET="my-bucket")
    def test_download_redirects_to_presigned_url(self):
        Document.objects.create(title="Other", s3_key="docs/other.pdf")
        document = Document.objects.create(title="Guide", s3_key="docs/guide.pdf")
        fake_s3 = MagicMock()
        fake_s3.generate_presigned_url.return_value = "https://example.com/signed"
        with patch("core.s3.boto3.client", return_value=fake_s3):
            response = self.client.get(reverse("download", args=[document.pk]))
        self.assertRedirects(response, "https://example.com/signed", fetch_redirect_response=False)
        kwargs = fake_s3.generate_presigned_url.call_args.kwargs
        self.assertEqual(kwargs["Params"]["Bucket"], "my-bucket")
        self.assertEqual(kwargs["Params"]["Key"], "docs/guide.pdf")

    def test_inactive_document_is_not_downloadable(self):
        document = Document.objects.create(title="Old", s3_key="old.pdf", is_active=False)
        self.assertEqual(self.client.get(reverse("download", args=[document.pk])).status_code, 404)


class DashboardTests(TestCase):
    def test_anonymous_visitor_is_sent_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response["Location"])

    def test_non_staff_user_is_sent_to_login(self):
        self.client.force_login(User.objects.create_user("visitor", password="x"))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_staff_user_sees_job_leads(self):
        self.client.force_login(User.objects.create_user("daryl", password="x", is_staff=True))
        JobLead.objects.create(
            title="Backend Engineer",
            expected_compensation="$150k",
            source="LinkedIn",
            application_link="https://example.com/apply",
        )
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Engineer")
        self.assertContains(response, "$150k")
        self.assertContains(response, "https://example.com/apply")

    def test_staff_user_without_leads_sees_message(self):
        self.client.force_login(User.objects.create_user("daryl", password="x", is_staff=True))
        self.assertContains(self.client.get(reverse("dashboard")), "No job leads yet.")


class JobSourceParsingTests(TestCase):
    def test_jsearch_annualizes_hourly_pay_and_hashes_long_ids(self):
        job = JSearch("key").parse({
            "job_id": "x" * 400, "job_title": "Engineer", "employer_name": "Acme",
            "job_min_salary": 50, "job_max_salary": 60, "job_salary_period": "HOUR",
            "job_publisher": "Indeed", "job_posted_at_datetime_utc": "2026-10-25T00:00:00.000Z",
        })
        self.assertEqual(job["min_salary"], 104000)
        self.assertEqual(job["expected_compensation"], "$50–$60/hour")
        self.assertEqual(job["source"], "Indeed via JSearch")
        self.assertLessEqual(len(job["external_id"]), 255)
        self.assertEqual(job["posted_at"].year, 2026)

    def test_serpapi_salary_parsing(self):
        parse = SerpApi("key").parse_salary
        self.assertEqual(parse("120K–150K a year"), (120000, 150000, "YEAR"))
        self.assertEqual(parse("120–150K a year"), (120000, 150000, "YEAR"))
        self.assertEqual(parse("$45–$60 an hour"), (45, 60, "HOUR"))
        self.assertEqual(parse("Full-time"), (None, None, "YEAR"))

    def test_serpapi_reads_pay_and_remote_from_extensions(self):
        job = SerpApi("key").parse({
            "job_id": "abc", "title": "Engineer", "company_name": "Acme", "via": "LinkedIn",
            "extensions": ["4 days ago", "125K–175K a year", "Work from home", "Full-time"],
        })
        self.assertEqual((job["min_salary"], job["max_salary"]), (125000, 175000))
        self.assertEqual(job["expected_compensation"], "$125k–$175k")
        self.assertTrue(job["is_remote"])
        self.assertEqual(job["source"], "LinkedIn via SerpApi")


def fake_job(**overrides):
    job = {
        "external_id": "jsearch:1", "title": "Senior Software Engineer", "company": "Acme",
        "location": "Remote", "is_remote": True, "expected_compensation": "$150k",
        "min_salary": 150000, "max_salary": None, "summary": "", "application_link": "https://example.com",
        "source": "Indeed via JSearch", "posted_at": None,
    }
    return job | overrides


@override_settings(JSEARCH_API_KEY="key", SERPAPI_API_KEY="", JOB_MIN_SALARY=90000)
class FetchJobsCommandTests(TestCase):
    def run_command(self, jobs, *args):
        with patch.object(JSearch, "search", return_value=jobs):
            call_command("fetch_jobs", *args, stdout=StringIO(), stderr=StringIO())

    def test_saves_matching_jobs_and_skips_junior_and_low_pay(self):
        self.run_command([
            fake_job(),
            fake_job(external_id="jsearch:2", title="Junior Software Engineer"),
            fake_job(external_id="jsearch:3", title="Software Engineer", min_salary=60000, max_salary=80000),
            fake_job(external_id="jsearch:4", title="Backend Engineer", min_salary=None),
        ])
        self.assertEqual(
            sorted(JobLead.objects.values_list("title", flat=True)),
            ["Backend Engineer", "Senior Software Engineer"],
        )

    def test_running_twice_does_not_duplicate(self):
        self.run_command([fake_job()])
        self.run_command([fake_job(), fake_job(external_id="serpapi:9")])
        self.assertEqual(JobLead.objects.count(), 1)

    def test_dry_run_saves_nothing(self):
        self.run_command([fake_job()], "--dry-run")
        self.assertEqual(JobLead.objects.count(), 0)

    def test_uses_saved_searches(self):
        JobSearch.objects.all().delete()
        JobSearch.objects.create(query="python developer", location="Denver, CO", remote_only=False)
        with patch.object(JSearch, "search", return_value=[]) as search:
            call_command("fetch_jobs", stdout=StringIO())
        search.assert_called_once_with("python developer", "Denver, CO", False, "week", 1)


class ResumeFolderTests(TestCase):
    def test_new_lead_gets_a_slugged_resume_folder(self):
        lead = JobLead.objects.create(title="Senior Software Engineer (Remote)", company="Acme, Inc.")
        self.assertEqual(lead.custom_resume, "docs/senior-software-engineer-remote/acme-inc/")

    def test_missing_company_uses_placeholder(self):
        self.assertEqual(JobLead.objects.create(title="Engineer").custom_resume, "docs/engineer/unknown-company/")

    @override_settings(AWS_S3_BUCKET="my-bucket")
    def test_creates_folder_object_in_s3_once(self):
        fake_s3 = MagicMock()
        with patch("core.s3.boto3.client", return_value=fake_s3):
            lead = JobLead.objects.create(title="Engineer", company="Acme")
            lead.status = JobLead.Status.APPLIED
            lead.save()
        fake_s3.put_object.assert_called_once_with(Bucket="my-bucket", Key="docs/engineer/acme/", Body=b"")

    @override_settings(AWS_S3_BUCKET="my-bucket")
    def test_s3_failure_does_not_block_saving(self):
        fake_s3 = MagicMock()
        fake_s3.put_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
        with patch("core.s3.boto3.client", return_value=fake_s3), self.assertLogs("core.models", "ERROR"):
            JobLead.objects.create(title="Engineer", company="Acme")
        self.assertEqual(JobLead.objects.count(), 1)

    def test_manually_entered_path_is_kept(self):
        lead = JobLead.objects.create(title="Engineer", custom_resume="resumes/mine.pdf")
        self.assertEqual(lead.custom_resume, "resumes/mine.pdf")


class DashboardListTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("daryl", password="x", is_staff=True))
        JobLead.objects.create(title="Backend Engineer", company="Acme", expected_compensation="$150k",
                               min_salary=150000)
        JobLead.objects.create(title="Frontend Engineer", company="Zeta", expected_compensation="$120k–$200k",
                               min_salary=120000, max_salary=200000)
        JobLead.objects.create(title="Platform Engineer", company="Netflix")

    def titles(self, **params):
        response = self.client.get(reverse("dashboard"), params)
        return [lead.title for lead in response.context["job_leads"]]

    def test_sort_by_title_both_directions(self):
        self.assertEqual(self.titles(sort="title"), ["Backend Engineer", "Frontend Engineer", "Platform Engineer"])
        self.assertEqual(self.titles(sort="-title"), ["Platform Engineer", "Frontend Engineer", "Backend Engineer"])

    def test_sort_by_pay_uses_top_of_range_and_puts_unlisted_last(self):
        self.assertEqual(self.titles(sort="-pay"), ["Frontend Engineer", "Backend Engineer", "Platform Engineer"])
        self.assertEqual(self.titles(sort="pay"), ["Backend Engineer", "Frontend Engineer", "Platform Engineer"])

    def test_unknown_sort_falls_back_to_newest(self):
        self.assertEqual(self.titles(sort="password")[0], "Platform Engineer")

    def test_title_and_company_search(self):
        self.assertEqual(self.titles(title="backend"), ["Backend Engineer"])
        self.assertEqual(self.titles(company="NET"), ["Platform Engineer"])
        self.assertEqual(self.titles(title="engineer", company="zeta"), ["Frontend Engineer"])

    def test_pay_listed_toggle(self):
        self.assertEqual(sorted(self.titles(has_pay="1")), ["Backend Engineer", "Frontend Engineer"])

    def test_applied_leads_hidden_unless_toggled(self):
        JobLead.objects.filter(title="Backend Engineer").update(applied=True)
        self.assertNotIn("Backend Engineer", self.titles())
        self.assertIn("Backend Engineer", self.titles(show_applied="1"))

    def test_applied_checkbox_saves_and_returns_to_same_view(self):
        lead = JobLead.objects.get(title="Backend Engineer")
        back = reverse("dashboard") + "?sort=title"
        response = self.client.post(reverse("lead_applied", args=[lead.pk]), {"applied": "1", "next": back})
        self.assertRedirects(response, back, fetch_redirect_response=False)
        lead.refresh_from_db()
        self.assertTrue(lead.applied)
        # An unticked checkbox sends nothing, which means "not applied".
        self.client.post(reverse("lead_applied", args=[lead.pk]), {"next": back})
        lead.refresh_from_db()
        self.assertFalse(lead.applied)

    def test_applied_checkbox_ignores_offsite_redirects(self):
        lead = JobLead.objects.get(title="Backend Engineer")
        response = self.client.post(reverse("lead_applied", args=[lead.pk]), {"applied": "1", "next": "https://evil.example"})
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_sort_links_keep_filters(self):
        response = self.client.get(reverse("dashboard"), {"title": "engineer", "sort": "title"})
        self.assertContains(response, "?title=engineer&amp;sort=-title")


@override_settings(AWS_S3_BUCKET="my-bucket")
class LeadFilesTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("daryl", password="x", is_staff=True))
        self.fake_s3 = MagicMock()
        patcher = patch("core.s3.boto3.client", return_value=self.fake_s3)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.lead = JobLead.objects.create(title="Engineer", company="Acme")

    def test_detail_lists_files_but_not_the_folder_marker(self):
        from datetime import datetime, timezone
        when = datetime(2026, 10, 1, tzinfo=timezone.utc)
        self.fake_s3.list_objects_v2.return_value = {"Contents": [
            {"Key": "docs/engineer/acme/", "Size": 0, "LastModified": when},
            {"Key": "docs/engineer/acme/resume.pdf", "Size": 2048, "LastModified": when},
        ]}
        response = self.client.get(reverse("lead_detail", args=[self.lead.pk]))
        self.assertEqual([f["name"] for f in response.context["files"]], ["resume.pdf"])
        self.assertContains(response, f'{reverse("lead_file", args=[self.lead.pk])}?name=resume.pdf')
        self.fake_s3.list_objects_v2.assert_called_with(Bucket="my-bucket", Prefix="docs/engineer/acme/", Delimiter="/")

    def test_download_presigns_file_in_lead_folder(self):
        self.fake_s3.generate_presigned_url.return_value = "https://example.com/signed"
        response = self.client.get(reverse("lead_file", args=[self.lead.pk]), {"name": "resume.pdf"})
        self.assertRedirects(response, "https://example.com/signed", fetch_redirect_response=False)
        params = self.fake_s3.generate_presigned_url.call_args.kwargs["Params"]
        self.assertEqual(params["Key"], "docs/engineer/acme/resume.pdf")
        self.assertTrue(params["ResponseContentDisposition"].startswith("attachment;"))

    def test_download_rejects_paths_outside_the_folder(self):
        response = self.client.get(reverse("lead_file", args=[self.lead.pk]), {"name": "../../Daryl-Robbin-Resume.pdf"})
        self.assertEqual(response.status_code, 404)

    def test_upload_puts_file_in_lead_folder(self):
        upload = SimpleUploadedFile("My Resume.pdf", b"%PDF-1.4", content_type="application/pdf")
        response = self.client.post(reverse("lead_upload", args=[self.lead.pk]), {"file": upload})
        self.assertRedirects(response, reverse("lead_detail", args=[self.lead.pk]), fetch_redirect_response=False)
        args, kwargs = self.fake_s3.upload_fileobj.call_args
        self.assertEqual(args[1:], ("my-bucket", "docs/engineer/acme/My_Resume.pdf"))
        self.assertEqual(kwargs["ExtraArgs"], {"ContentType": "application/pdf"})

    def test_upload_failure_shows_message(self):
        self.fake_s3.upload_fileobj.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
        self.fake_s3.list_objects_v2.return_value = {}
        upload = SimpleUploadedFile("resume.pdf", b"%PDF-1.4")
        response = self.client.post(reverse("lead_upload", args=[self.lead.pk]), {"file": upload}, follow=True)
        self.assertContains(response, "Upload failed")

    def test_file_pages_require_staff(self):
        self.client.logout()
        for url in (reverse("lead_detail", args=[self.lead.pk]), reverse("lead_file", args=[self.lead.pk])):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.post(reverse("lead_upload", args=[self.lead.pk])).status_code, 302)
        self.fake_s3.upload_fileobj.assert_not_called()
