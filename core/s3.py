"""Thin wrappers around the private S3 bucket that holds documents and resumes."""
import boto3
from botocore.config import Config
from django.conf import settings


def client():
    return boto3.client("s3", region_name=settings.AWS_REGION, config=Config(signature_version="s3v4"))


def presigned_url(key, disposition, filename, content_type=None):
    """A short-lived link to one object, so the bucket can stay private."""
    params = {
        "Bucket": settings.AWS_S3_BUCKET,
        "Key": key,
        "ResponseContentDisposition": f'{disposition}; filename="{filename}"',
    }
    if content_type:
        params["ResponseContentType"] = content_type
    return client().generate_presigned_url("get_object", Params=params, ExpiresIn=settings.DOWNLOAD_LINK_SECONDS)


def list_files(prefix):
    """Files directly inside a 'folder' prefix, newest first, as dicts with name, key, size and modified."""
    response = client().list_objects_v2(Bucket=settings.AWS_S3_BUCKET, Prefix=prefix, Delimiter="/")
    files = [
        {"name": obj["Key"][len(prefix):], "key": obj["Key"], "size": obj["Size"], "modified": obj["LastModified"]}
        for obj in response.get("Contents", [])
        if obj["Key"] != prefix  # skip the empty folder marker itself
    ]
    return sorted(files, key=lambda f: f["modified"], reverse=True)


def upload(key, fileobj, content_type=""):
    extra = {"ContentType": content_type} if content_type else {}
    client().upload_fileobj(fileobj, settings.AWS_S3_BUCKET, key, ExtraArgs=extra)


def create_folder(prefix):
    """An empty object named like the prefix makes the 'folder' show up in the S3 console."""
    client().put_object(Bucket=settings.AWS_S3_BUCKET, Key=prefix, Body=b"")
