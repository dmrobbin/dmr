import boto3
from botocore.config import Config
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .models import Document


def active_documents():
    return Document.objects.filter(is_active=True)


def home(request):
    return render(request, "core/home.html", {"documents": active_documents()})


def download(request, pk):
    """Redirect to a short-lived presigned S3 URL so the bucket can stay private."""
    document = get_object_or_404(active_documents(), pk=pk)
    if not settings.AWS_S3_BUCKET:
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
