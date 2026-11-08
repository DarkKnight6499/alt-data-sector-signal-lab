# Source verification

Retrieval date: 2026-11-08. Original primary text was opened with the web tool. No public observations were downloaded into the shipped dataset. Shell fetch scripts have not been run against live services.

| Source | Document and section | Verified use | Status |
| --- | --- | --- | --- |
| [eCFR](https://www.ecfr.gov/current/title-17/chapter-II/part-229/subpart-229.300/section-229.303) | 17 CFR 229.303(a), (b)(2)(ii)-(iii); page displayed Title 17 current through 2026-11-05 | MD&A addresses material known events and uncertainties. Results discussion includes known trends affecting revenue or income and, where applicable, price and volume explanations. This is context for the synthetic text, not a compliance engine. | Verified from displayed rule text |
| [SEC guidance](https://www.sec.gov/files/rules/interp/2020/33-10751.pdf) | Releases 33-10751, 34-88094, FR-87, Section I, printed pages 4-5 | The Commission generally expects a metric definition and calculation, investor usefulness, and management use, depending on facts and circumstances. Material methodology changes merit consideration of additional disclosure. The extraction schema preserves definitions, periods, units and evidence as research controls. | Verified from original PDF text returned by the web tool |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Sections data.sec.gov/submissions and XBRL Data APIs, companyfacts | Submissions and companyfacts URLs, 10-digit CIKs, and entity-wide standard-taxonomy facts. The API does not cover every custom operational KPI. | Documentation reached; live payload fetch not tested |
| [Greenhouse](https://docs.greenhouse.io/job-board.html) | Authentication; Jobs, List jobs | Public GET board endpoint; response has jobs, id, internal_job_id, updated_at and meta.total. Distinct non-null internal_job_id counts jobs rather than duplicated job posts. Current snapshots cannot establish historical counts. | Documentation reached; live board fetch not tested |
| [Wikimedia](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html) | Page view analytics; Get number of page views for a page | Wikimedia page views are an attention proxy, not company website traffic. Documentation says data start 2015-07-01. | Documentation reached; dynamic endpoint schema still unverified |

No accounting recognition, regulatory capital, non-GAAP classification, or investment compliance rules are implemented. Numerical tolerances, publication lags, costs, weight caps and risk floors are illustrative project parameters, not regulatory thresholds.

## Not verified

- Any real employer board token, company CIK mapping or article-to-company mapping. The fetch configuration requires explicit mappings.
- The live Wikimedia legacy REST endpoint used by the fetch script. The documentation page was accessible, but its interactive endpoint details did not appear in the returned text. This route must be verified by the later fetch run.
- Live HTTP behavior, permissions, data coverage, publication latency or historical revisions for any service. Each fetch writes a success/failure manifest. Failure must not create replacement observations.
- Brinson-Fachler attribution is implemented as an explicitly documented arithmetic convention with algebraic and hand-computed tests. No external certification or real-world validation is claimed.

## Source lessons

SEC and eCFR text opened successfully. Greenhouse documentation redirects from developers.greenhouse.io to docs.greenhouse.io. Greenhouse distinguishes post id from internal_job_id. Wikimedia provides encyclopedia attention, not corporate web visits. No public fetch was attempted from the offline shell.
