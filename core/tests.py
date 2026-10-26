from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Document


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


class DownloadTests(TestCase):
    def test_download_404_for_missing_document(self):
        self.assertEqual(self.client.get(reverse("download", args=[999])).status_code, 404)

    @override_settings(AWS_S3_BUCKET="my-bucket")
    def test_download_redirects_to_presigned_url(self):
        Document.objects.create(title="Other", s3_key="docs/other.pdf")
        document = Document.objects.create(title="Guide", s3_key="docs/guide.pdf")
        fake_s3 = MagicMock()
        fake_s3.generate_presigned_url.return_value = "https://example.com/signed"
        with patch("core.views.boto3.client", return_value=fake_s3):
            response = self.client.get(reverse("download", args=[document.pk]))
        self.assertRedirects(response, "https://example.com/signed", fetch_redirect_response=False)
        kwargs = fake_s3.generate_presigned_url.call_args.kwargs
        self.assertEqual(kwargs["Params"]["Bucket"], "my-bucket")
        self.assertEqual(kwargs["Params"]["Key"], "docs/guide.pdf")

    def test_inactive_document_is_not_downloadable(self):
        document = Document.objects.create(title="Old", s3_key="old.pdf", is_active=False)
        self.assertEqual(self.client.get(reverse("download", args=[document.pk])).status_code, 404)
