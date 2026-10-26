import logging

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from . import s3

logger = logging.getLogger(__name__)


class Document(models.Model):
    """A file stored in the private S3 bucket that visitors can download."""

    title = models.CharField(max_length=200)
    s3_key = models.CharField(
        max_length=500,
        help_text="Object key in the S3 bucket, e.g. 'docs/welcome.pdf'",
    )
    filename = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name the visitor's browser saves it as (optional)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active documents are offered on the home page",
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    @property
    def download_name(self):
        return self.filename or self.s3_key.rsplit("/", 1)[-1]

    @property
    def file_type(self):
        """Extension after the last '.' in the key's file name, e.g. 'pdf'."""
        name = self.s3_key.rsplit("/", 1)[-1]
        return name.rsplit(".", 1)[-1].lower() if "." in name else ""


class JobLead(models.Model):
    """A job opening being tracked on the private dashboard."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        INTERESTED = "interested", "Interested"
        APPLIED = "applied", "Applied"
        INTERVIEWING = "interviewing", "Interviewing"
        REJECTED = "rejected", "Rejected"
        IGNORED = "ignored", "Not interested"

    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    is_remote = models.BooleanField(default=False)
    expected_compensation = models.CharField(
        max_length=100,
        blank=True,
        help_text="Free text, e.g. '$140k-160k + equity'",
    )
    min_salary = models.PositiveIntegerField(null=True, blank=True, help_text="Annual, in dollars; used for sorting")
    max_salary = models.PositiveIntegerField(null=True, blank=True, help_text="Annual, in dollars; used for sorting")
    summary = models.TextField(blank=True)
    application_link = models.URLField(max_length=1000, blank=True)
    source = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where the lead came from, e.g. 'LinkedIn' or 'referral from Sam'",
    )
    custom_resume = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 folder for this lead's tailored resume, e.g. 'docs/senior-software-engineer/acme/'. "
                  "Set automatically when the lead is created.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    applied = models.BooleanField(default=False, help_text="Applied leads are hidden on the dashboard by default")
    external_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="ID from the job API this lead was imported from; empty for manual entries",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.title} at {self.company}" if self.company else self.title

    def save(self, *args, **kwargs):
        new_folder = not self.custom_resume
        if new_folder:
            self.custom_resume = self.resume_folder()
        super().save(*args, **kwargs)
        if new_folder:
            create_s3_folder(self.custom_resume)

    def resume_folder(self):
        """e.g. 'docs/senior-software-engineer/acme/'; slugs keep the S3 key URL-safe."""
        title = slugify(self.title)[:100].strip("-") or "untitled"
        company = slugify(self.company)[:100].strip("-") or "unknown-company"
        return f"{settings.JOB_RESUME_PREFIX}{title}/{company}/"


def create_s3_folder(prefix):
    """Create an empty 'folder' object so the prefix shows up in the S3 console, ready for uploads.

    Failures are logged rather than raised so a missing permission never blocks saving a lead.
    """
    if not settings.AWS_S3_BUCKET:
        return
    try:
        s3.create_folder(prefix)
    except (BotoCoreError, ClientError):
        logger.exception("Could not create S3 folder %s", prefix)


class JobSearch(models.Model):
    """A saved search that `manage.py fetch_jobs` runs against each job API."""

    query = models.CharField(max_length=200, help_text="e.g. 'senior software engineer'")
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="City or region, e.g. 'Seattle, WA'; leave blank for anywhere in the US",
    )
    remote_only = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "job searches"

    def __str__(self):
        where = "remote" if self.remote_only else (self.location or "anywhere")
        return f"{self.query} ({where})"
