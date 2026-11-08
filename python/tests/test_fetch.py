import importlib.util
import unittest

from altdata_lab.config import ROOT

# Config: import the optional script directly; tests use local payloads only.
FETCH_PATH = ROOT / "python" / "scripts" / "fetch_public.py"
SPEC = importlib.util.spec_from_file_location("fetch_public", FETCH_PATH)
FETCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FETCH)
RETRIEVAL = "2025-02-01T00:00:00+00:00"
TEST_URL = "https://example.invalid/local-fixture"


class FetchNormalizationTests(unittest.TestCase):
    def test_postings_deduplicate_jobs_and_ignore_prospects(self):
        payload = {"jobs": [{"id": 1, "internal_job_id": 9}, {"id": 2, "internal_job_id": 9},
                             {"id": 3, "internal_job_id": 10}, {"id": 4, "internal_job_id": None}]}
        self.assertEqual(FETCH.count_current_jobs(payload), 2)

    def test_facts_keep_vintage_and_retrieval_availability(self):
        payload = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"val": 100, "end": "2020-12-31", "filed": "2021-02-01", "accn": "old"},
            {"val": 101, "end": "2020-12-31", "filed": "2022-02-01", "accn": "revision"}]}}}}}
        rows = FETCH.normalize_companyfacts(payload, "TEST", RETRIEVAL, TEST_URL, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual({row[FETCH.AVAILABLE] for row in rows}, {RETRIEVAL})
        self.assertEqual({row["val"] for row in rows}, {100, 101})

    def test_pageviews_month_end_and_incomplete_month(self):
        rows = FETCH.normalize_pageviews({"items": [{"timestamp": "2024020100", "views": 42},
                                                    {"timestamp": "2025020100", "views": 10}]},
                                         "TEST", RETRIEVAL, TEST_URL)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][FETCH.PERIOD], "2024-02-29")
        self.assertEqual(rows[0][FETCH.METRIC], "wikipedia_page_views")

    def test_missing_payload_is_not_zero(self):
        with self.assertRaises(ValueError):
            FETCH.count_current_jobs({})
        with self.assertRaises(ValueError):
            FETCH.normalize_pageviews({"items": []}, "TEST", RETRIEVAL, TEST_URL)

    def test_filing_text_suppresses_scripts(self):
        parser = FETCH.FilingText()
        parser.feed("<p>Revenue</p><script>bad data</script><p>100</p>")
        self.assertEqual(parser.text(), "Revenue\n100")


if __name__ == "__main__":
    unittest.main()
