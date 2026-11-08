# Formula attribution workbook

attribution.xlsx contains 48 monthly reconciliations, 144 group calculations and the two-group hand example. All inputs are synthetic. Results on synthetic data are not evidence of alpha.

Groups contains editable portfolio and benchmark group weights and returns. Allocation, selection, interaction, contribution totals and total benchmark return use live formulas. Attribution sums each month's effects, subtracts Python's transaction-cost input and compares gross and net active returns with independent Python outputs. Weight-difference columns compare each month's weight sums with one. Hand check calculates 0.8% allocation, 0.5% selection and 0.3% interaction, totaling 1.6% active return.

Percentages are stored as decimal numbers. Dates are numeric Excel dates. Differences show return units, not basis points. No multi-period linking is performed. Costs are imported Python inputs, not recalculated trading costs. Changing weights or returns recalculates the attribution; the Python comparison columns stay fixed until the workbook is rebuilt. This deliberately exposes differences after edits.

Rebuild after running the offline Python pipeline:

1. Run python/scripts/prepare_workbook.py with the project Python path configured.
2. Make @oai/artifact-tool available to Node and run node excel/build_workbook.mjs from the project root. In the bundled Windows environment, run a temporary copy under .work with a node_modules junction to the bundled dependencies.
3. Run python/scripts/finalize_workbook.py to set the author metadata and automatic recalculation.
4. Run the full Python unit suite. Remove the .work directory and the export's optional inspect sidecar after reviewing previews.

Verification: artifact-tool recalculation, every group effect against Python, every monthly reconciliation, the hand example, a return-input perturbation, zero formula-error matches and visual review of all three sheets. The saved OOXML caches and formulas are also checked by Python tests. Native Microsoft Excel open/recalculate behavior has not been tested.
