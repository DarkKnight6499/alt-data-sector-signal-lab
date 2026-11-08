"""Long-only inverse-volatility tilt with proportional capping."""

import numpy as np
import pandas as pd

from .config import FLOAT_TOL

# Config: numerical limit for bounded proportional redistribution.
MAX_ITERATIONS = 1000
EXPONENT_LIMIT = 20


def capped_weights(raw: pd.Series, cap: float) -> pd.Series:
    if raw.empty or raw.index.has_duplicates or not np.isfinite(raw).all() or (raw <= 0).any():
        raise ValueError("Require unique names and finite positive raw weights")
    if not np.isfinite(cap) or cap <= 0 or cap > 1 or len(raw) * cap < 1 - FLOAT_TOL:
        raise ValueError("Infeasible name cap")
    weights = pd.Series(0.0, index=raw.index)
    free = pd.Series(True, index=raw.index)
    for _ in range(MAX_ITERATIONS):
        remaining = 1 - weights.loc[~free].sum()
        proposal = raw.loc[free] / raw.loc[free].sum() * remaining
        over = proposal > cap + FLOAT_TOL
        if not over.any():
            weights.loc[free] = proposal
            return weights
        weights.loc[proposal.index[over]] = cap
        free.loc[proposal.index[over]] = False
        if not free.any():
            if abs(weights.sum() - 1) <= FLOAT_TOL:
                return weights
            break
    raise ArithmeticError("Capping failed to converge")


def risk_aware_weights(scores: pd.Series, volatility: pd.Series, cap: float,
                       tilt: float, floor: float) -> pd.Series:
    if (scores.index.has_duplicates or set(scores.index) != set(volatility.index)
            or not np.isfinite(scores).all() or not np.isfinite(volatility).all()
            or (volatility < 0).any() or not np.isfinite([tilt, floor]).all() or floor <= 0):
        raise ValueError("Invalid aligned scores, volatility or risk controls")
    raw = np.exp((tilt * scores).clip(-EXPONENT_LIMIT, EXPONENT_LIMIT)) / volatility.reindex(scores.index).clip(lower=floor)
    return capped_weights(raw, cap)
