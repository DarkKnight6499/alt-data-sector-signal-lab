"""Monthly backtest with dated inputs, drift-aware trades and an equal-weight benchmark."""

from dataclasses import asdict

import numpy as np
import pandas as pd

from .attribution import brinson_fachler
from .config import (ACTIVE, ALLOCATION, BENCH_RETURN, BENCH_WEIGHT, DECISION, GROUP,
                     INTERACTION, PERIOD, PORT_RETURN, RETURN, SCORE, SELECTION,
                     TICKER, VOL, WEIGHT, ResearchConfig)
from .portfolio import risk_aware_weights
from .signals import FEATURE_AVAILABLE, FEATURE_PERIOD, features_asof

# Config: output schema and metric conventions.
GROSS = "gross_return"
NET = "net_return"
COST = "transaction_cost"
TRADED = "traded_notional"
TURNOVER = "one_way_turnover"
IC = "rank_ic"
GROSS_NAV = "gross_nav"
NET_NAV = "net_nav"
BENCH_NAV = "benchmark_nav"
DRAWDOWN = "net_drawdown"
ATTRIBUTION_RESIDUAL = "attribution_residual"


def trade_statistics(target: pd.Series, drifted: pd.Series, cost_bps: float):
    if set(target.index) != set(drifted.index) or not np.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("Invalid trade alignment or cost")
    risky_trades = (target - drifted.reindex(target.index)).abs().sum()
    cash_change = abs((1 - target.sum()) - (1 - drifted.sum()))
    return {TRADED: risky_trades, TURNOVER: .5 * (risky_trades + cash_change),
            COST: risky_trades * cost_bps / 10000}


def maximum_drawdown(returns: pd.Series) -> float:
    if returns.empty or not np.isfinite(returns).all() or (returns < -1).any():
        raise ValueError("Invalid drawdown returns")
    nav = (1 + returns).cumprod()
    peak = nav.cummax().clip(lower=1.)
    return float((nav / peak - 1).min())


def information_coefficient(scores: pd.Series, realized: pd.Series) -> float:
    if (scores.index.has_duplicates or realized.index.has_duplicates
            or set(scores.index) != set(realized.index)
            or not np.isfinite(scores).all() or not np.isfinite(realized).all()):
        raise ValueError("IC requires finite aligned cross sections")
    if scores.nunique() <= 1 or realized.nunique() <= 1:
        return np.nan
    return float(scores.rank(method="average").corr(realized.rank(method="average")))


def summarize(monthly: pd.DataFrame, config: ResearchConfig) -> dict:
    active = monthly[NET] - monthly[BENCH_RETURN]
    tracking_error = active.std(ddof=1)
    n = len(monthly)
    return {"data_kind": "synthetic", "periods": n,
            "gross_total_return": float((1 + monthly[GROSS]).prod() - 1),
            "net_total_return": float((1 + monthly[NET]).prod() - 1),
            "benchmark_total_return": float((1 + monthly[BENCH_RETURN]).prod() - 1),
            "net_annualized_return": float((1 + monthly[NET]).prod() ** (config.periods_per_year / n) - 1),
            "annualized_tracking_error": float(tracking_error * np.sqrt(config.periods_per_year)),
            "information_ratio": float(active.mean() / tracking_error * np.sqrt(config.periods_per_year))
            if tracking_error > 0 else None,
            "mean_rank_ic": float(monthly[IC].mean()) if monthly[IC].notna().any() else None,
            "rank_ic_periods": int(monthly[IC].notna().sum()),
            "active_hit_rate": float((active > 0).mean()),
            "maximum_drawdown": maximum_drawdown(monthly[NET]),
            "mean_one_way_turnover": float(monthly[TURNOVER].mean()),
            "total_cost_return_points": float(monthly[COST].sum()),
            "max_attribution_residual": float(monthly[ATTRIBUTION_RESIDUAL].abs().max()),
            "assumptions": asdict(config)}


def run_backtest(universe: pd.DataFrame, returns: pd.DataFrame,
                 observations: pd.DataFrame, config=ResearchConfig()):
    if universe.empty or universe[TICKER].duplicated().any() or universe[[TICKER, GROUP]].isna().any().any():
        raise ValueError("Invalid universe")
    if (not np.isfinite([config.cost_bps, config.volatility_floor, config.signal_tilt]).all()
            or config.cost_bps < 0 or config.volatility_window < 2 or config.periods_per_year < 1):
        raise ValueError("Invalid research controls")
    if returns.duplicated([PERIOD, TICKER]).any():
        raise ValueError("Duplicate return key")
    tickers = sorted(universe[TICKER].tolist())
    if set(returns[TICKER]) != set(tickers):
        raise ValueError("Return universe mismatch")
    panel = returns.pivot(index=PERIOD, columns=TICKER, values=RETURN).sort_index().reindex(columns=tickers)
    if panel.empty or not np.isfinite(panel.to_numpy()).all() or (panel <= -1).any().any():
        raise ValueError("Require complete finite returns greater than -100%")
    panel.index = pd.to_datetime(panel.index)
    if not (panel.index == panel.index + pd.offsets.MonthEnd(0)).all():
        raise ValueError("Returns must use month-end dates")
    if len(panel) != len(pd.date_range(panel.index.min(), panel.index.max(), freq="ME")):
        raise ValueError("Missing return month")
    if len(panel) <= config.volatility_window:
        raise ValueError("Insufficient return history")
    benchmark_weights = pd.Series(1 / len(tickers), index=tickers)
    drifted = pd.Series(0., index=tickers)
    groups = universe.set_index(TICKER)[GROUP].reindex(tickers)
    monthly_rows, weight_rows, attribution_rows = [], [], []
    for date in panel.index[config.volatility_window:]:
        cutoff = date - pd.offsets.MonthEnd(1) + pd.Timedelta(hours=23, minutes=59, seconds=59)
        features = features_asof(observations, cutoff, tickers)
        history = panel.loc[panel.index <= cutoff].tail(config.volatility_window)
        if len(history) != config.volatility_window or history.index.max() > cutoff:
            raise ValueError("Invalid volatility history cutoff")
        volatility = history.std(ddof=1)
        weights = risk_aware_weights(features[SCORE], volatility, config.name_cap,
                                    config.signal_tilt, config.volatility_floor)
        realized = panel.loc[date]
        trade = trade_statistics(weights, drifted, config.cost_bps)
        gross = float(weights.dot(realized))
        net = gross - trade[COST]
        if net <= -1:
            raise ValueError("Costs exhaust portfolio NAV")
        benchmark = float(benchmark_weights.dot(realized))
        scores = features[SCORE]
        rank_ic = information_coefficient(scores, realized)
        group_rows = []
        for group in sorted(groups.unique()):
            names = groups.index[groups == group]
            portfolio_group_weight = weights.loc[names].sum()
            benchmark_group_weight = benchmark_weights.loc[names].sum()
            group_rows.append({GROUP: group, WEIGHT: portfolio_group_weight,
                               BENCH_WEIGHT: benchmark_group_weight,
                               PORT_RETURN: weights.loc[names].dot(realized.loc[names]) / portfolio_group_weight,
                               BENCH_RETURN: benchmark_weights.loc[names].dot(realized.loc[names]) / benchmark_group_weight})
        attribution = brinson_fachler(pd.DataFrame(group_rows))
        attribution[PERIOD] = date
        attribution_rows.extend(attribution.to_dict("records"))
        residual = attribution[[ALLOCATION, SELECTION, INTERACTION]].sum().sum() - (gross - benchmark)
        monthly_rows.append({PERIOD: date, DECISION: cutoff, GROSS: gross, NET: net,
                             BENCH_RETURN: benchmark, ACTIVE: net - benchmark, IC: rank_ic,
                             ATTRIBUTION_RESIDUAL: residual, **trade})
        for ticker in tickers:
            weight_rows.append({PERIOD: date, DECISION: cutoff, TICKER: ticker, GROUP: groups[ticker],
                                WEIGHT: weights[ticker], BENCH_WEIGHT: benchmark_weights[ticker],
                                SCORE: scores[ticker], VOL: volatility[ticker], RETURN: realized[ticker],
                                FEATURE_AVAILABLE: features.loc[ticker, FEATURE_AVAILABLE],
                                FEATURE_PERIOD: features.loc[ticker, FEATURE_PERIOD],
                                "volatility_last_period": history.index.max()})
        drifted = weights * (1 + realized) / (1 + gross)
    monthly = pd.DataFrame(monthly_rows)
    monthly[GROSS_NAV] = (1 + monthly[GROSS]).cumprod()
    monthly[NET_NAV] = (1 + monthly[NET]).cumprod()
    monthly[BENCH_NAV] = (1 + monthly[BENCH_RETURN]).cumprod()
    monthly[DRAWDOWN] = monthly[NET_NAV] / monthly[NET_NAV].cummax().clip(lower=1) - 1
    return monthly, pd.DataFrame(weight_rows), pd.DataFrame(attribution_rows), summarize(monthly, config)
