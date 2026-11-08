# Limitations

## Synthetic

- All names, subsectors, job counts, web indices, financials, excerpts, returns and benchmark inputs are seeded or authored examples.
- The data generator imposes a weak latent relationship between proxies and returns. Performance is conditional on that assumption.
- Recorded LLM fixtures are authored examples, not real model responses. They demonstrate the adapter and validation path only.
- Results on synthetic data are not evidence of alpha.

## Stylized

- The parser accepts a narrow reported-value grammar. It cannot reliably parse arbitrary filings, tables, comparative columns, negation, mixed fiscal calendars or multilingual transcripts.
- Exact evidence matching checks a substring; it does not prove economic meaning, detect prompt injection or establish semantic entailment. Real LLM integration needs stronger grounding, schema enforcement, adversarial tests and human-reviewed labels.
- The financial controls share the synthetic generator with the excerpts. This tests consistency checks, not an independent audit or accounting compliance.
- Publication lags, monthly execution and stale-data limits are assumed. Daily timing, overnight news and execution delays are unresolved at monthly frequency.
- Fixed membership excludes delistings, corporate actions, sector reclassifications and survivorship effects. Total returns are generated directly.
- Risk-aware weights use diagonal trailing volatility, not covariance, factor risk, liquidity or a forecast error model. Caps do not ensure diversification across correlated names.
- Costs are linear return deductions on buys and sells. The benchmark is costless. Market impact, taxes, financing, spread dynamics and implementability are omitted.
- Attribution is arithmetic per month. No linked multi-period attribution, benchmark constituent changes, FX decomposition or cash attribution is provided.
- No parameter tuning, confidence intervals, multiple-testing adjustment, regime validation or out-of-sample claim is made.

## Unverified and unrun

- Live public fetches have not run. SEC, Greenhouse and Wikimedia documentation access does not establish payload availability or coverage.
- Wikimedia's legacy endpoint, real CIK/board/article mappings and real historical vintages remain unverified.
- Public snapshots are not a ready-made backtest panel. Current job boards have no reconstructed historical counts. Current facts may include later revisions. Retrieval-time availability is intentionally conservative.
- A real industrial total-return benchmark and historical membership have not been sourced.
- Native Microsoft Excel opening and recalculation were not tested. Live formulas, formula-engine perturbations and exported cached values were tested.
- Regulatory and accounting compliance is outside scope. Only the narrow MD&A and KPI contextual statements listed in source_verification.md were checked. No accounting recognition or regulatory limits are implemented.
