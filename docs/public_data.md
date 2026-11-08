# Optional public snapshots

The offline library never fetches data. Run python/scripts/fetch_public.py separately on a machine with network access. It writes raw responses, normalized CSVs and a timestamped manifest under data/public/. That directory is gitignored and separate from the synthetic snapshot.

Copy data/public_fetch_config.example.json to a local configuration file. Add an entities list with objects containing ticker and any of cik, greenhouse_board and wikipedia_article. Use identifiers checked against primary sources. Do not map fictional IND tickers to real companies. An empty configuration intentionally exits before any network request.

Set PUBLIC_DATA_USER_AGENT to a descriptive project name and contact email. The value is sent to services and is not stored in the manifest. Call:

```powershell
python python/scripts/fetch_public.py path/to/local_config.json
```

The script fetches SEC companyfacts, submissions and the latest recent 10-K or 10-Q primary document for each configured CIK. It preserves taxonomy, tag, unit, duration, filing date and accession. An empty sec_tags list keeps all facts. To filter, specify fully qualified names such as us-gaap:Revenues only after checking issuer usage. Financial tags and durations are not automatically interchangeable across issuers. Extracted plain text covers the entire filing and requires reviewed section selection. The demo's narrow parser is not a general EDGAR parser.

Greenhouse counts distinct non-null internal_job_id values in the current board response, excluding prospect posts. Store repeated snapshots to build history. updated_at is not treated as original posting time. Historical job counts cannot be reconstructed from today's board.

Wikimedia monthly per-article page views are a public attention series. They are not corporate website visits or demand. Article mappings, redirects, bot filters, API availability and endpoint behavior require a live check. Incomplete current months are excluded. The legacy REST route remains unverified in this build; a failed endpoint is reported in the manifest.

Requests are serial, spaced at least one second apart, with bounded retries for transient errors. A permanent HTTP error stops retries for that request. Raw success, normalization failures, HTTP errors, byte counts, retrieval time and file hashes are retained. A failure produces no fabricated count or price. The script does not fetch benchmark prices or historical index membership.

Current SEC companyfacts and historical web counts can reflect later revisions. The conservative normalized available_at equals retrieval time, including for old periods. Do not backdate it to manufacture an investable history. The fetched files are not automatically accepted by the synthetic pipeline. Real research needs reviewed identity mappings, units, document evidence, vintage handling, point-in-time membership, total returns and an independently sourced benchmark before constructing a real panel.

Live fetch script status: written, local normalization tests run, no external data downloaded. See source_verification.md for primary-source URLs and verification limits.
