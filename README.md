# alt-data-sector-signal-lab

Offline industrial signal research: extract KPIs from filing-style text, validate against financial controls, combine alternative-data proxies, construct capped weights, backtest against a sector benchmark and reconcile Brinson-Fachler attribution in Excel.

**All shipped data and recorded-response fixtures are synthetic. Results on synthetic data are not evidence of alpha.**

## Run

Requires Python 3.10+, NumPy and pandas 2.2+. No API keys, network connection or additional Python libraries are required. From the project root:

```powershell
$env:PYTHONPATH = "python"
python -m altdata_lab.pipeline
python -m unittest discover -s python/tests -v
```

The shipped snapshot is ready to use. To regenerate it deterministically:

```powershell
python python/scripts/generate_synthetic.py
python -m altdata_lab.pipeline
```

The pipeline verifies snapshot hashes before using data. It writes CSV tables, metrics and a run manifest to examples/output/. It does not rebuild Excel automatically; see [workbook instructions](excel/README.md).

## Contents

| Path | Purpose |
| --- | --- |
| python/altdata_lab/ | Offline extraction, validation, signals, weights, backtest and attribution |
| python/tests/ | Hand-computed cases, timestamp boundaries, future-data mutations, snapshot and workbook checks |
| python/tests/fixtures/ | Three authored synthetic LLM response examples with intentional errors |
| data/synthetic/ | Seed 1729 snapshot: 12 fictional firms, 60 months, 240 quarterly excerpts |
| python/scripts/fetch_public.py | Optional public-source fetcher; writes only to data/public/ |
| examples/output/ | Extraction reports, dated weights, returns, attribution, metrics and manifests |
| excel/attribution.xlsx | Live formulas for 48 monthly attribution reconciliations and a hand example |
| docs/ | Method, public-data integration boundary, source verification and limitations |

## Research design

- Signals: consecutive-month growth in synthetic job postings and web traffic, plus accepted filings-derived operating margin. Revenue, operating income and backlog are also extracted and checked.
- Information timing: publication dates precede use. Filing lag is 45 days; jobs lag is 7 days; web lag is 10 days. Rejected values never enter signals.
- Portfolio: long only, 15% name cap, inverse-volatility tilt with a 12-month trailing window. No covariance optimization.
- Benchmark: monthly equal weights across the same fictional industrial firms. This is a synthetic sector benchmark, not a public index.
- Evaluation: drift-aware turnover, 10 basis points per dollar traded, rank IC, active hit rate, tracking error, information ratio and drawdown.
- Attribution: single-period allocation, selection and separate interaction. Gross effects bridge to net active return by subtracting portfolio costs.

The default run covers January 2021 through December 2024 after a 12-month volatility warm-up. The extraction report contains 924 accepted, 26 rejected and 10 missing candidates. The recorded adapter separately accepts 9 candidates and rejects 3 intentional errors. It makes no API calls and is not an evaluation of a real LLM.

## Verification and limitations

Unit tests include a 1.6% hand-computed active return, capping redistribution, initial funding, drifted trades, both-side costs, drawdown from initial capital, exact release-time boundaries, future-data mutations and every exported workbook effect. The offline pipeline is tested with sockets disabled. Formula recalculation and input changes were checked with artifact-tool. Native Microsoft Excel recalculation was not tested.

The dataset imposes a small latent relationship between proxies and returns. Text grammar, publication lags, costs, risk controls and market structure are stylized. Public fetch code is supplied for a later network-enabled run; it does not turn current snapshots into historical point-in-time data. No real-world validation or statistical evidence of alpha is claimed. See [limitations](docs/limitations.md) and [methodology](docs/methodology.md).

MD&A context and KPI guidance were checked against eCFR and the SEC's original text. Public API documentation was opened; live data payloads were not fetched. The Wikimedia endpoint remains unverified. Full URLs, retrieval date, sections and unresolved checks appear in [source verification](docs/source_verification.md). Optional acquisition and real-data integration requirements appear in [public data](docs/public_data.md).
