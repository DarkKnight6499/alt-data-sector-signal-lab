import fs from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

// Config: source interchange, workbook destination, schema and numerical tolerance.
const ROOT = process.cwd();
const WORK = path.join(ROOT, ".work");
const INPUT = path.join(WORK, "workbook_inputs.json");
const OUTPUT = path.join(ROOT, "excel", "attribution.xlsx");
const TEMP_OUTPUT = path.join(WORK, "attribution.xlsx");
const TOLERANCE = 1e-10;
const FONT = "Arial";
const PERCENT_FORMAT = "0.00%;(0.00%);0.00%";
const DIFFERENCE_FORMAT = "0.0000000000;(0.0000000000);0.0000000000";
const PERIOD = "period_end";
const GROUP = "subsector";
const WP = "portfolio_weight";
const WB = "benchmark_weight";
const RP = "portfolio_return";
const RB = "benchmark_return";
const GROSS = "gross_return";
const NET = "net_return";
const COST = "transaction_cost";
const ALLOCATION = "allocation";
const SELECTION = "selection";
const INTERACTION = "interaction";
const EFFECT_HEADERS = ["Month", "Subsector", "Port weight", "Bench weight", "Port return", "Bench return",
  "Total bench", "Allocation", "Selection", "Interaction", "Port contrib", "Bench contrib"];
const SUMMARY_HEADERS = ["Month", "Allocation", "Selection", "Interaction", "Gross active", "Cost",
  "Net active", "Python gross", "Python net", "Gross diff", "Net diff", "Port wt diff", "Bench wt diff"];
const FIRST_ROW = 6;
const HAND = [
  { [PERIOD]: "2000-01-31", [GROUP]: "A", [WP]: .6, [WB]: .5, [RP]: .12, [RB]: .10 },
  { [PERIOD]: "2000-01-31", [GROUP]: "B", [WP]: .4, [WB]: .5, [RP]: .01, [RB]: .02 },
];

const data = JSON.parse(await fs.readFile(INPUT, "utf8"));
const workbook = Workbook.create();
const summary = workbook.worksheets.add("Attribution");
const groups = workbook.worksheets.add("Groups");
const hand = workbook.worksheets.add("Hand check");
const groupLast = FIRST_ROW + data.groups.length - 1;
const summaryLast = FIRST_ROW + data.monthly.length - 1;

function title(sheet, text, note, endColumn, lastRow) {
  sheet.showGridLines = false;
  sheet.getRange(`A2:${endColumn}${lastRow}`).format.font = { name: FONT, size: 10 };
  sheet.getRange(`A2:${endColumn}${lastRow}`).format.rowHeight = 21;
  sheet.getRange(`A2:${endColumn}${lastRow}`).format.columnWidth = 15;
  sheet.getRange("A:A").format.columnWidth = 13;
  sheet.getRange("A2").values = [[text]];
  sheet.getRange("A2").format.font = { name: FONT, size: 14, bold: true };
  sheet.getRange("A3").values = [[note]];
  sheet.getRange(`A5:${endColumn}5`).format.font = { name: FONT, size: 10, bold: true };
  sheet.getRange(`A5:${endColumn}5`).format.rowHeight = 29;
  sheet.getRange(`A5:${endColumn}5`).format.horizontalAlignment = "center";
  sheet.getRange(`A5:${endColumn}5`).format.wrapText = true;
  sheet.getRange(`A6:A${lastRow}`).setNumberFormat("mmm-yy");
  sheet.freezePanes.freezeRows(5);
}

function effectTable(sheet, records) {
  const lastRow = FIRST_ROW + records.length - 1;
  sheet.getRange("A5:L5").values = [EFFECT_HEADERS];
  sheet.getRange(`A${FIRST_ROW}:F${lastRow}`).values = records.map(record => [
    new Date(`${record[PERIOD].slice(0, 10)}T00:00:00Z`), record[GROUP], record[WP], record[WB], record[RP], record[RB],
  ]);
  sheet.getRange(`G${FIRST_ROW}:L${lastRow}`).formulas = records.map((record, index) => {
    const row = FIRST_ROW + index;
    return [
      `=SUMIFS($L$${FIRST_ROW}:$L$${lastRow},$A$${FIRST_ROW}:$A$${lastRow},A${row})`,
      `=(C${row}-D${row})*(F${row}-G${row})`,
      `=D${row}*(E${row}-F${row})`,
      `=(C${row}-D${row})*(E${row}-F${row})`,
      `=C${row}*E${row}`, `=D${row}*F${row}`,
    ];
  });
  sheet.getRange(`C${FIRST_ROW}:L${lastRow}`).setNumberFormat(PERCENT_FORMAT);
}

title(summary, "Industrial attribution", "Synthetic data. Results are not evidence of alpha.", "M", summaryLast);
title(groups, "Monthly group calculations", "Inputs: examples/output/attribution.csv. All names, weights and returns are synthetic.", "L", groupLast);
title(hand, "Hand-computed attribution", "Two groups. Expected active return: 1.60%. Separate interaction convention.", "L", 16);
groups.getRange("B:B").format.columnWidth = 18;
effectTable(groups, data.groups);
effectTable(hand, HAND);
summary.getRange("A5:M5").values = [SUMMARY_HEADERS];
for (let index = 0; index < data.monthly.length; index++) {
  const row = FIRST_ROW + index;
  const record = data.monthly[index];
  summary.getRange(`A${row}`).values = [[new Date(`${record[PERIOD].slice(0, 10)}T00:00:00Z`)]];
  summary.getRange(`F${row}`).values = [[record[COST]]];
  summary.getRange(`H${row}:I${row}`).values = [[record[GROSS] - record[RB], record[NET] - record[RB]]];
  for (const [column, source] of [["B", "H"], ["C", "I"], ["D", "J"]]) {
    summary.getRange(`${column}${row}`).formulas = [[
      `=SUMIFS('Groups'!$${source}$${FIRST_ROW}:$${source}$${groupLast},'Groups'!$A$${FIRST_ROW}:$A$${groupLast},A${row})`,
    ]];
  }
  summary.getRange(`E${row}`).formulas = [[`=SUM(B${row}:D${row})`]];
  summary.getRange(`G${row}`).formulas = [[`=E${row}-F${row}`]];
  summary.getRange(`J${row}:M${row}`).formulas = [[`=E${row}-H${row}`, `=G${row}-I${row}`,
    `=SUMIFS('Groups'!$C$${FIRST_ROW}:$C$${groupLast},'Groups'!$A$${FIRST_ROW}:$A$${groupLast},A${row})-1`,
    `=SUMIFS('Groups'!$D$${FIRST_ROW}:$D$${groupLast},'Groups'!$A$${FIRST_ROW}:$A$${groupLast},A${row})-1`]];
}
summary.getRange(`B6:I${summaryLast}`).setNumberFormat(PERCENT_FORMAT);
summary.getRange(`J6:M${summaryLast}`).setNumberFormat(DIFFERENCE_FORMAT);
hand.getRange("A10:D13").values = [
  ["Effect", "Live total", "Hand expected", "Difference"],
  ["Allocation", null, .008, null],
  ["Selection", null, .005, null],
  ["Interaction", null, .003, null],
];
hand.getRange("B11:B13").formulas = [["=SUM(H6:H7)"], ["=SUM(I6:I7)"], ["=SUM(J6:J7)"]];
hand.getRange("D11:D13").formulas = [["=B11-C11"], ["=B12-C12"], ["=B13-C13"]];
hand.getRange("A15").values = [["Gross active"]];
hand.getRange("B15").formulas = [["=SUM(B11:B13)"]];
hand.getRange("C15").values = [[.016]];
hand.getRange("D15").formulas = [["=B15-C15"]];
hand.getRange("B11:C15").setNumberFormat(PERCENT_FORMAT);
hand.getRange("D11:D15").setNumberFormat(DIFFERENCE_FORMAT);
hand.getRange("A10:D10").format.font = { name: FONT, size: 10, bold: true };
workbook.recalculate();

// Independent source totals catch shifted formula ranges before export.
for (let index = 0; index < data.groups.length; index++) {
  const row = FIRST_ROW + index;
  const actual = groups.getRange(`H${row}:J${row}`).values[0];
  for (const [effectIndex, effect] of [ALLOCATION, SELECTION, INTERACTION].entries()) {
    assert.ok(Math.abs(actual[effectIndex] - data.groups[index][effect]) < TOLERANCE, `Group ${row} ${effect}`);
  }
}
for (const values of summary.getRange(`J6:M${summaryLast}`).values) {
  for (const value of values) assert.ok(typeof value === "number" && Math.abs(value) < TOLERANCE);
}
for (const address of ["D11", "D12", "D13", "D15"]) assert.ok(Math.abs(hand.getRange(address).values[0][0]) < TOLERANCE);

// Input changes must flow through the live formulas, then original values are restored.
const originalReturn = groups.getRange("E6").values[0][0];
const originalNetActive = summary.getRange("G6").values[0][0];
const groupWeight = groups.getRange("C6").values[0][0];
groups.getRange("E6").values = [[originalReturn + .01]];
workbook.recalculate();
assert.ok(Math.abs(summary.getRange("G6").values[0][0] - originalNetActive - .01 * groupWeight) < TOLERANCE);
groups.getRange("E6").values = [[originalReturn]];
workbook.recalculate();

const errors = await workbook.inspect({ kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 }, summary: "Formula errors" });
await fs.writeFile(path.join(WORK, "workbook_error_scan.txt"), errors.ndjson);
for (const sheet of [summary, groups, hand]) {
  const preview = await workbook.render({ sheetName: sheet.name,
    range: sheet.name === "Hand check" ? "A1:L16" : (sheet.name === "Attribution" ? "A1:M13" : "A1:L13"),
    scale: 1.4, format: "png" });
  await fs.writeFile(path.join(WORK, `${sheet.name.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const file = await SpreadsheetFile.exportXlsx(workbook);
await file.save(TEMP_OUTPUT);
await fs.rename(TEMP_OUTPUT, OUTPUT);
await fs.writeFile(path.join(WORK, "workbook_checks.json"), JSON.stringify({
  group_rows: data.groups.length, monthly_rows: data.monthly.length, hand_example: "passed",
  source_reconciliation: "passed", input_perturbation: "passed",
  formula_engine: "artifact-tool", native_excel: "not tested",
}, null, 2));
console.log(`Workbook exported: ${data.monthly.length} months, ${data.groups.length} group rows. Formula checks passed.`);
