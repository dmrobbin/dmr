from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Document


class HomeTests(TestCase):
    def test_home_without_document_shows_message_and_no_button(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No document is available")
        self.assertNotContains(response, reverse("download"))

    def test_home_with_document_shows_button(self):
        Document.objects.create(title="Guide", s3_key="docs/guide.pdf")
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("download"))
        self.assertContains(response, "Guide")


class DownloadTests(TestCase):
    def test_download_404_without_document(self):
        self.assertEqual(self.client.get(reverse("download")).status_code, 404)

    @override_settings(AWS_S3_BUCKET="my-bucket")
    def test_download_redirects_to_presigned_url(self):
        Document.objects.create(title="Guide", s3_key="docs/guide.pdf")
        fake_s3 = MagicMock()
        fake_s3.generate_presigned_url.return_value = "https://example.com/signed"
        with patch("core.views.boto3.client", return_value=fake_s3):
            response = self.client.get(reverse("download"))
        self.assertRedirects(response, "https://example.com/signed", fetch_redirect_response=False)
        kwargs = fake_s3.generate_presigned_url.call_args.kwargs
        self.assertEqual(kwargs["Params"]["Bucket"], "my-bucket")
        self.assertEqual(kwargs["Params"]["Key"], "docs/guide.pdf")

    def test_inactive_document_is_not_offered(self):
        Document.objects.create(title="Old", s3_key="old.pdf", is_active=False)
        self.assertEqual(self.client.get(reverse("download")).status_code, 404)
