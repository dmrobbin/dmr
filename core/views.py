from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import get_valid_filename
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from . import s3
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

    # For PDFs, make sure browsers render it rather than download it, whatever S3 has stored.
    content_type = "application/pdf" if document.file_type == "pdf" else None
    return redirect(s3.presigned_url(document.s3_key, disposition, document.download_name, content_type))


def download(request, pk):
    return presigned_redirect(pk, "attachment")


@xframe_options_sameorigin
def view_document(request, pk):
    """Open the document in the browser instead of downloading it (used by the home page embed)."""
    return presigned_redirect(pk, "inline")


# Dashboard columns that can be sorted: ?sort=<key> ascending, ?sort=-<key> descending.
SORT_FIELDS = {
    "title": F("title"),
    "company": F("company"),
    "location": F("location"),
    "pay": Coalesce("max_salary", "min_salary"),
    "source": F("source"),
    "status": F("status"),
    "added": F("created"),
}
SORTABLE_COLUMNS = [
    ("title", "Title"),
    ("company", "Company"),
    ("location", "Location"),
    ("pay", "Compensation"),
    ("source", "Source"),
    ("status", "Status"),
    ("added", "Added"),
]


@staff_member_required
def dashboard(request):
    """Private job-search dashboard; anyone not logged in as staff is sent to the admin login."""
    leads = JobLead.objects.all()
    title = request.GET.get("title", "").strip()
    company = request.GET.get("company", "").strip()
    has_pay = request.GET.get("has_pay") == "1"
    if title:
        leads = leads.filter(title__icontains=title)
    if company:
        leads = leads.filter(company__icontains=company)
    if has_pay:
        leads = leads.exclude(expected_compensation="")

    sort = request.GET.get("sort", "-added")
    key = sort.removeprefix("-")
    if key not in SORT_FIELDS:
        sort, key = "-added", "added"
    descending = sort.startswith("-")
    field = SORT_FIELDS[key]
    leads = leads.order_by(field.desc(nulls_last=True) if descending else field.asc(nulls_last=True), "-created")

    columns = [
        {
            "label": label,
            # Clicking the current column flips its direction; other columns start ascending,
            # except pay and date, where the biggest/newest first is more useful.
            "sort": (key if descending else f"-{key}") if key == col
            else (f"-{col}" if col in ("pay", "added") else col),
            "arrow": ("↓" if descending else "↑") if key == col else "",
        }
        for col, label in SORTABLE_COLUMNS
    ]
    return render(request, "core/dashboard.html", {
        "job_leads": leads,
        "columns": columns,
        "filters": {"title": title, "company": company, "has_pay": has_pay},
        "filtered": bool(title or company or has_pay),
    })


@staff_member_required
def lead_detail(request, pk):
    """One lead's full description plus the files in its S3 resume folder."""
    lead = get_object_or_404(JobLead, pk=pk)
    files, files_error = [], ""
    if not settings.AWS_S3_BUCKET:
        files_error = "S3 isn't configured here (AWS_S3_BUCKET is empty)."
    elif lead.custom_resume.endswith("/"):
        try:
            files = s3.list_files(lead.custom_resume)
        except (BotoCoreError, ClientError) as exc:
            files_error = f"Couldn't list files: {exc}"
    return render(request, "core/lead_detail.html", {"lead": lead, "files": files, "files_error": files_error})


@staff_member_required
def lead_file(request, pk):
    """Download one file from the lead's S3 folder through a presigned link."""
    lead = get_object_or_404(JobLead, pk=pk)
    name = request.GET.get("name", "")
    # Only plain file names inside this lead's folder; no paths into the rest of the bucket.
    if not settings.AWS_S3_BUCKET or not name or "/" in name or not lead.custom_resume.endswith("/"):
        raise Http404("No such file")
    return redirect(s3.presigned_url(lead.custom_resume + name, "attachment", name))


@staff_member_required
@require_POST
def lead_upload(request, pk):
    lead = get_object_or_404(JobLead, pk=pk)
    upload = request.FILES.get("file")
    if not upload:
        messages.error(request, "Choose a file to upload.")
    elif not settings.AWS_S3_BUCKET or not lead.custom_resume.endswith("/"):
        messages.error(request, "This lead has no S3 folder to upload to.")
    else:
        name = get_valid_filename(upload.name)
        try:
            s3.upload(lead.custom_resume + name, upload, upload.content_type or "")
        except (BotoCoreError, ClientError) as exc:
            messages.error(request, f"Upload failed: {exc}")
        else:
            messages.success(request, f"Uploaded {name}.")
    return redirect("lead_detail", pk=lead.pk)
