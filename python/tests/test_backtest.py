import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from altdata_lab.backtest import *
from altdata_lab.config import *
from altdata_lab.pipeline import run, verify_manifest
from altdata_lab.signals import features_asof, validate_observations
from altdata_lab.synthetic import write_snapshot

# Config: disposable test files stay under the ignored scratch directory.
WORK_DIR = ROOT / ".work"
HAND_TICKERS = ("A", "B")
HAND_DATES = ("2020-01-31", "2020-02-29", "2020-03-31", "2020-04-30")
HAND_CONFIG = ResearchConfig(volatility_window=2, name_cap=.6, cost_bps=10)


def hand_inputs():
    universe = pd.DataFrame([{TICKER: ticker, GROUP: "Machinery"} for ticker in HAND_TICKERS])
    returns = pd.DataFrame([{TICKER: ticker, PERIOD: date,
                             RETURN: (.1 if ticker == "A" else -.1) if date == "2020-03-31" else 0.}
                            for date in HAND_DATES for ticker in HAND_TICKERS])
    observations = []
    for ticker in HAND_TICKERS:
        for date, available, value in (("2019-11-30", "2019-12-07", 80),
                                       ("2019-12-31", "2020-01-07", 100),
                                       ("2020-01-31", "2020-02-07", 110),
                                       ("2020-02-29", "2020-03-07", 121)):
            for metric in (JOBS, WEB):
                observations.append({TICKER: ticker, PERIOD: date, AVAILABLE: available, METRIC: metric, VALUE: value})
        observations.append({TICKER: ticker, PERIOD: "2019-12-31", AVAILABLE: "2020-02-14",
                             METRIC: OPERATING_MARGIN, VALUE: .12})
    return universe, returns, pd.DataFrame(observations)


class AsOfTests(unittest.TestCase):
    def test_hand_growth_and_future_observation_ignored(self):
        _, _, observations = hand_inputs()
        cutoff = "2020-02-29 23:59:59"
        base = features_asof(observations, cutoff, HAND_TICKERS)
        np.testing.assert_allclose(base[JOBS_GROWTH], [.1, .1])
        future = observations[AVAILABLE] > cutoff
        observations.loc[future, VALUE] = 1000000
        pd.testing.assert_frame_equal(base, features_asof(observations, cutoff, HAND_TICKERS))
        self.assertTrue((base[FEATURE_AVAILABLE] <= pd.Timestamp(cutoff)).all())

    def test_available_at_boundary(self):
        _, _, observations = hand_inputs()
        mask = (observations[PERIOD] == "2020-01-31")
        observations.loc[mask, AVAILABLE] = "2020-02-29 23:59:59"
        before = features_asof(observations, "2020-02-29 23:59:58", HAND_TICKERS)
        after = features_asof(observations, "2020-02-29 23:59:59", HAND_TICKERS)
        np.testing.assert_allclose(before[JOBS_GROWTH], [.25, .25])
        np.testing.assert_allclose(after[JOBS_GROWTH], [.1, .1])

    def test_reject_invalid_dates_duplicates_missing_stale(self):
        _, _, observations = hand_inputs()
        early = observations.copy()
        early[AVAILABLE] = "2019-01-01"
        for invalid in (early, pd.concat([observations, observations]), observations.assign(value=np.nan)):
            with self.assertRaises(ValueError):
                validate_observations(invalid)
        with self.assertRaisesRegex(ValueError, "Stale"):
            features_asof(observations, "2022-01-01", HAND_TICKERS)

    def test_growth_gap_is_not_a_monthly_change(self):
        _, _, observations = hand_inputs()
        observations = observations.loc[observations[PERIOD] != "2019-12-31"]
        observations = pd.concat([observations, pd.DataFrame([{TICKER: ticker, PERIOD: "2019-12-31",
            AVAILABLE: "2020-02-14", METRIC: OPERATING_MARGIN, VALUE: .12} for ticker in HAND_TICKERS])])
        with self.assertRaisesRegex(ValueError, "Nonconsecutive"):
            features_asof(observations, "2020-02-29", HAND_TICKERS)


class BacktestTests(unittest.TestCase):
    def test_hand_drift_costs_and_initial_funding(self):
        monthly, weights, attribution, summary = run_backtest(*hand_inputs(), HAND_CONFIG)
        np.testing.assert_allclose(monthly[GROSS], [0, 0], atol=1e-15)
        np.testing.assert_allclose(monthly[TRADED], [1, .1], atol=1e-15)
        np.testing.assert_allclose(monthly[TURNOVER], [1, .05], atol=1e-15)
        np.testing.assert_allclose(monthly[COST], [.001, .0001], atol=1e-15)
        self.assertAlmostEqual(summary["net_total_return"], (1-.001)*(1-.0001)-1)
        self.assertAlmostEqual(summary["maximum_drawdown"], .999 * .9999 - 1)
        self.assertEqual(summary["active_hit_rate"], 0)
        self.assertTrue((weights["volatility_last_period"] < weights[PERIOD]).all())

    def test_current_and_future_returns_do_not_change_current_weights(self):
        universe, returns, observations = hand_inputs()
        _, base_weights, _, _ = run_backtest(universe, returns, observations, HAND_CONFIG)
        returns.loc[returns[PERIOD] >= "2020-03-31", RETURN] = .5
        _, altered_weights, _, _ = run_backtest(universe, returns, observations, HAND_CONFIG)
        first_base = base_weights.loc[base_weights[PERIOD] == pd.Timestamp("2020-03-31"), WEIGHT]
        first_altered = altered_weights.loc[altered_weights[PERIOD] == pd.Timestamp("2020-03-31"), WEIGHT]
        np.testing.assert_allclose(first_base, first_altered, atol=0)

    def test_late_filing_never_enters_earlier_weights(self):
        universe, returns, observations = hand_inputs()
        late = pd.DataFrame([{TICKER: "A", PERIOD: "2020-03-31", AVAILABLE: "2020-05-15",
                              METRIC: OPERATING_MARGIN, VALUE: 999}])
        _, base, _, _ = run_backtest(universe, returns, observations, HAND_CONFIG)
        _, altered, _, _ = run_backtest(universe, returns, pd.concat([observations, late]), HAND_CONFIG)
        pd.testing.assert_frame_equal(base, altered)

    def test_missing_return_rejected(self):
        universe, returns, observations = hand_inputs()
        incomplete = returns.loc[~((returns[TICKER] == "A") & (returns[PERIOD] == "2020-03-31"))]
        with self.assertRaisesRegex(ValueError, "complete"):
            run_backtest(universe, incomplete, observations, HAND_CONFIG)

    def test_drawdown_includes_initial_capital(self):
        self.assertAlmostEqual(maximum_drawdown(pd.Series([-.1, .2, -.25])), -.25)
        self.assertAlmostEqual(maximum_drawdown(pd.Series([-.2, .1])), -.2)

    def test_cost_uses_both_buys_and_sells(self):
        trade = trade_statistics(pd.Series({"A": .5, "B": .5}), pd.Series({"A": .6, "B": .4}), 10)
        self.assertAlmostEqual(trade[COST], .0002)
        self.assertAlmostEqual(trade[TURNOVER], .1)

    def test_rank_ic_hand_case_and_undefined_ties(self):
        scores = pd.Series({"A": 1., "B": 2., "C": 3.})
        realized = pd.Series({"C": .2, "A": .3, "B": .1})
        self.assertAlmostEqual(information_coefficient(scores, realized), -.5)
        self.assertTrue(np.isnan(information_coefficient(scores * 0, realized)))


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK_DIR.mkdir(exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=WORK_DIR)
        cls.base = Path(cls.temporary.name)
        cls.data = cls.base / "data"
        cls.fixtures = cls.base / "fixtures"
        cls.output = cls.base / "output"
        write_snapshot(cls.data, cls.fixtures)
        with patch("socket.socket", side_effect=AssertionError("Network access forbidden")):
            cls.summary = run(cls.data, cls.output, cls.fixtures)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_reproducible_snapshot(self):
        before = (self.data / "manifest.json").read_bytes()
        write_snapshot(self.data, self.fixtures)
        self.assertEqual(before, (self.data / "manifest.json").read_bytes())

    def test_full_run_caps_cutoffs_and_reconciliation(self):
        weights = pd.read_csv(self.output / "weights.csv")
        self.assertLessEqual(weights[WEIGHT].max(), ResearchConfig().name_cap + 1e-10)
        np.testing.assert_allclose(weights.groupby(PERIOD)[WEIGHT].sum(), 1)
        self.assertTrue((pd.to_datetime(weights[FEATURE_AVAILABLE]) <= pd.to_datetime(weights[DECISION])).all())
        self.assertLess(self.summary["max_attribution_residual"], 1e-12)
        self.assertEqual(self.summary["periods"], 48)
        self.assertGreater(self.summary["extraction_status_counts"]["rejected"], 0)
        self.assertEqual(self.summary["recorded_adapter_status_counts"]["rejected"], 3)

    def test_hash_tampering_detected(self):
        path = self.data / "returns.csv"
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        try:
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_manifest(self.data)
        finally:
            path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
