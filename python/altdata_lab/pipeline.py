"""Run the shipped snapshot without network access."""

import hashlib
import json
from dataclasses import asdict

import pandas as pd

from .backtest import run_backtest
from .config import (ACCEPTED, AVAILABLE, DATA_DIR, DOC_ID, EXTRACTED, FIXTURE_DIR,
                     METRIC, OPERATING_MARGIN, OUTPUT_DIR, PERIOD, RATIO_UNIT,
                     STATUS, SYNTHETIC, TEXT, TICKER, UNIT, VALUE, ResearchConfig)
from .extraction import RecordedLLMAdapter, RuleExtractor, validate_extractions
from .signals import validate_observations
from .synthetic import write_snapshot

# Config: files read by the offline entry point.
CSV_FILES = ("universe.csv", "returns.csv", "observations.csv", "reported_financials.csv")
EXTRACTION_REPORT = "extraction_report.csv"
LLM_REPORT = "recorded_adapter_report.csv"


def verify_manifest(data_dir, fixture_dir=None):
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    if not manifest[SYNTHETIC] or manifest["public_observations"] != 0:
        raise ValueError("This demo requires an explicitly synthetic manifest")
    for filename, expected in manifest["files"].items():
        path = (data_dir / filename).resolve()
        if path.parent != data_dir.resolve():
            raise ValueError("Manifest path escapes snapshot")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            raise ValueError(f"Snapshot hash mismatch: {filename}")
    if fixture_dir is not None:
        fixture = fixture_dir / "recorded_responses.json"
        if hashlib.sha256(fixture.read_bytes()).hexdigest() != manifest["recorded_fixture_sha256"]:
            raise ValueError("Recorded fixture hash mismatch")


def extract_panel(documents, financials, extractor, method):
    reports, accepted_rows = [], []
    for doc in documents:
        candidates = extractor.extract(doc[DOC_ID], doc[TEXT])
        report = validate_extractions(doc, candidates, financials, method)
        reports.append(report)
        for record in report.loc[report[STATUS] == ACCEPTED].to_dict("records"):
            if record[METRIC] == OPERATING_MARGIN:
                accepted_rows.append({TICKER: doc[TICKER], PERIOD: doc[PERIOD],
                                      AVAILABLE: doc[AVAILABLE], METRIC: OPERATING_MARGIN,
                                      VALUE: record[EXTRACTED], UNIT: RATIO_UNIT, SYNTHETIC: True})
    return pd.concat(reports, ignore_index=True), pd.DataFrame(accepted_rows)


def run(data_dir=DATA_DIR, output_dir=OUTPUT_DIR, fixture_dir=FIXTURE_DIR, config=ResearchConfig()):
    verify_manifest(data_dir, fixture_dir)
    frames = {name: pd.read_csv(data_dir / name) for name in CSV_FILES}
    documents = [json.loads(line) for line in (data_dir / "documents.jsonl").read_text(encoding="utf-8").splitlines()]
    if any(not doc.get(SYNTHETIC) for doc in documents) or any(not frame[SYNTHETIC].eq(True).all() for frame in frames.values()):
        raise ValueError("Missing synthetic labels")
    report, filing_panel = extract_panel(documents, frames["reported_financials.csv"], RuleExtractor(), "rule")
    adapter = RecordedLLMAdapter.from_file(fixture_dir / "recorded_responses.json")
    fixture_documents = [doc for doc in documents if doc[DOC_ID] in adapter.responses]
    recorded_report, _ = extract_panel(fixture_documents, frames["reported_financials.csv"], adapter, "recorded_adapter")
    observations = pd.concat([frames["observations.csv"], filing_panel], ignore_index=True)
    validate_observations(observations)
    monthly, weights, attribution, summary = run_backtest(frames["universe.csv"], frames["returns.csv"], observations, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, frame in ((EXTRACTION_REPORT, report), (LLM_REPORT, recorded_report),
                            ("validated_observations.csv", observations), ("monthly_backtest.csv", monthly),
                            ("weights.csv", weights), ("attribution.csv", attribution)):
        frame.to_csv(output_dir / filename, index=False, float_format="%.12g", lineterminator="\n")
    summary["extraction_status_counts"] = report[STATUS].value_counts().to_dict()
    summary["recorded_adapter_status_counts"] = recorded_report[STATUS].value_counts().to_dict()
    summary["warning"] = "Results on synthetic data are not evidence of alpha."
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output_dir / "run_manifest.json").write_text(json.dumps({"synthetic": True,
        "snapshot_manifest_sha256": hashlib.sha256((data_dir / "manifest.json").read_bytes()).hexdigest(),
        "controls": asdict(config), "numpy_version": __import__("numpy").__version__,
        "pandas_version": pd.__version__,
        "output_files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted(output_dir.glob("*.csv"))}}, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
