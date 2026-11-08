# Methodology

## Dataset and extraction

All shipped observations, returns, reported financial controls, excerpts and recorded-response fixtures are synthetic. Seed 1729 produces 12 fictional industrial names in three illustrative subsectors, January 2020 through December 2024. Quarterly excerpts alternate MD&A and earnings-call labels. These are authored examples, not transcripts. The recorded adapter replays three authored JSON responses, including intentional errors. No model or API generated these responses.

The generator imposes a small relationship between a latent state, proxies and next-month returns. That relationship is an assumption. Results on synthetic data are not evidence of alpha.

The rule extractor accepts whole reported-value lines for revenue, operating income, backlog and operating margin. It normalizes billion amounts to USD millions and percentages to ratios. It ignores prose outside its grammar, including forward guidance. It supports signed decimals and comma-separated amounts. It does not infer fiscal periods or resolve arbitrary tables.

Candidate validation matches issuer, period, metric, unit and exact evidence substring against synthetic financial controls. Margin is independently recomputed as operating income divided by revenue. Tolerance is the larger of an absolute tolerance and 0.000001 times the control's absolute value. Absolute tolerances are 0.0001 USD million and 0.000001 for ratios. These are project choices. Missing metrics, duplicates, unit errors, period errors, ungrounded evidence, late controls and value mismatches are reported separately. Only accepted rule-derived margins enter the backtest. Rejected margins leave the previous accepted vintage in use until it becomes stale. Recorded-adapter outputs are evaluated separately and never enter portfolio weights.

## Information clock

Dates and timestamps are timezone-naive UTC by convention. Monthly proxies describe a calendar month and become available 7 days later for jobs and 10 days later for web traffic. Quarterly filings and their financial controls become available 45 days after period end. These lags are synthetic assumptions, not observed reporting delays.

At the last second of the preceding calendar month, the strategy selects only rows with available_at at or before that decision. It holds target weights over the following monthly total return. This assumes execution at the next month boundary without an additional execution delay. Monthly returns cannot resolve overnight release or execution timing.

Job and web features are changes between the last two available consecutive monthly observations. Margin is the latest accepted available quarterly margin. Jobs and web observations older than 75 days, or margin older than 250 days from period end, abort the run. The margin limit allows one rejected quarterly observation without immediate termination. Missing features, missing returns, duplicate keys, future-dated availability errors and gaps fail explicitly. No backfill from future data is used. The fixed synthetic universe is known throughout; it is not a reconstruction of historical index membership.

Each feature is ranked across the 12 names using average ranks divided by name count, transformed as 2 times percentile rank minus 1. Score is the mean of the three ranks. No future normalization or fitted model is used. Rank IC is the monthly Pearson correlation of average signal ranks and realized return ranks, equivalent to Spearman correlation. Undefined IC is excluded and its valid count is reported.

## Weights, benchmark and costs

Raw weight equals exp(0.8 times score) divided by monthly return volatility. Volatility uses the 12 monthly returns ending before the holding month, with a 0.01 floor. The long-only proportional redistribution algorithm caps each name at 15% and sums weights to one. This is a diagonal volatility heuristic; it does not optimize a covariance matrix or control factor exposures. Parameters are fixed, not selected using simulated performance.

The sector benchmark rebalances monthly to equal weights across the same 12 synthetic names. It is a synthetic sector benchmark, not a public index or ETF. It bears no transaction costs. Portfolio trades are measured from previous gross-return-drifted holdings. Initial holdings are cash. Traded notional sums absolute risky-asset buys and sells; cost is 10 basis points per dollar traded. One-way turnover is half of risky traded notional plus absolute cash change, so initial deployment has turnover 1 and traded notional 1. Later fully invested rebalances have traded notional twice one-way turnover.

Net monthly return equals gross return less cost. Costs are a month-end return deduction, with pro rata funding and no impact on relative next-period risky holdings. This is an approximation, not a self-financing execution simulation. No spreads, liquidity constraints, taxes, impact, financing, cash yield or borrow fees are modeled.

NAV compounds monthly returns. Drawdown includes initial NAV 1. Active hit rate is the fraction of months net portfolio return strictly exceeds benchmark return; ties are misses. Tracking error is sample standard deviation of monthly net active returns times sqrt(12). Information ratio uses monthly arithmetic active mean divided by that standard deviation, times sqrt(12). Annualized portfolio return is geometric. Total cost return points are summed monthly deductions, not the compounded gross/net NAV difference. No statistical significance or real-world validation is claimed.

## Attribution convention

Attribution is arithmetic, single-period, gross of portfolio costs. For group g, portfolio weight wP, benchmark weight wB, portfolio group return rP, benchmark group return rB and total benchmark return RB:

- Allocation = (wP - wB) times (rB - RB).
- Selection = wB times (rP - rB).
- Interaction = (wP - wB) times (rP - rB).

Group weights use beginning-of-period name weights. Group returns are the corresponding within-group weighted returns. Fully invested group weights make the sum of the three effects equal gross portfolio return less benchmark return. Subtract the month's portfolio cost to bridge to net active return. The CSV includes group contribution differences; an individual group's contribution difference need not equal that group's three effects because allocation is benchmark-centered.

No arithmetic sum across months is presented as compounded attribution. The workbook reconciles every month separately. Geometric linking of effects is outside scope.

Hand example: wP=(0.6,0.4), wB=(0.5,0.5), rP=(0.12,0.01), rB=(0.10,0.02). RB=0.06. Allocation=(0.004,0.004), selection=(0.010,-0.005), interaction=(0.002,0.001). Total active return is 0.016.
