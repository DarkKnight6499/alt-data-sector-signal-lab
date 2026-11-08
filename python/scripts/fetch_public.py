"""Optional live snapshots. This script is never imported by the offline library."""

import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# Config: edit the JSON mapping, not the fetch implementation. No secrets are persisted.
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "data" / "public_fetch_config.example.json"
OUTPUT_ROOT = ROOT / "data" / "public"
USER_AGENT_ENV = "PUBLIC_DATA_USER_AGENT"
TIMEOUT_SECONDS = 45
DELAY_SECONDS = 1.0
MAX_ATTEMPTS = 3
RETRY_STATUSES = {429, 500, 502, 503, 504}
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
GREENHOUSE_JOBS = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
WIKIMEDIA_VIEWS = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
                   "en.wikipedia.org/all-access/user/{article}/monthly/{start}/{end}")
TICKER = "ticker"
CIK = "cik"
BOARD = "greenhouse_board"
ARTICLE = "wikipedia_article"
PERIOD = "period_end"
AVAILABLE = "available_at"
RETRIEVED = "retrieved_at"
METRIC = "metric"
VALUE = "value"
SOURCE_URL = "source_url"
INTERNAL_JOB_ID = "internal_job_id"
ROWS_KEY = "records"
PUBLIC_JOB_METRIC = "current_open_jobs"
PUBLIC_WEB_METRIC = "wikipedia_page_views"
ALLOWED_FORMS = {"10-K", "10-Q"}
FACT_COLUMNS = [TICKER, "taxonomy", "tag", "unit", "start", "end", "val", "filed", "accn", "form", "fy", "fp", "frame", AVAILABLE, SOURCE_URL]
COUNT_COLUMNS = [TICKER, PERIOD, AVAILABLE, METRIC, VALUE, SOURCE_URL]
SAFE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
SAFE_DOCUMENT = re.compile(r"^[A-Za-z0-9_.-]+$")


class FilingText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "div", "tr", "br", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data + " ")

    def text(self):
        return "\n".join(" ".join(line.split()) for line in "".join(self.parts).splitlines() if line.strip())


def normalize_companyfacts(payload, ticker, retrieved, source_url, tags):
    rows = []
    for taxonomy, concepts in payload.get("facts", {}).items():
        for tag, concept in concepts.items():
            if tags and f"{taxonomy}:{tag}" not in tags:
                continue
            for unit, facts in concept.get("units", {}).items():
                for fact in facts:
                    rows.append({TICKER: ticker, "taxonomy": taxonomy, "tag": tag, "unit": unit,
                                 **{key: fact.get(key) for key in ("start", "end", "val", "filed", "accn", "form", "fy", "fp", "frame")},
                                 AVAILABLE: retrieved, SOURCE_URL: source_url})
    return rows


def count_current_jobs(payload):
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("Greenhouse payload lacks jobs list")
    return len({job[INTERNAL_JOB_ID] for job in jobs if job.get(INTERNAL_JOB_ID) is not None})


def normalize_pageviews(payload, ticker, retrieved, source_url):
    if not isinstance(payload.get("items"), list) or not payload["items"]:
        raise ValueError("Wikimedia payload has no monthly items")
    rows = []
    for item in payload["items"]:
        start = datetime.strptime(item["timestamp"][:8], "%Y%m%d")
        next_month = start.replace(year=start.year + (start.month == 12), month=start.month % 12 + 1, day=1)
        period = (next_month - timedelta(days=1)).date().isoformat()
        if next_month.replace(tzinfo=timezone.utc) > datetime.fromisoformat(retrieved.replace("Z", "+00:00")):
            continue
        value = item["views"]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("Invalid pageview count")
        rows.append({TICKER: ticker, PERIOD: period, AVAILABLE: retrieved,
                     METRIC: PUBLIC_WEB_METRIC, VALUE: value, SOURCE_URL: source_url})
    return rows


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class Fetcher:
    def __init__(self, output, user_agent):
        self.output = output
        self.user_agent = user_agent
        self.entries = []

    def fetch(self, url, stem, json_payload=True):
        entry = {SOURCE_URL: url, RETRIEVED: datetime.now(timezone.utc).isoformat(),
                 "status": "failed", "attempts": 0}
        self.entries.append(entry)
        for attempt in range(MAX_ATTEMPTS):
            entry["attempts"] += 1
            time.sleep(DELAY_SECONDS * (2 ** attempt))
            try:
                request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json" if json_payload else "text/html"})
                with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    raw = response.read()
                    entry["http_status"] = response.status
                    entry["final_url"] = response.geturl()
                path = self.output / (stem + (".json" if json_payload else ".html"))
                path.write_bytes(raw)
                entry.update({"status": "success", "path": path.name,
                              "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
                entry.pop("error", None)
                payload = json.loads(raw) if json_payload else raw.decode("utf-8", errors="replace")
                return payload, entry
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
                entry["status"] = "failed"
                entry["error"] = str(error)
                if isinstance(error, HTTPError):
                    entry["http_status"] = error.code
                    if error.code not in RETRY_STATUSES:
                        break
                elif isinstance(error, ValueError):
                    break
        return None, entry


def fetch_entity(entity, settings, fetcher):
    ticker = entity[TICKER]
    if not SAFE_NAME.fullmatch(ticker):
        raise ValueError("Ticker must be a safe identifier")
    if entity.get(CIK):
        cik = str(entity[CIK]).zfill(10)
        if len(cik) != 10 or not cik.isdigit():
            raise ValueError("CIK must contain at most 10 digits")
        url = SEC_FACTS.format(cik=cik)
        facts, entry = fetcher.fetch(url, f"{ticker}_companyfacts")
        if facts is not None:
            rows = normalize_companyfacts(facts, ticker, entry[RETRIEVED], url, settings.get("sec_tags", []))
            write_csv(fetcher.output / f"{ticker}_facts.csv", rows, FACT_COLUMNS)
            entry[ROWS_KEY] = len(rows)
        submissions, entry = fetcher.fetch(SEC_SUBMISSIONS.format(cik=cik), f"{ticker}_submissions")
        if submissions is not None:
            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            candidates = [index for index, form in enumerate(forms) if form in ALLOWED_FORMS]
            if not candidates:
                entry["normalization_error"] = "No 10-K or 10-Q in recent submissions"
            else:
                index = candidates[0]
                accession = recent["accessionNumber"][index].replace("-", "")
                document = recent["primaryDocument"][index]
                if not accession.isdigit() or not SAFE_DOCUMENT.fullmatch(document):
                    raise ValueError("Unsafe archive document path")
                url = SEC_ARCHIVE.format(cik=int(cik), accession=accession, document=document)
                html, entry = fetcher.fetch(url, f"{ticker}_{accession}", json_payload=False)
                if html is not None:
                    parser = FilingText()
                    parser.feed(html)
                    (fetcher.output / f"{ticker}_{accession}.txt").write_text(parser.text(), encoding="utf-8")
                    entry.update({"form": forms[index], "accession": accession,
                                  "filing_date": recent["filingDate"][index], "section": "Entire primary filing; MD&A selection requires review"})
    if entity.get(BOARD):
        board = entity[BOARD]
        if not SAFE_NAME.fullmatch(board):
            raise ValueError("Invalid Greenhouse board token")
        url = GREENHOUSE_JOBS.format(board=board)
        jobs, entry = fetcher.fetch(url, f"{ticker}_jobs")
        if jobs is not None:
            row = {TICKER: ticker, PERIOD: entry[RETRIEVED][:10], AVAILABLE: entry[RETRIEVED],
                   METRIC: PUBLIC_JOB_METRIC, VALUE: count_current_jobs(jobs), SOURCE_URL: url}
            write_csv(fetcher.output / f"{ticker}_jobs.csv", [row], COUNT_COLUMNS)
            entry[ROWS_KEY] = 1
    if entity.get(ARTICLE):
        url = WIKIMEDIA_VIEWS.format(article=quote(entity[ARTICLE], safe=""),
                                     start=settings["web_start"], end=settings["web_end"])
        views, entry = fetcher.fetch(url, f"{ticker}_pageviews")
        if views is not None:
            rows = normalize_pageviews(views, ticker, entry[RETRIEVED], url)
            write_csv(fetcher.output / f"{ticker}_pageviews.csv", rows, COUNT_COLUMNS)
            entry[ROWS_KEY] = len(rows)


def main(config_path=DEFAULT_CONFIG):
    settings = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if not settings.get("entities"):
        raise SystemExit("No entities configured. Add verified CIK, board and article mappings first.")
    user_agent = os.environ.get(USER_AGENT_ENV, "")
    if "@" not in user_agent:
        raise SystemExit(f"Set {USER_AGENT_ENV} to a descriptive project name and contact email.")
    tickers = [entity[TICKER] for entity in settings["entities"]]
    if len(set(tickers)) != len(tickers):
        raise SystemExit("Duplicate ticker mappings")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = OUTPUT_ROOT / stamp
    output.mkdir(parents=True, exist_ok=False)
    fetcher = Fetcher(output, user_agent)
    manifest = {"synthetic": False, "retrieved_at": stamp, "config": settings,
                "availability_policy": "Retrieval time, never backdated for historical research", "requests": fetcher.entries}
    try:
        for entity in settings["entities"]:
            try:
                fetch_entity(entity, settings, fetcher)
            except (ValueError, KeyError, TypeError, OSError) as error:
                fetcher.entries.append({TICKER: entity.get(TICKER), "status": "normalization_failed", "error": str(error)})
    finally:
        manifest["files"] = {path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
                             for path in sorted(output.iterdir()) if path.is_file()}
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    failures = sum(entry["status"] != "success" or "normalization_error" in entry for entry in fetcher.entries)
    print(f"Snapshot: {output}. Failures: {failures}.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG))
