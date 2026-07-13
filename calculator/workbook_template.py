"""Load the calculation workbook template."""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook

from calculator.template_structure import default_template_path, validate_template_structure


class WorkbookTemplateError(ValueError):
    """Raised when the bundled calculation template is not safe to export."""


def load_calculation_template(path: str | Path | None = None) -> Workbook:
    """Load a validated copy of the calculation workbook template."""

    template_path = Path(path) if path is not None else default_template_path()
    _raise_for_template_issues(template_path)
    return load_workbook(template_path, data_only=False)


def _raise_for_template_issues(template_path: Path) -> None:
    issues = validate_template_structure(template_path)
    if issues:
        formatted = "\n".join(f"- {issue}" for issue in issues)
        raise WorkbookTemplateError(f"Calculation template is invalid:\n{formatted}")
