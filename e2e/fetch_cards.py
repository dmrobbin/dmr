"""Fetch the corpus CPUs' cards into the scratch database, in batches. Images aren't copied: no S3 bucket is set here, so
the cards keep their text and no picture (the placeholders). Run with DJANGO_SQLITE_PATH pointing at the scratch file."""
import os
import pathlib
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import django  # noqa: E402

django.setup()
from django.core.management import call_command  # noqa: E402
from django.conf import settings  # noqa: E402

assert not settings.AWS_S3_BUCKET, "AWS_S3_BUCKET is set: refusing to fetch, since images would be uploaded"
assert "scratch" in str(settings.DATABASES["default"]["NAME"]), "not the scratch database"
serials = [line for line in (pathlib.Path(__file__).parent / "scratch" / "serials.txt").read_text(encoding="utf-8").splitlines() if line]
for start in range(0, len(serials), 100):
    batch = serials[start:start + 100]
    print(f"batch {start // 100 + 1}: {len(batch)} cards", flush=True)
    call_command("fetch_cards", card=batch, skip_existing=True, delay=1.0)
print("done", flush=True)
