from django.conf import settings
from django.core.management.base import BaseCommand

from core.job_sources import JobSourceError, JSearch, SerpApi
from core.models import JobLead, JobSearch

# Titles containing any of these are below the mid/senior level being targeted.
EXCLUDED_TITLE_WORDS = ["junior", "jr.", "jr ", "intern", "new grad", "entry level", "entry-level", "graduate"]


class Command(BaseCommand):
    help = "Pull job listings for each active JobSearch from the job APIs into JobLead."

    def add_arguments(self, parser):
        parser.add_argument("--query", help="Run this one search instead of the saved JobSearch rows")
        parser.add_argument("--location", default="")
        parser.add_argument("--remote", action="store_true", help="Remote jobs only (with --query)")
        parser.add_argument("--posted", default="week", choices=["today", "3days", "week", "month", "all"],
                            help="How recent listings must be (JSearch only)")
        parser.add_argument("--pages", type=int, default=1, help="Result pages per search; each costs API quota")
        parser.add_argument("--source", choices=["jsearch", "serpapi"], help="Only use this API")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be added without saving")

    def handle(self, *args, **options):
        sources = self.sources(options["source"])
        if not sources:
            self.stderr.write("No job API keys are configured (JSEARCH_API_KEY / SERPAPI_API_KEY).")
            return

        if options["query"]:
            searches = [JobSearch(query=options["query"], location=options["location"], remote_only=options["remote"])]
        else:
            searches = list(JobSearch.objects.filter(is_active=True))
            if not searches:
                self.stderr.write("No active job searches; add one in the admin or pass --query.")
                return

        self.seen = set()  # jobs handled this run, so --dry-run dedupes like a real run
        total_added = 0
        for search in searches:
            for source in sources:
                try:
                    jobs = source.search(search.query, search.location, search.remote_only,
                                         options["posted"], options["pages"])
                except JobSourceError as exc:
                    self.stderr.write(self.style.ERROR(f"{source.name} / {search}: {exc}"))
                    continue
                added = [job for job in jobs if self.keep(job) and self.save(job, options["dry_run"])]
                total_added += len(added)
                self.stdout.write(f"{source.name} / {search}: {len(jobs)} found, {len(added)} new")
                for job in added:
                    self.stdout.write(f"  + {job['title']} at {job['company']} ({job['expected_compensation'] or 'pay not listed'})")

        verb = "would add" if options["dry_run"] else "added"
        self.stdout.write(self.style.SUCCESS(f"Done: {verb} {total_added} job leads."))

    def sources(self, only):
        available = {
            "jsearch": (settings.JSEARCH_API_KEY, JSearch),
            "serpapi": (settings.SERPAPI_API_KEY, SerpApi),
        }
        return [cls(key) for name, (key, cls) in available.items() if key and only in (None, name)]

    def keep(self, job):
        title = f"{job['title'].lower()} "
        if any(word in title for word in EXCLUDED_TITLE_WORDS):
            return False
        # Listings without pay info are kept; most employers leave it off.
        best_pay = job["max_salary"] or job["min_salary"]
        return not best_pay or best_pay >= settings.JOB_MIN_SALARY

    def save(self, job, dry_run):
        """Store the job unless it's already saved, from any source. Returns whether it's new."""
        keys = {job["external_id"], (job["title"].lower(), job["company"].lower())}
        if keys & self.seen:
            return False
        self.seen |= keys
        if JobLead.objects.filter(external_id=job["external_id"]).exists():
            return False
        if JobLead.objects.filter(title__iexact=job["title"], company__iexact=job["company"]).exists():
            return False
        if not dry_run:
            fields = job | {"application_link": job["application_link"][:1000]}
            for pay in ("min_salary", "max_salary"):
                fields[pay] = round(job[pay]) if job[pay] else None
            JobLead.objects.create(**fields)
        return True
