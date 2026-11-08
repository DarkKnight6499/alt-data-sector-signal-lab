"""As-of features using only observations available by the decision cutoff."""

import numpy as np
import pandas as pd

from .config import (AVAILABLE, FEATURES, JOBS, JOBS_GROWTH, MAX_AGE_DAYS, METRIC,
                     OPERATING_MARGIN, PERIOD, SCORE, TICKER, VALUE, WEB, WEB_GROWTH)

# Config: exact long-panel keys; revisions require a separate vintage-aware importer.
OBSERVATION_KEYS = [TICKER, PERIOD, METRIC]
GROWTH_FEATURES = {JOBS: JOBS_GROWTH, WEB: WEB_GROWTH}
FEATURE_AVAILABLE = "latest_feature_available_at"
FEATURE_PERIOD = "latest_feature_period_end"


def validate_observations(observations: pd.DataFrame):
    required = [TICKER, PERIOD, AVAILABLE, METRIC, VALUE]
    if not set(required).issubset(observations.columns) or observations.empty:
        raise ValueError("Missing observation schema or empty panel")
    if observations.loc[:, required].isna().any().any():
        raise ValueError("Missing observation fields")
    if observations.duplicated(OBSERVATION_KEYS).any():
        raise ValueError("Duplicate observation key")
    if not np.isfinite(observations[VALUE].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite observation")
    periods = pd.to_datetime(observations[PERIOD], errors="raise", format="mixed")
    available = pd.to_datetime(observations[AVAILABLE], errors="raise", format="mixed")
    if (available < periods).any():
        raise ValueError("Observation available before period end")


def features_asof(observations: pd.DataFrame, cutoff, tickers) -> pd.DataFrame:
    validate_observations(observations)
    cutoff = pd.Timestamp(cutoff)
    eligible = observations.loc[pd.to_datetime(observations[AVAILABLE], format="mixed") <= cutoff].copy()
    rows = []
    for ticker in tickers:
        row = {TICKER: ticker}
        latest_dates, latest_periods = [], []
        for metric in (*GROWTH_FEATURES, OPERATING_MARGIN):
            history = eligible.loc[(eligible[TICKER] == ticker) & (eligible[METRIC] == metric)]
            history = history.sort_values(PERIOD)
            if history.empty:
                raise ValueError(f"Missing as-of {metric} for {ticker}")
            latest = history.tail(1).to_dict("records")[0]
            if (cutoff - pd.Timestamp(latest[PERIOD])).days > MAX_AGE_DAYS[metric]:
                raise ValueError(f"Stale {metric} for {ticker}")
            latest_dates.append(pd.Timestamp(latest[AVAILABLE]))
            latest_periods.append(pd.Timestamp(latest[PERIOD]))
            if metric in GROWTH_FEATURES:
                if len(history) < 2:
                    raise ValueError(f"Insufficient growth history for {ticker}")
                earlier = history.tail(2).head(1).to_dict("records")[0]
                # Growth needs consecutive monthly observations to retain its meaning.
                if pd.Period(latest[PERIOD], freq="M") - pd.Period(earlier[PERIOD], freq="M") != pd.offsets.MonthEnd(1):
                    raise ValueError(f"Nonconsecutive growth periods for {ticker}")
                if earlier[VALUE] <= 0 or latest[VALUE] < 0:
                    raise ValueError("Growth requires a positive denominator and nonnegative numerator")
                row[GROWTH_FEATURES[metric]] = latest[VALUE] / earlier[VALUE] - 1
            else:
                row[metric] = latest[VALUE]
        row[FEATURE_AVAILABLE] = max(latest_dates)
        row[FEATURE_PERIOD] = max(latest_periods)
        rows.append(row)
    result = pd.DataFrame(rows).set_index(TICKER)
    ranks = result.loc[:, FEATURES].rank(method="average", pct=True)
    result[SCORE] = (2 * ranks - 1).mean(axis=1)
    return result
