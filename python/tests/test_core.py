import unittest

import numpy as np
import pandas as pd

from altdata_lab.attribution import brinson_fachler
from altdata_lab.config import *
from altdata_lab.extraction import Extraction, RecordedLLMAdapter, RuleExtractor, validate_extractions
from altdata_lab.portfolio import capped_weights, risk_aware_weights

# Config: hand-computed controls and a synthetic reported excerpt.
DOC = {DOC_ID: "hand", TICKER: "TEST", PERIOD: "2020-03-31", AVAILABLE: "2020-05-15",
       TEXT: "Revenue was USD 1.2 billion for period ended 2020-03-31.\n"
             "Operating income was USD -120 million for period ended 2020-03-31.\n"
             "Backlog was USD 2,000 million for period ended 2020-03-31.\n"
             "Operating margin was -10% for period ended 2020-03-31.\n"
             "We expect Revenue of USD 9 billion next year."}


def controls():
    return pd.DataFrame([{TICKER: DOC[TICKER], PERIOD: DOC[PERIOD],
                          AVAILABLE: DOC[AVAILABLE], METRIC: metric, VALUE: value, UNIT: MONEY_UNIT}
                         for metric, value in ((REVENUE, 1200), (OPERATING_INCOME, -120), (BACKLOG, 2000))])


class ExtractionTests(unittest.TestCase):
    def test_units_signs_and_guidance(self):
        values = {item.metric: item.value for item in RuleExtractor().extract("hand", DOC[TEXT])}
        self.assertEqual(values, {REVENUE: 1200, OPERATING_INCOME: -120,
                                  BACKLOG: 2000, OPERATING_MARGIN: -0.1})

    def test_reported_reconciliation(self):
        report = validate_extractions(DOC, RuleExtractor().extract("hand", DOC[TEXT]), controls(), "rule")
        self.assertTrue((report[STATUS] == ACCEPTED).all())

    def test_missing_duplicate_value_period_unit_evidence(self):
        first = RuleExtractor().extract("hand", DOC[TEXT])[0]
        cases = [(Extraction(REVENUE, 1300, MONEY_UNIT, DOC[PERIOD], first.evidence), "value_mismatch"),
                 (Extraction(REVENUE, 1200, MONEY_UNIT, "2019-03-31", first.evidence), "period_mismatch"),
                 (Extraction(REVENUE, 1200, RATIO_UNIT, DOC[PERIOD], first.evidence), "unit_mismatch"),
                 (Extraction(REVENUE, 1200, MONEY_UNIT, DOC[PERIOD], "invented"), "ungrounded_evidence")]
        for candidate, reason in cases:
            report = validate_extractions(DOC, [candidate], controls(), "recorded")
            self.assertEqual(report.loc[report[METRIC] == REVENUE, REASON].item(), reason)
            self.assertEqual((report[STATUS] == "missing").sum(), 3)
        report = validate_extractions(DOC, [first, first], controls(), "rule")
        self.assertTrue((report.loc[report[METRIC] == REVENUE, REASON] == "duplicate_metric").all())

    def test_control_unavailable(self):
        financials = controls()
        financials[AVAILABLE] = "2020-05-16"
        report = validate_extractions(DOC, RuleExtractor().extract("hand", DOC[TEXT]), financials, "rule")
        self.assertTrue((report[REASON] == "control_not_available").all())

    def test_llm_schema(self):
        for record in ({METRIC: REVENUE}, {METRIC: REVENUE, VALUE: True, UNIT: MONEY_UNIT,
                                          PERIOD: DOC[PERIOD], EVIDENCE: "x"}):
            with self.assertRaises(ValueError):
                RecordedLLMAdapter({"hand": [record]}).extract("hand", DOC[TEXT])

    def test_reported_control_units(self):
        financials = controls()
        financials.loc[financials[METRIC] == REVENUE, UNIT] = "USD"
        report = validate_extractions(DOC, RuleExtractor().extract("hand", DOC[TEXT]), financials, "rule")
        self.assertTrue((report.loc[report[METRIC].isin([REVENUE, OPERATING_MARGIN]), REASON] == "reported_unit_mismatch").all())

    def test_wrong_issuer_cannot_validate(self):
        financials = controls()
        financials[TICKER] = "OTHER"
        report = validate_extractions(DOC, RuleExtractor().extract("hand", DOC[TEXT]), financials, "rule")
        self.assertTrue((report[REASON] == "missing_reported_control").all())

    def test_duplicate_reported_controls_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_extractions(DOC, [], pd.concat([controls(), controls()]), "rule")


class AttributionTests(unittest.TestCase):
    def test_hand_computed_three_effects(self):
        data = pd.DataFrame([{GROUP: "A", WEIGHT: .6, BENCH_WEIGHT: .5, PORT_RETURN: .12, BENCH_RETURN: .1},
                             {GROUP: "B", WEIGHT: .4, BENCH_WEIGHT: .5, PORT_RETURN: .01, BENCH_RETURN: .02}])
        result = brinson_fachler(data)
        np.testing.assert_allclose(result[ALLOCATION], [.004, .004], atol=1e-15)
        np.testing.assert_allclose(result[SELECTION], [.01, -.005], atol=1e-15)
        np.testing.assert_allclose(result[INTERACTION], [.002, .001], atol=1e-15)
        self.assertAlmostEqual(result[ACTIVE].sum(), .016)

    def test_equal_portfolio_zero_effects(self):
        data = pd.DataFrame([{GROUP: "A", WEIGHT: 1, BENCH_WEIGHT: 1, PORT_RETURN: -.1, BENCH_RETURN: -.1}])
        self.assertEqual(brinson_fachler(data)[[ALLOCATION, SELECTION, INTERACTION]].sum().sum(), 0)

    def test_reject_invalid_weight_totals(self):
        data = pd.DataFrame([{GROUP: "A", WEIGHT: .8, BENCH_WEIGHT: 1, PORT_RETURN: 0, BENCH_RETURN: 0}])
        with self.assertRaises(ValueError):
            brinson_fachler(data)


class PortfolioTests(unittest.TestCase):
    def test_cap_waterfill(self):
        result = capped_weights(pd.Series({"A": 8., "B": 1., "C": 1.}), .5)
        np.testing.assert_allclose(result, [.5, .25, .25])

    def test_inverse_volatility(self):
        result = risk_aware_weights(pd.Series({"A": 0., "B": 0.}),
                                    pd.Series({"A": .1, "B": .2}), 1., .8, .01)
        np.testing.assert_allclose(result, [2/3, 1/3])

    def test_infeasible_and_bad_inputs(self):
        for raw, cap in ((pd.Series({"A": 1., "B": 1.}), .4),
                         (pd.Series({"A": np.nan, "B": 1.}), .6)):
            with self.assertRaises(ValueError):
                capped_weights(raw, cap)


if __name__ == "__main__":
    unittest.main()
