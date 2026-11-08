"""Prepare named workbook inputs from Python outputs, without Excel dependencies."""

import json

import pandas as pd

from altdata_lab.backtest import COST, GROSS, NET
from altdata_lab.config import (ALLOCATION, BENCH_RETURN, BENCH_WEIGHT, GROUP, INTERACTION,
                                OUTPUT_DIR, PERIOD, PORT_RETURN, ROOT, SELECTION, WEIGHT)

# Config: all workbook source tables and the transient interchange path.
WORK_DIR = ROOT / ".work"
INPUT_FILE = WORK_DIR / "workbook_inputs.json"
GROUP_FIELDS = [PERIOD, GROUP, WEIGHT, BENCH_WEIGHT, PORT_RETURN, BENCH_RETURN,
                ALLOCATION, SELECTION, INTERACTION]
MONTH_FIELDS = [PERIOD, GROSS, NET, BENCH_RETURN, COST]


def main():
    WORK_DIR.mkdir(exist_ok=True)
    groups = pd.read_csv(OUTPUT_DIR / "attribution.csv")
    monthly = pd.read_csv(OUTPUT_DIR / "monthly_backtest.csv")
    payload = {"groups": groups.loc[:, GROUP_FIELDS].to_dict("records"),
               "monthly": monthly.loc[:, MONTH_FIELDS].to_dict("records")}
    INPUT_FILE.write_text(json.dumps(payload, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Workbook inputs: {len(groups)} group rows, {len(monthly)} months")


if __name__ == "__main__":
    main()
