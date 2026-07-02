"""Formula expectations for the calculation workbook."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from calculator.columns import DATA_END_ROW, DATA_START_ROW, KALK_SHEET_NAME, TOTALS_ROW
from calculator.template_structure import default_template_path

ROW_FORMULA_COLUMNS = ("S", "U", "W", "X", "Y", "Z", "AB", "AC", "AD", "AE")
ROW_FORMULA_TEMPLATES = {
    "S": "=+Q{row}*R{row}",
    "U": "=S{row}*(1-T{row})",
    "W": "=IFERROR(VLOOKUP(V{row},Curr!$B$2:$C$13,2,FALSE),0)",
    "X": "=U{row}*W{row}",
    "Y": "=Q{row}",
    "Z": "=+Y{row}*R{row}",
    "AB": "=IFERROR(VLOOKUP(AA{row},Curr!$B$2:$C$13,2,FALSE),0)",
    "AC": "=+Y{row}*AB{row}*R{row}",
    "AD": "=+AC{row}-X{row}",
    "AE": "=IFERROR(AD{row}/AC{row},0)",
}
TOTAL_FORMULAS = {
    f"Z{TOTALS_ROW}": "=SUM(Z7:Z99)",
    f"AC{TOTALS_ROW}": "=SUM(AC7:AC99)",
    f"AD{TOTALS_ROW}": "=SUM(AD7:AD99)",
    f"AE{TOTALS_ROW}": "=IFERROR(AD101/AC101,0)",
    f"AF{TOTALS_ROW}": "=SUM(AF8:AF100)",
    f"AG{TOTALS_ROW}": "=SUM(AG8:AG100)",
    f"AH{TOTALS_ROW}": "=SUM(AH8:AH100)",
    f"AI{TOTALS_ROW}": "=SUM(AI8:AI100)",
    f"AJ{TOTALS_ROW}": "=SUM(AJ8:AJ100)",
}
PAYMENT_FORMULAS = {
    "Z104": "=Z103/2",
    "Z106": "=Z103-Z107",
    "Z109": "=Z103*0.3",
    "Z110": "=Z107-Z109",
    "Z111": "=Z103-Z109-Z110",
}


@dataclass(frozen=True)
class FormulaMap:
    """Actual formulas found in the workbook template."""

    row_formulas: dict[int, dict[str, str | None]]
    total_formulas: dict[str, str | None]
    payment_formulas: dict[str, str | None]


def expected_row_formulas(row: int) -> dict[str, str]:
    """Return expected per-row formulas for a Kalk data row."""

    if row < DATA_START_ROW or row > DATA_END_ROW:
        raise ValueError(f"Formula row must be between {DATA_START_ROW} and {DATA_END_ROW}.")
    return {column: template.format(row=row) for column, template in ROW_FORMULA_TEMPLATES.items()}


def inspect_formula_map(path: str | Path | None = None) -> FormulaMap:
    """Read the formula map from the calculation template."""

    template_path = Path(path) if path is not None else default_template_path()
    sheet = load_workbook(template_path, data_only=False)[KALK_SHEET_NAME]
    row_formulas = {
        row: {column: sheet[f"{column}{row}"].value for column in ROW_FORMULA_COLUMNS}
        for row in range(DATA_START_ROW, DATA_END_ROW + 1)
    }
    return FormulaMap(
        row_formulas=row_formulas,
        total_formulas={cell: sheet[cell].value for cell in TOTAL_FORMULAS},
        payment_formulas={cell: sheet[cell].value for cell in PAYMENT_FORMULAS},
    )


def validate_formula_map(path: str | Path | None = None) -> tuple[str, ...]:
    """Return formula mismatches found in the template."""

    formula_map = inspect_formula_map(path)
    issues: list[str] = []
    for row, formulas in formula_map.row_formulas.items():
        expected = expected_row_formulas(row)
        for column, expected_formula in expected.items():
            actual_formula = formulas[column]
            if actual_formula != expected_formula:
                issues.append(f"{column}{row}: expected {expected_formula!r}, got {actual_formula!r}.")
    issues.extend(_mismatches(formula_map.total_formulas, TOTAL_FORMULAS))
    issues.extend(_mismatches(formula_map.payment_formulas, PAYMENT_FORMULAS))
    return tuple(issues)


def _mismatches(actual: dict[str, str | None], expected: dict[str, str]) -> list[str]:
    issues: list[str] = []
    for cell, expected_formula in expected.items():
        actual_formula = actual[cell]
        if actual_formula != expected_formula:
            issues.append(f"{cell}: expected {expected_formula!r}, got {actual_formula!r}.")
    return issues
