import boto3
from botocore.config import Config
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .models import Document, JobLead

# The document shown inline at the top of the home page.
FEATURED_DOCUMENT_ID = 1


def active_documents():
    return Document.objects.filter(is_active=True)


def home(request):
    return render(request, "core/home.html", {
        "featured": active_documents().filter(pk=FEATURED_DOCUMENT_ID).first(),
        "documents": active_documents(),
    })


def presigned_redirect(pk, disposition):
    """Redirect to a short-lived presigned S3 URL so the bucket can stay private."""
    document = get_object_or_404(active_documents(), pk=pk)
    if not settings.AWS_S3_BUCKET:
        raise Http404("No document available")

    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )
    params = {
        "Bucket": settings.AWS_S3_BUCKET,
        "Key": document.s3_key,
        "ResponseContentDisposition": f'{disposition}; filename="{document.download_name}"',
    }
    if document.file_type == "pdf":
        # Make sure browsers render it rather than download it, whatever S3 has stored.
        params["ResponseContentType"] = "application/pdf"
    url = s3.generate_presigned_url(
        "get_object", Params=params, ExpiresIn=settings.DOWNLOAD_LINK_SECONDS
    )
    return redirect(url)


def download(request, pk):
    return presigned_redirect(pk, "attachment")


@xframe_options_sameorigin
def view_document(request, pk):
    """Open the document in the browser instead of downloading it (used by the home page embed)."""
    return presigned_redirect(pk, "inline")


@staff_member_required
def dashboard(request):
    """Private job-search dashboard; anyone not logged in as staff is sent to the admin login."""
    return render(request, "core/dashboard.html", {"job_leads": JobLead.objects.all()})
