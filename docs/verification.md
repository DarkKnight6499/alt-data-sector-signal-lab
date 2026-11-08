# Verification record

Date: 2026-11-08.

| Check | Result |
| --- | --- |
| Required bundled Python runtime, with the specified reference library path | 38 unit tests passed |
| Dependencies used by Python | NumPy, pandas and standard library; no packages installed |
| Seeded snapshot regeneration | File hashes reproduce; pipeline checks data and fixture hashes |
| Offline pipeline | 48 monthly holding periods; execution with sockets disabled passed |
| Extraction controls | 924 accepted, 26 rejected, 10 missing; recorded adapter has 9 accepted and 3 rejected |
| Information timing | Exact availability boundary, future-value mutation, late filings and current-return mutation tests passed |
| Hand calculations | Brinson effects, inverse volatility, caps, drift, costs, drawdown and rank IC passed |
| Formula workbook | 144 group effects and 48 monthly reconciliations match Python within 0.0000000001 return units |
| Workbook behavior | Return-input perturbation propagated through live formulas; original input restored |
| Workbook layout | All three sheet previews reviewed; no clipped important values found |
| Formula errors | Zero matches; saved formula caches have no Excel error cells |
| Author and calculation | Author metadata set; automatic recalculation enabled |
| Public fetcher | Local normalization fixtures and empty-config guard ran; no live requests ran |
| Primary-source text | eCFR MD&A and SEC KPI guidance reached; exact scope in source_verification.md |

Known untested behavior: live fetch success, real point-in-time data assembly, real performance, a real LLM and native Microsoft Excel recalculation. Synthetic results provide no evidence of alpha.

The first availability-boundary test exposed mixed date/timestamp parsing. Explicit mixed-format parsing fixed it. Reported-control unit checks prevent USD controls from silently validating USD-million extractions. Greenhouse fixtures distinguish repeated posts from distinct jobs and exclude prospect posts. Wikimedia fixtures test leap-year month ends and exclude incomplete months.
