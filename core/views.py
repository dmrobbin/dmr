import boto3
from botocore.config import Config
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render

from .models import Document


def current_document():
    return Document.objects.filter(is_active=True).first()


def home(request):
    return render(request, "core/home.html", {"document": current_document()})


def download(request):
    """Redirect to a short-lived presigned S3 URL so the bucket can stay private."""
    document = current_document()
    if document is None or not settings.AWS_S3_BUCKET:
        raise Http404("No document available")

    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )
    url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": document.s3_key,
            "ResponseContentDisposition": f'attachment; filename="{document.download_name}"',
        },
        ExpiresIn=settings.DOWNLOAD_LINK_SECONDS,
    )
    return redirect(url)
