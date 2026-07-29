"""Export calculator state into the calculation workbook template."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from openpyxl.packaging.custom import StringProperty
from openpyxl.workbook.workbook import Workbook

from calculator.calculator_state import CalculatorState
from calculator.columns import CURRENCY_SHEET_NAME, DATA_END_ROW, DATA_START_ROW, KALK_SHEET_NAME
from calculator.currency_rates import normalize_currency_rates
from calculator.filename_sanitizer import calculation_workbook_filename
from calculator.validation import ensure_valid_calculator_state
from calculator.workbook_export_plan import (
    ExportSourceProvenance,
    WorkbookExportPlan,
    build_workbook_export_plan,
    ensure_workbook_export_capacity,
)
from calculator.workbook_date_metadata import CUSTOM_PROPERTY_NAME as DATE_CUSTOM_PROPERTY_NAME
from calculator.workbook_package_export import export_reference_workbook_package
from calculator.workbook_provenance import CUSTOM_PROPERTY_NAME, provenance_json
from calculator.workbook_template import load_calculation_template


@dataclass(frozen=True)
class WorkbookExport:
    """Generated workbook download payload with internal source lineage."""

    filename: str
    content: bytes
    source_provenance: tuple[ExportSourceProvenance, ...] = ()


def export_calculation_workbook(
    state: CalculatorState,
    template_path: str | Path | None = None,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> WorkbookExport:
    """Return a fast reference-package XLSX payload for calculator state."""

    active_rates = normalize_currency_rates(currency_rates)
    ensure_workbook_export_capacity(state)
    ensure_valid_calculator_state(state, active_rates)
    plan = build_workbook_export_plan(state, active_rates)
    package = export_reference_workbook_package(plan, template_path)
    return WorkbookExport(
        filename=calculation_workbook_filename(state.itinerary_name),
        content=package.content,
        source_provenance=plan.source_provenance,
    )


def save_calculation_workbook(
    state: CalculatorState,
    output_dir: str | Path,
    template_path: str | Path | None = None,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> Path:
    """Write the exported calculation workbook to a directory."""

    export = export_calculation_workbook(state, template_path, currency_rates=currency_rates)
    output_path = Path(output_dir) / export.filename
    output_path.write_bytes(export.content)
    return output_path


def build_calculation_workbook(
    state: CalculatorState,
    template_path: str | Path | None = None,
    *,
    currency_rates: Mapping[str, float] | None = None,
) -> Workbook:
    """Render the canonical export plan through openpyxl.

    The package renderer is the production download path. This renderer remains
    as an intentional compatibility and parity-check API for callers that need
    a mutable :class:`openpyxl.Workbook`.
    """

    active_rates = normalize_currency_rates(currency_rates)
    ensure_workbook_export_capacity(state)
    ensure_valid_calculator_state(state, active_rates)
    plan = build_workbook_export_plan(state, active_rates)
    workbook = load_calculation_template(template_path)
    _apply_export_plan(workbook, plan)
    _apply_source_provenance(workbook, plan)
    _apply_date_metadata(workbook, plan)
    _restore_excel_advanced_view(workbook[KALK_SHEET_NAME])
    return workbook


def _apply_export_plan(workbook: Workbook, plan: WorkbookExportPlan) -> None:
    currency_sheet = workbook[CURRENCY_SHEET_NAME]
    calculator_sheet = workbook[KALK_SHEET_NAME]
    for cell in plan.currency_cells:
        currency_sheet[cell.reference] = cell.value
    for cell in plan.calculator_cells:
        calculator_sheet[cell.reference] = cell.value

    for row_number in range(DATA_START_ROW, DATA_END_ROW + 1):
        calculator_sheet.row_dimensions[row_number].hidden = row_number > plan.visible_data_end_row

    properties = dict(plan.calculation_properties)
    workbook.calculation.calcMode = str(properties["calcMode"])
    workbook.calculation.fullCalcOnLoad = bool(properties["fullCalcOnLoad"])
    workbook.calculation.forceFullCalc = bool(properties["forceFullCalc"])



def _apply_source_provenance(workbook: Workbook, plan: WorkbookExportPlan) -> None:
    existing = next((prop for prop in workbook.custom_doc_props if prop.name == CUSTOM_PROPERTY_NAME), None)
    if existing is not None:
        workbook.custom_doc_props.props.remove(existing)
    if plan.source_provenance:
        workbook.custom_doc_props.append(
            StringProperty(name=CUSTOM_PROPERTY_NAME, value=provenance_json(plan.source_provenance))
        )


def _apply_date_metadata(workbook: Workbook, plan: WorkbookExportPlan) -> None:
    existing = next((prop for prop in workbook.custom_doc_props if prop.name == DATE_CUSTOM_PROPERTY_NAME), None)
    if existing is not None:
        workbook.custom_doc_props.props.remove(existing)
    if plan.date_metadata_json:
        workbook.custom_doc_props.append(
            StringProperty(name=DATE_CUSTOM_PROPERTY_NAME, value=plan.date_metadata_json)
        )


def _restore_excel_advanced_view(sheet: object) -> None:
    """Keep the template's grouped hidden columns expandable in Excel."""

    sheet.sheet_view.showOutlineSymbols = True
