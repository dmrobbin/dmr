"""The CPU creation page's Import tab: new CPUs' files (as the new-cpu skill writes them) checked and imported from the
browser, and the export they're written from, as a zip. The same as export_cpu_corpus and import_cpu, without a shell
on the server."""
import io
import json
import random
import zipfile

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .card_images import series_title
from .cpu_corpus import export_corpus, import_cpus, import_world_pack
from .cpu_views import back_to, home_context, staff_required
from .models import Card

MAX_FILES = 40  # in one batch
MAX_FILE_BYTES = 256 * 1024  # a CPU's file is a few kilobytes


@staff_required
def corpus_download(request):
    """export_cpu_corpus's folder as a zip, to unzip over corpus/ where new CPUs are written."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, text in export_corpus().items():
            archive.writestr(path, text)
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="corpus.zip"'
    return response


def uploaded_files(request):
    """([(file name, text)], error). A check reads the files chosen; the import after it, the texts the check
    showed, carried in the form, so what's imported is exactly what was checked."""
    if request.POST.get("step") == "import":
        return list(zip(request.POST.getlist("name"), request.POST.getlist("text"))), None
    uploads = request.FILES.getlist("files")
    if not uploads:
        return [], "Choose the CPU files to check."
    if len(uploads) > MAX_FILES:
        return [], f"At most {MAX_FILES} files at a time."
    found = []
    for upload in uploads:
        if upload.size > MAX_FILE_BYTES:
            return [], f"{upload.name} is too big to be a CPU's file."
        found.append((upload.name, upload.read().decode("utf-8-sig", errors="replace")))
    return found, None


def show_title(result):
    """The show a CPU's deck is from, for shortlist_renders --show; "" if it has no deck."""
    series = (result.data.get("deck") or {}).get("series")
    expansion = Card.objects.filter(serial_number__startswith=f"{series}/").values_list("expansion", flat=True).first() if series else None
    return series_title(expansion) if expansion else ""


@staff_required
@require_POST
def cpu_import(request):
    """Check a batch of CPU files (a dry run: nothing saved) or, from the check's page, import it."""
    files, error = uploaded_files(request)
    if error:
        messages.error(request, error)
        return back_to("import")
    batch, unreadable = [], []
    for name, text in files:
        try:
            data = json.loads(text)
        except ValueError as exc:
            unreadable.append(f"{name}: not JSON ({exc}).")
            continue
        if not isinstance(data, dict):
            unreadable.append(f"{name}: not a CPU's file.")
            continue
        batch.append({"name": name, "text": text, "data": data})
    if unreadable:
        messages.error(request, " ".join(unreadable))
        return back_to("import")
    importing = request.POST.get("step") == "import"
    try:
        seed = int(request.POST.get("seed", ""))
    except ValueError:
        seed = random.randrange(1_000_000)  # chosen by the check, and carried to the import: the same decks
    results = import_cpus([entry["data"] for entry in batch], request.user, seed=seed, dry_run=not importing)
    ready = not any(result.problems for result in results)
    for entry, result in zip(batch, results):
        entry["result"] = result
        entry["deck_size"] = sum(copies for _, copies in result.cards)
        entry["show"] = show_title(result)
    shows = {}  # {show: [file names]}: a shortlist_renders command for each show, once they're imported
    for entry in batch:
        shows.setdefault(entry["show"], []).append(entry["name"])
    if importing and ready:
        messages.success(request, f"Imported {len(batch)} CPU{'s' if len(batch) != 1 else ''}. "
                                  "None is finalized yet: give each its pictures, play its scenes, then finalize it.")
    return render(request, "weiss/cpu_home.html", {**home_context("import"), "batch": batch, "seed": seed,
                                                   "ready": ready, "imported": importing and ready,
                                                   "shortlists": sorted(shows.items())})


MAX_PACK_BYTES = 2 * 1024 * 1024  # a world pack holds many CPUs' chatter and scenes


@staff_required
@require_POST
def world_pack_import(request):
    """Check world pack files (corpus/world/, the CPUs' part in world mode) or import them: the import checks first and
    saves only if nothing's wrong. CPUs are found by name; ones that aren't here are skipped and listed."""
    uploads = request.FILES.getlist("packs")
    if not uploads:
        messages.error(request, "Choose the world pack files.")
        return back_to("import")
    files, unreadable = [], []
    for upload in uploads[:MAX_FILES]:
        if upload.size > MAX_PACK_BYTES:
            unreadable.append(f"{upload.name} is too big for a world pack.")
            continue
        try:
            data = json.loads(upload.read().decode("utf-8-sig", errors="replace"))
        except ValueError as exc:
            unreadable.append(f"{upload.name}: not JSON ({exc}).")
            continue
        if not isinstance(data, dict) or not isinstance(data.get("cpus", []), list):
            unreadable.append(f"{upload.name}: not a world pack.")
            continue
        files.append((upload.name, data))
    if unreadable:
        messages.error(request, " ".join(unreadable))
        return back_to("import")
    importing = request.POST.get("step") == "import"
    results = import_world_pack([data for _, data in files], dry_run=not importing, user=request.user)
    ready = not any(result.problems for result in results)
    if importing and ready:
        made = sum(len(result.done) for result in results)
        messages.success(request, f"Gave {made} CPU{'s' if made != 1 else ''} their world mode haunts, chatter and scenes.")
    return render(request, "weiss/cpu_home.html", {**home_context("import"), "pack": list(zip([name for name, _ in files], results)),
                                                   "pack_ready": ready, "pack_imported": importing and ready})
