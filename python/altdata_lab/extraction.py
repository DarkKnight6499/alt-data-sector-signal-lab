"""Conservative line parser and local recorded-response adapter. No network I/O."""

import json
import math
import re
from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from .config import (ACCEPTED, AVAILABLE, BACKLOG, CHECK_COLUMNS, DOC_ID, ERROR,
                     EVIDENCE, EXTRACTED, KPI_UNITS, METHOD, METRIC, MONEY_ABS_TOL,
                     OPERATING_INCOME, OPERATING_MARGIN, PERIOD, RATIO_ABS_TOL,
                     REASON, REL_TOL, REPORTED, REQUIRED_KPIS, REVENUE, STATUS,
                     TICKER, TOLERANCE, UNIT, VALUE)

# Config: the parser deliberately accepts only this narrow reported-value grammar.
LABELS = {"Revenue": REVENUE, "Operating income": OPERATING_INCOME,
          "Backlog": BACKLOG, "Operating margin": OPERATING_MARGIN}
NUMBER = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
LINE = re.compile(
    rf"^(Revenue|Operating income|Backlog|Operating margin) was "
    rf"(?:(?:USD (?P<money>{NUMBER}) (?P<scale>million|billion))|"
    rf"(?P<percent>{NUMBER})%) for period ended (?P<period>\d{{4}}-\d{{2}}-\d{{2}})\.$"
)
RECORD_FIELDS = {METRIC, VALUE, UNIT, PERIOD, EVIDENCE}


@dataclass(frozen=True)
class Extraction:
    metric: str
    value: float
    unit: str
    period_end: str
    evidence: str


class Extractor(Protocol):
    def extract(self, document_id: str, text: str) -> list[Extraction]:
        """Return candidates with exact evidence and explicit period and unit."""
        ...


class RuleExtractor:
    def extract(self, document_id: str, text: str) -> list[Extraction]:
        result = []
        for line in text.splitlines():
            match = LINE.fullmatch(line.strip())
            if match is None:
                continue
            metric = LABELS[match.group(1)]
            is_ratio = metric == OPERATING_MARGIN
            if is_ratio != (match.group("percent") is not None):
                continue
            raw = match.group("percent") if is_ratio else match.group("money")
            value = float(raw.replace(",", ""))
            value *= 0.01 if is_ratio else (1000 if match.group("scale") == "billion" else 1)
            result.append(Extraction(metric, value, KPI_UNITS[metric],
                                     match.group("period"), line.strip()))
        return result


class RecordedLLMAdapter:
    """Replay authored synthetic fixtures; these are not actual provider responses."""

    def __init__(self, responses: dict):
        if not isinstance(responses, dict):
            raise ValueError("Recorded responses must be keyed by document id")
        self.responses = responses

    @classmethod
    def from_file(cls, path):
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def extract(self, document_id: str, text: str) -> list[Extraction]:
        records = self.responses.get(document_id, [])
        if not isinstance(records, list):
            raise ValueError("Recorded response must be a list")
        result = []
        for record in records:
            if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
                raise ValueError("Invalid recorded extraction schema")
            if (any(not isinstance(record[key], str)
                    for key in (METRIC, UNIT, PERIOD, EVIDENCE))
                    or record[METRIC] not in KPI_UNITS or isinstance(record[VALUE], bool)
                    or not isinstance(record[VALUE], (float, int))
                    or not math.isfinite(record[VALUE])):
                raise ValueError("Invalid recorded extraction types or metric")
            result.append(Extraction(**record))
        return result


def validate_extractions(document: dict, candidates: list[Extraction],
                         financials: pd.DataFrame, method: str) -> pd.DataFrame:
    """Require matched identity, period, units, evidence and a reported control."""
    required = {TICKER, PERIOD, METRIC, VALUE, UNIT, AVAILABLE}
    if not required.issubset(financials.columns):
        raise ValueError("Missing financial control schema")
    relevant = financials.loc[(financials[TICKER] == document[TICKER]) &
                              (financials[PERIOD] == document[PERIOD])]
    if relevant.loc[:, sorted(required)].isna().any().any():
        raise ValueError("Missing financial control fields")
    if relevant.duplicated([TICKER, PERIOD, METRIC]).any():
        raise ValueError("Duplicate reported financial control")
    lookup = relevant.set_index(METRIC).to_dict("index")
    expected = {key: row[VALUE] for key, row in lookup.items()}
    if REVENUE in expected and OPERATING_INCOME in expected and expected[REVENUE] != 0:
        expected[OPERATING_MARGIN] = expected[OPERATING_INCOME] / expected[REVENUE]
    rows = []
    for candidate in candidates:
        metric = candidate.metric
        control = expected.get(metric)
        tolerance = max(RATIO_ABS_TOL if metric == OPERATING_MARGIN else MONEY_ABS_TOL,
                        abs(control or 0) * REL_TOL)
        error = abs(candidate.value - control) if control is not None else None
        dependencies = (REVENUE, OPERATING_INCOME) if metric == OPERATING_MARGIN else (metric,)
        bad_control_unit = any(key in lookup and lookup[key][UNIT] != KPI_UNITS.get(key)
                               for key in dependencies)
        reason = ""
        if sum(item.metric == metric for item in candidates) > 1:
            reason = "duplicate_metric"
        elif candidate.period_end != document[PERIOD]:
            reason = "period_mismatch"
        elif candidate.unit != KPI_UNITS.get(metric):
            reason = "unit_mismatch"
        elif bad_control_unit:
            reason = "reported_unit_mismatch"
        elif not candidate.evidence.strip() or candidate.evidence not in document["text"]:
            reason = "ungrounded_evidence"
        elif control is None or not math.isfinite(control):
            reason = "missing_reported_control"
        elif not math.isfinite(candidate.value) or error > tolerance:
            reason = "value_mismatch"
        elif AVAILABLE in relevant and (pd.to_datetime(relevant[AVAILABLE], format="mixed") >
                                       pd.Timestamp(document[AVAILABLE])).any():
            reason = "control_not_available"
        rows.append({DOC_ID: document[DOC_ID], TICKER: document[TICKER],
                     PERIOD: document[PERIOD], AVAILABLE: document[AVAILABLE], METRIC: metric,
                     UNIT: candidate.unit, EVIDENCE: candidate.evidence, EXTRACTED: candidate.value,
                     REPORTED: control, ERROR: error, TOLERANCE: tolerance,
                     STATUS: "rejected" if reason else ACCEPTED, REASON: reason,
                     METHOD: method})
    for metric in REQUIRED_KPIS:
        if not any(item.metric == metric for item in candidates):
            rows.append({DOC_ID: document[DOC_ID], TICKER: document[TICKER],
                         PERIOD: document[PERIOD], AVAILABLE: document[AVAILABLE], METRIC: metric,
                         UNIT: KPI_UNITS[metric], STATUS: "missing",
                         REASON: "not_extracted", METHOD: method})
    return pd.DataFrame(rows, columns=CHECK_COLUMNS)
