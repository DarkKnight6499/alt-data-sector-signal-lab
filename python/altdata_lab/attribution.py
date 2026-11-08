"""Single-period arithmetic Brinson-Fachler attribution with interaction separate."""

import numpy as np
import pandas as pd

from .config import (ACTIVE, ALLOCATION, BENCH_RETURN, BENCH_WEIGHT, FLOAT_TOL,
                     GROUP, INTERACTION, PORT_RETURN, SELECTION, WEIGHT)

# Config: fully invested long-only attribution schema.
NUMERIC_COLUMNS = [WEIGHT, BENCH_WEIGHT, PORT_RETURN, BENCH_RETURN]
EFFECT_COLUMNS = [ALLOCATION, SELECTION, INTERACTION]


def brinson_fachler(groups: pd.DataFrame) -> pd.DataFrame:
    if groups.empty or groups[GROUP].duplicated().any():
        raise ValueError("Require one row per nonempty group")
    numeric = groups.loc[:, NUMERIC_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("Attribution inputs must be finite")
    for column in (WEIGHT, BENCH_WEIGHT):
        if (groups[column] < 0).any() or not np.isclose(groups[column].sum(), 1, atol=FLOAT_TOL, rtol=0):
            raise ValueError("Weights must be nonnegative and sum to one")
    result = groups.copy()
    benchmark = (result[BENCH_WEIGHT] * result[BENCH_RETURN]).sum()
    difference = result[WEIGHT] - result[BENCH_WEIGHT]
    result[ALLOCATION] = difference * (result[BENCH_RETURN] - benchmark)
    result[SELECTION] = result[BENCH_WEIGHT] * (result[PORT_RETURN] - result[BENCH_RETURN])
    result[INTERACTION] = difference * (result[PORT_RETURN] - result[BENCH_RETURN])
    result[ACTIVE] = result[WEIGHT] * result[PORT_RETURN] - result[BENCH_WEIGHT] * result[BENCH_RETURN]
    residual = result[EFFECT_COLUMNS].sum().sum() - result[ACTIVE].sum()
    if abs(residual) > FLOAT_TOL:
        raise ArithmeticError("Attribution does not reconcile")
    return result
