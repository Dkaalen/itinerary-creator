"""Formula expectations for the calculation workbook."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from calculator.columns import DATA_END_ROW, DATA_START_ROW, KALK_SHEET_NAME, TOTALS_ROW
from calculator.template_structure import default_template_path

ROW_FORMULA_COLUMNS = ("S", "U", "W", "X", "Y", "Z", "AB", "AC", "AD", "AE")
ROW_FORMULA_TEMPLATES = {
    "S": "=ROUND(Q{row}*R{row},2)",
    "U": "=ROUND(S{row}*(1-T{row}),2)",
    "W": "=IFERROR(VLOOKUP(V{row},Curr!$B$2:$C$13,2,FALSE),0)",
    "X": "=ROUND(U{row}*W{row},2)",
    "Y": "=Q{row}",
    "Z": "=ROUND(Y{row}*R{row},2)",
    "AB": "=IFERROR(VLOOKUP(AA{row},Curr!$B$2:$C$13,2,FALSE),0)",
    "AC": "=ROUND(Z{row}*AB{row},2)",
    "AD": "=ROUND(AC{row}-X{row},2)",
    "AE": "=IFERROR(AD{row}/AC{row},0)",
}
TOTAL_FORMULAS = {
    f"Z{TOTALS_ROW}": f"=SUM(Z{DATA_START_ROW}:Z{DATA_END_ROW})",
    f"AC{TOTALS_ROW}": f"=SUM(AC{DATA_START_ROW}:AC{DATA_END_ROW})",
    f"AD{TOTALS_ROW}": f"=SUM(AD{DATA_START_ROW}:AD{DATA_END_ROW})",
    f"AE{TOTALS_ROW}": f"=IFERROR(AD{TOTALS_ROW}/AC{TOTALS_ROW},0)",
    f"AF{TOTALS_ROW}": f"=SUM(AF{DATA_START_ROW}:AF{DATA_END_ROW})",
    f"AG{TOTALS_ROW}": f"=SUM(AG{DATA_START_ROW}:AG{DATA_END_ROW})",
    f"AH{TOTALS_ROW}": f"=SUM(AH{DATA_START_ROW}:AH{DATA_END_ROW})",
    f"AI{TOTALS_ROW}": f"=SUM(AI{DATA_START_ROW}:AI{DATA_END_ROW})",
    f"AJ{TOTALS_ROW}": f"=SUM(AJ{DATA_START_ROW}:AJ{DATA_END_ROW})",
}
PAYMENT_FORMULAS = {
    "Z106": "=Z103-Z107",
    "Z109": "=Z103*0.3",
    "Z110": "=Z107-Z109",
    "Z111": "=Z103-Z109-Z110",
}
LEGACY_PAYMENT_CELLS_TO_CLEAR = ("Y104", "Z104")


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
