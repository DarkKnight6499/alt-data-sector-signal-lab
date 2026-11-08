"""Shared schema and explicit research assumptions."""

from dataclasses import dataclass
from pathlib import Path

# Config: paths, schema, units and research assumptions.
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "synthetic"
OUTPUT_DIR = ROOT / "examples" / "output"
FIXTURE_DIR = ROOT / "python" / "tests" / "fixtures"
SEED = 1729
START = "2020-01-31"
MONTHS = 60
AUTHOR = "Yazad Madan"
TICKER = "ticker"
GROUP = "subsector"
PERIOD = "period_end"
AVAILABLE = "available_at"
METRIC = "metric"
VALUE = "value"
UNIT = "unit"
DOC_ID = "document_id"
TEXT = "text"
KIND = "kind"
SYNTHETIC = "synthetic"
RETURN = "total_return"
DECISION = "decision_at"
WEIGHT = "portfolio_weight"
BENCH_WEIGHT = "benchmark_weight"
PORT_RETURN = "portfolio_return"
BENCH_RETURN = "benchmark_return"
ALLOCATION = "allocation"
SELECTION = "selection"
INTERACTION = "interaction"
ACTIVE = "active_return"
REVENUE = "revenue"
OPERATING_INCOME = "operating_income"
OPERATING_MARGIN = "operating_margin"
BACKLOG = "backlog"
JOBS = "job_postings"
WEB = "web_traffic"
JOBS_GROWTH = "job_growth"
WEB_GROWTH = "web_growth"
SCORE = "score"
VOL = "volatility"
STATUS = "status"
REASON = "reason"
EVIDENCE = "evidence"
METHOD = "method"
EXTRACTED = "extracted_value"
REPORTED = "reported_value"
ERROR = "absolute_error"
TOLERANCE = "tolerance"
ACCEPTED = "accepted"
CHECK_COLUMNS = [DOC_ID, TICKER, PERIOD, AVAILABLE, METRIC, UNIT, EVIDENCE,
                 EXTRACTED, REPORTED, ERROR, TOLERANCE, STATUS, REASON, METHOD]
MONEY_UNIT = "USD_million"
RATIO_UNIT = "ratio"
COUNT_UNIT = "count"
INDEX_UNIT = "index"
KPI_UNITS = {REVENUE: MONEY_UNIT, OPERATING_INCOME: MONEY_UNIT,
             BACKLOG: MONEY_UNIT, OPERATING_MARGIN: RATIO_UNIT}
REQUIRED_KPIS = tuple(KPI_UNITS)
SUBSECTORS = ("Machinery", "Aerospace", "Electrical")
FIRMS_PER_GROUP = 4
JOBS_LAG_DAYS = 7
WEB_LAG_DAYS = 10
FILING_LAG_DAYS = 45
TEXT_DECIMALS = 4
MONEY_ABS_TOL = 0.0001
RATIO_ABS_TOL = 0.000001
REL_TOL = 0.000001
MAX_AGE_DAYS = {JOBS: 75, WEB: 75, OPERATING_MARGIN: 250}
FEATURES = (JOBS_GROWTH, WEB_GROWTH, OPERATING_MARGIN)
FLOAT_TOL = 1e-10


@dataclass(frozen=True)
class ResearchConfig:
    """Illustrative controls, not regulatory limits or optimized parameters."""

    volatility_window: int = 12
    volatility_floor: float = 0.01
    name_cap: float = 0.15
    signal_tilt: float = 0.8
    cost_bps: float = 10.0
    periods_per_year: int = 12
