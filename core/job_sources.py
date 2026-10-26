"""Clients for the job-search APIs that `manage.py fetch_jobs` pulls leads from.

Each source turns its API's results into plain dicts with the same keys, so the
command can filter and save them without knowing where they came from.
"""
import hashlib
import json
import re
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Multipliers that turn a pay rate into an annual salary.
ANNUAL = {"YEAR": 1, "MONTH": 12, "WEEK": 52, "DAY": 260, "HOUR": 2080}


class JobSourceError(Exception):
    pass


def get_json(url, params, headers=None):
    request = Request(f"{url}?{urlencode(params)}", headers=headers or {})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        raise JobSourceError(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise JobSourceError(str(exc.reason)) from exc


def short_id(source, raw_id):
    """API job ids can be hundreds of characters; store a fixed-length hash instead."""
    return f"{source}:{hashlib.sha1(raw_id.encode()).hexdigest()}"


def format_salary(low, high, period="YEAR"):
    def money(n):
        return f"${n / 1000:.0f}k" if n >= 1000 else f"${n:,.0f}"

    if not low and not high:
        return ""
    amount = f"{money(low)}–{money(high)}" if low and high and low != high else money(low or high)
    return amount if period == "YEAR" else f"{amount}/{period.lower()}"


def annual(amount, period):
    return amount * ANNUAL.get(period, 1) if amount else None


class JSearch:
    """Google for Jobs results (Indeed, LinkedIn, Glassdoor, company sites) via OpenWeb Ninja."""

    name = "JSearch"
    url = "https://api.openwebninja.com/jsearch/search"

    def __init__(self, api_key):
        self.api_key = api_key

    def search(self, query, location="", remote_only=False, posted="week", pages=1):
        params = {
            "query": f"{query} in {location}" if location else query,
            "page": 1,
            "num_pages": pages,
            "country": "us",
            "date_posted": posted,
        }
        if remote_only:
            params["work_from_home"] = "true"
        data = get_json(self.url, params, {"X-API-Key": self.api_key})
        return [self.parse(job) for job in data.get("data", [])]

    def parse(self, job):
        period = job.get("job_salary_period") or "YEAR"
        low, high = job.get("job_min_salary"), job.get("job_max_salary")
        posted = job.get("job_posted_at_datetime_utc")
        return {
            "external_id": short_id("jsearch", job["job_id"]),
            "title": job.get("job_title") or "",
            "company": job.get("employer_name") or "",
            "location": job.get("job_location") or "",
            "is_remote": bool(job.get("job_is_remote")),
            "expected_compensation": format_salary(low, high, period),
            "min_salary": annual(low, period),
            "max_salary": annual(high, period),
            "summary": job.get("job_description") or "",
            "application_link": job.get("job_apply_link") or "",
            "source": f"{job.get('job_publisher') or 'Unknown'} via JSearch",
            "posted_at": datetime.fromisoformat(posted.replace("Z", "+00:00")) if posted else None,
        }


class SerpApi:
    """Google Jobs results via SerpApi."""

    name = "SerpApi"
    url = "https://serpapi.com/search.json"
    # Matches pay like "120K–150K a year" or "$45–$60 an hour".
    salary_pattern = re.compile(
        r"\$?([\d,.]+)\s*(K)?\s*(?:[–-]\s*\$?([\d,.]+)\s*(K)?)?\s*(?:a|an|per)\s+(year|month|week|day|hour)",
        re.IGNORECASE,
    )

    def __init__(self, api_key):
        self.api_key = api_key

    def search(self, query, location="", remote_only=False, posted="week", pages=1):
        params = {
            "engine": "google_jobs",
            "q": query,
            # Without a location, Google sometimes returns nothing for broad remote queries.
            "location": location or "United States",
            "gl": "us",
            "hl": "en",
            "api_key": self.api_key,
        }
        if remote_only:
            params["ltype"] = 1
        jobs = []
        for _ in range(pages):
            data = get_json(self.url, params)
            if "error" in data and not data.get("jobs_results"):
                # SerpApi reports "no results" as an error too; only treat other errors as failures.
                if "hasn't returned any results" in data["error"]:
                    break
                raise JobSourceError(data["error"])
            jobs += [self.parse(job) for job in data.get("jobs_results", [])]
            next_token = data.get("serpapi_pagination", {}).get("next_page_token")
            if not next_token:
                break
            params["next_page_token"] = next_token
        return jobs

    def parse_salary(self, text):
        match = self.salary_pattern.search(text or "")
        if not match:
            return None, None, "YEAR"
        low_num, low_k, high_num, high_k, period = match.groups()

        def number(digits, k):
            value = float(digits.replace(",", ""))
            return value * 1000 if k or (high_k and not k) else value

        low = number(low_num, low_k)
        high = number(high_num, high_k) if high_num else None
        return low, high, period.upper()

    def parse(self, job):
        # Pay and remote status come as plain text in "extensions", e.g. ["125K–175K a year", "Work from home"];
        # "detected_extensions" holds them parsed but is often missing.
        detected = job.get("detected_extensions") or {}
        extensions = job.get("extensions") or []
        salary = detected.get("salary") or next((e for e in extensions if self.salary_pattern.search(e)), "")
        low, high, period = self.parse_salary(salary)
        apply_options = job.get("apply_options") or []
        return {
            "external_id": short_id("serpapi", job.get("job_id") or job.get("share_link") or job["title"]),
            "title": job.get("title") or "",
            "company": job.get("company_name") or "",
            "location": job.get("location") or "",
            "is_remote": bool(detected.get("work_from_home")) or "Work from home" in extensions,
            "expected_compensation": format_salary(low, high, period) or salary,
            "min_salary": annual(low, period),
            "max_salary": annual(high, period),
            "summary": job.get("description") or "",
            "application_link": apply_options[0]["link"] if apply_options else job.get("share_link") or "",
            "source": f"{(job.get('via') or 'Unknown').removeprefix('via ')} via SerpApi",
            # SerpApi only gives relative dates like "3 days ago", which aren't worth parsing.
            "posted_at": None,
        }
