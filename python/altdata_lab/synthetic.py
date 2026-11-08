"""Generate a reproducible synthetic snapshot and authored adapter fixtures."""

import hashlib
import json
from dataclasses import asdict

import numpy as np
import pandas as pd

from .config import (AVAILABLE, BACKLOG, COUNT_UNIT, DATA_DIR, DOC_ID, FIRMS_PER_GROUP,
                     FIXTURE_DIR, GROUP, INDEX_UNIT, JOBS, JOBS_LAG_DAYS, KIND, KPI_UNITS,
                     METRIC, MONEY_UNIT, MONTHS, OPERATING_INCOME, OPERATING_MARGIN,
                     PERIOD, RETURN, REVENUE, SEED, START, SUBSECTORS, SYNTHETIC,
                     TEXT, TEXT_DECIMALS, TICKER, UNIT, VALUE, WEB, WEB_LAG_DAYS,
                     FILING_LAG_DAYS)
from .extraction import RuleExtractor

# Config: synthetic data-generating process; no fitted parameters or public rows.
LATENT_PERSISTENCE = 0.65
LATENT_NOISE = 0.7
MARKET_MEAN = 0.004
MARKET_SIGMA = 0.025
GROUP_SIGMA = 0.012
NAME_SIGMA = 0.04
IMPOSED_RETURN_LOADING = 0.002
BASE_REVENUE = 450.0
REVENUE_STEP = 90.0
REVENUE_TREND = 0.002
REVENUE_LATENT = 0.03
BASE_MARGIN = 0.12
MARGIN_LATENT = 0.015
BASE_BACKLOG_MULTIPLE = 2.0
BACKLOG_LATENT = 0.1
BASE_JOBS = 80
JOBS_STEP = 10
JOBS_LATENT = 0.15
JOBS_SIGMA = 0.05
WEB_BASE = 100.0
WEB_LATENT = 0.1
WEB_SIGMA = 0.05
QUARTER_MONTHS = (3, 6, 9, 12)
REVENUE_ERROR_EVERY = 17
MARGIN_ERROR_EVERY = 19
MISSING_BACKLOG_EVERY = 23
MANIFEST_FILE = "manifest.json"
REVENUE_ERROR_MULTIPLIER = 1.1
MARGIN_ERROR = 0.01
FIXTURE_DOCUMENTS = 3
FIXTURE_WRONG_PERIOD = "2019-12-31"
FIXTURE_SCALE_ERROR = 1000


def write_snapshot(data_dir=DATA_DIR, fixture_dir=FIXTURE_DIR, seed=SEED):
    random = np.random.default_rng(seed)
    dates = pd.date_range(START, periods=MONTHS, freq="ME")
    universe = [{TICKER: f"IND{group_number * FIRMS_PER_GROUP + name + 1:02d}",
                 GROUP: group, SYNTHETIC: True}
                for group_number, group in enumerate(SUBSECTORS)
                for name in range(FIRMS_PER_GROUP)]
    firms = pd.DataFrame(universe)
    latent = {row[TICKER]: 0. for row in universe}
    returns, observations, financials, documents = [], [], [], []
    for month_number, date in enumerate(dates):
        market = random.normal(MARKET_MEAN, MARKET_SIGMA)
        group_shock = {group: random.normal(0, GROUP_SIGMA) for group in SUBSECTORS}
        for firm_number, firm in enumerate(universe):
            ticker = firm[TICKER]
            prior_latent = latent[ticker]
            latent[ticker] = LATENT_PERSISTENCE * prior_latent + random.normal(0, LATENT_NOISE)
            state = latent[ticker]
            returns.append({TICKER: ticker, PERIOD: date.strftime("%Y-%m-%d"),
                            RETURN: market + group_shock[firm[GROUP]] +
                            IMPOSED_RETURN_LOADING * prior_latent + random.normal(0, NAME_SIGMA),
                            SYNTHETIC: True})
            jobs = max(1, round((BASE_JOBS + JOBS_STEP * firm_number) *
                               np.exp(JOBS_LATENT * state + random.normal(0, JOBS_SIGMA))))
            web = WEB_BASE * np.exp(WEB_LATENT * state + random.normal(0, WEB_SIGMA))
            for metric, value, lag, unit in ((JOBS, jobs, JOBS_LAG_DAYS, COUNT_UNIT),
                                            (WEB, web, WEB_LAG_DAYS, INDEX_UNIT)):
                observations.append({TICKER: ticker, PERIOD: date.strftime("%Y-%m-%d"),
                                     AVAILABLE: (date + pd.Timedelta(days=lag)).strftime("%Y-%m-%d"),
                                     METRIC: metric, VALUE: value, UNIT: unit, SYNTHETIC: True})
            if date.month not in QUARTER_MONTHS:
                continue
            revenue = round((BASE_REVENUE + REVENUE_STEP * firm_number) *
                            np.exp(REVENUE_TREND * month_number + REVENUE_LATENT * state), TEXT_DECIMALS)
            income = round(revenue * (BASE_MARGIN + MARGIN_LATENT * state), TEXT_DECIMALS)
            backlog = round(revenue * (BASE_BACKLOG_MULTIPLE + BACKLOG_LATENT * state), TEXT_DECIMALS)
            available = (date + pd.Timedelta(days=FILING_LAG_DAYS)).strftime("%Y-%m-%d")
            period = date.strftime("%Y-%m-%d")
            for metric, value in ((REVENUE, revenue), (OPERATING_INCOME, income), (BACKLOG, backlog)):
                financials.append({TICKER: ticker, PERIOD: period, AVAILABLE: available,
                                   METRIC: metric, VALUE: value, UNIT: MONEY_UNIT, SYNTHETIC: True})
            document_number = len(documents) + 1
            text_revenue = revenue * REVENUE_ERROR_MULTIPLIER if document_number % REVENUE_ERROR_EVERY == 0 else revenue
            margin = income / revenue
            text_margin = margin + MARGIN_ERROR if document_number % MARGIN_ERROR_EVERY == 0 else margin
            lines = [f"SYNTHETIC {ticker} quarterly operating discussion.",
                     f"Revenue was USD {text_revenue:.4f} million for period ended {period}.",
                     f"Operating income was USD {income:.4f} million for period ended {period}."]
            if document_number % MISSING_BACKLOG_EVERY:
                lines.append(f"Backlog was USD {backlog:.4f} million for period ended {period}.")
            lines.extend([f"Operating margin was {100 * text_margin:.4f}% for period ended {period}.",
                          "Backlog means unfilled orders in this synthetic example; cancellations remain possible.",
                          "Management uses backlog to plan capacity. Operating margin equals operating income divided by revenue.",
                          "Prior-year revenue and forward guidance are outside the parser grammar.",
                          "We expect revenue of USD 9999 million next year. This is guidance, not reported revenue."])
            documents.append({DOC_ID: f"{ticker}_{period}", TICKER: ticker, PERIOD: period,
                              AVAILABLE: available, KIND: "mda" if document_number % 2 else "earnings_call",
                              TEXT: "\n".join(lines), SYNTHETIC: True})
    data_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir.mkdir(parents=True, exist_ok=True)
    for filename, frame in (("universe.csv", firms), ("returns.csv", pd.DataFrame(returns)),
                            ("observations.csv", pd.DataFrame(observations)),
                            ("reported_financials.csv", pd.DataFrame(financials))):
        frame.to_csv(data_dir / filename, index=False, float_format="%.12g", lineterminator="\n")
    document_path = data_dir / "documents.jsonl"
    document_path.write_text("".join(json.dumps(doc, sort_keys=True) + "\n" for doc in documents), encoding="utf-8")
    fixtures = {}
    for number, doc in enumerate(documents[:FIXTURE_DOCUMENTS]):
        records = [asdict(item) for item in RuleExtractor().extract(doc[DOC_ID], doc[TEXT])]
        if number == 1:
            for record in records:
                if record[METRIC] == REVENUE:
                    record[VALUE] *= FIXTURE_SCALE_ERROR
        if number == 2:
            for record in records:
                if record[METRIC] == BACKLOG:
                    record[PERIOD] = FIXTURE_WRONG_PERIOD
                if record[METRIC] == OPERATING_MARGIN:
                    record["evidence"] = "This statement does not occur in the source."
        fixtures[doc[DOC_ID]] = records
    (fixture_dir / "recorded_responses.json").write_text(json.dumps(fixtures, indent=2) + "\n", encoding="utf-8")
    files = ["universe.csv", "returns.csv", "observations.csv", "reported_financials.csv", "documents.jsonl"]
    manifest = {"dataset": "seeded synthetic industrial panel", "seed": seed,
                "synthetic": True, "public_observations": 0, "start": dates.min().strftime("%Y-%m-%d"),
                "end": dates.max().strftime("%Y-%m-%d"), "generator": "python/altdata_lab/synthetic.py",
                "imposed_return_loading": IMPOSED_RETURN_LOADING,
                "recorded_fixture_sha256": hashlib.sha256((fixture_dir / "recorded_responses.json").read_bytes()).hexdigest(),
                "files": {name: {"sha256": hashlib.sha256((data_dir / name).read_bytes()).hexdigest()}
                          for name in files}}
    (data_dir / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
