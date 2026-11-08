import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd

from altdata_lab.backtest import COST, GROSS, NET
from altdata_lab.config import (ALLOCATION, AUTHOR, BENCH_RETURN, INTERACTION,
                                OUTPUT_DIR, ROOT, SELECTION)

# Config: exported formula workbook and independent named source columns.
WORKBOOK_PATH = ROOT / "excel" / "attribution.xlsx"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "dc": "http://purl.org/dc/elements/1.1/",
      "r": "http://schemas.openxmlformats.org/package/2006/relationships"}
SUMMARY_SHEET = "xl/worksheets/sheet1.xml"
GROUP_SHEET = "xl/worksheets/sheet2.xml"
HAND_SHEET = "xl/worksheets/sheet3.xml"
FIRST_DATA_ROW = 6
TOLERANCE = 1e-10
EFFECT_EXCEL_COLUMNS = {ALLOCATION: "H", SELECTION: "I", INTERACTION: "J"}


def cells(archive, name):
    return {cell.get("r"): cell for cell in ET.fromstring(archive.read(name)).findall(".//s:c", NS)}


def number(cell_map, address):
    return float(cell_map[address].find("s:v", NS).text)


class WorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not WORKBOOK_PATH.exists():
            raise RuntimeError("Build excel/attribution.xlsx before final verification")
        cls.archive = ZipFile(WORKBOOK_PATH)
        cls.summary = cells(cls.archive, SUMMARY_SHEET)
        cls.groups = cells(cls.archive, GROUP_SHEET)
        cls.hand = cells(cls.archive, HAND_SHEET)

    @classmethod
    def tearDownClass(cls):
        cls.archive.close()

    def test_every_month_reconciles_to_python(self):
        source = pd.read_csv(OUTPUT_DIR / "monthly_backtest.csv")
        for offset, record in enumerate(source.to_dict("records")):
            row = FIRST_DATA_ROW + offset
            self.assertAlmostEqual(number(self.summary, f"E{row}"), record[GROSS] - record[BENCH_RETURN], delta=TOLERANCE)
            self.assertAlmostEqual(number(self.summary, f"G{row}"), record[NET] - record[BENCH_RETURN], delta=TOLERANCE)
            self.assertAlmostEqual(number(self.summary, f"F{row}"), record[COST], delta=TOLERANCE)
            for column in ("J", "K", "L", "M"):
                self.assertLess(abs(number(self.summary, f"{column}{row}")), TOLERANCE)

    def test_all_group_effects_are_formulas_and_match_python(self):
        source = pd.read_csv(OUTPUT_DIR / "attribution.csv")
        for offset, record in enumerate(source.to_dict("records")):
            row = FIRST_DATA_ROW + offset
            for effect, column in EFFECT_EXCEL_COLUMNS.items():
                self.assertIsNotNone(self.groups[f"{column}{row}"].find("s:f", NS))
                self.assertAlmostEqual(number(self.groups, f"{column}{row}"), record[effect], delta=TOLERANCE)

    def test_hand_example(self):
        for address, expected in (("B11", .008), ("B12", .005), ("B13", .003), ("B15", .016)):
            self.assertAlmostEqual(number(self.hand, address), expected)

    def test_no_cached_errors_or_external_links(self):
        for name in self.archive.namelist():
            self.assertNotIn("externalLinks/", name)
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                for cell in cells(self.archive, name).values():
                    self.assertNotEqual(cell.get("t"), "e")
                    if cell.find("s:f", NS) is not None:
                        self.assertIsNotNone(cell.find("s:v", NS))

    def test_metadata_recalculation_and_plain_format(self):
        core = ET.fromstring(self.archive.read("docProps/core.xml"))
        self.assertEqual(core.find("dc:creator", NS).text, AUTHOR)
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        self.assertEqual(workbook.find("s:calcPr", NS).get("calcMode"), "auto")
        styles = ET.fromstring(self.archive.read("xl/styles.xml"))
        for font in styles.findall("s:fonts/s:font", NS):
            color = font.find("s:color", NS)
            if color is not None and "rgb" in color.attrib:
                self.assertIn(color.get("rgb")[-6:], {"000000"})
        for name in (SUMMARY_SHEET, GROUP_SHEET, HAND_SHEET):
            self.assertNotIn(b"tabColor", self.archive.read(name))


if __name__ == "__main__":
    unittest.main()
