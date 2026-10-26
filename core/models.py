from django.db import models


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
