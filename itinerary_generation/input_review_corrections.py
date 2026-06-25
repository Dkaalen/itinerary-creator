"""Safe correction actions for structured input review."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from itinerary_generation.destination_registry import destination_for_alias
from itinerary_generation.input_review_helpers import _rows, _text
from itinerary_generation.input_review_models import StructuredInputCorrectionAction


def _canonical_destination_name(value: str) -> str:
    record = destination_for_alias(value)
    return record.name if record else str(value or "").strip()


def _correction_field_updates(row: Mapping[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    declared_type = _text(row, "type")
    effective_type = _text(row, "effective_type")
    if declared_type and effective_type and declared_type != effective_type:
        updates["type"] = effective_type

    for key in ("city", "destination", "route_origin", "route_destination", "from", "to"):
        value = _text(row, key)
        if not value:
            continue
        canonical = _canonical_destination_name(value)
        if canonical and canonical != value and destination_for_alias(value) is not None:
            updates[key] = canonical
    return updates


def build_input_correction_actions(
    rows: Iterable[Mapping[str, Any]] | None,
) -> tuple[StructuredInputCorrectionAction, ...]:
    """Return safe, explicit correction actions for parsed supplier rows."""

    actions: list[StructuredInputCorrectionAction] = []
    for index, row in enumerate(_rows(rows), start=1):
        updates = _correction_field_updates(row)
        if not updates:
            continue
        labels: list[str] = []
        declared_type = _text(row, "type")
        effective_type = _text(row, "effective_type")
        if declared_type and effective_type and declared_type != effective_type:
            labels.append(f"type {declared_type} → {effective_type}")
        destination_updates = [key for key in updates if key != "type"]
        if destination_updates:
            labels.append("destination spelling")
        action_label = "Accept parser fix: " + ", ".join(labels)
        actions.append(
            StructuredInputCorrectionAction(
                row_number=index,
                action_type="safe_parser_fix",
                action_label=action_label,
                safe_auto_apply=True,
                field_updates=updates,
                reason="Parser-normalized row type or destination alias can be accepted safely.",
            )
        )
    return tuple(actions)


def apply_input_correction_actions(
    rows: Iterable[Mapping[str, Any]] | None,
    actions: Iterable[StructuredInputCorrectionAction | Mapping[str, Any]] | None = None,
    *,
    row_numbers: Iterable[int] | None = None,
) -> tuple[list[dict[str, Any]], tuple[StructuredInputCorrectionAction, ...]]:
    """Apply selected safe input corrections to parsed rows."""

    normalized_rows = _rows(rows)
    available_actions = tuple(
        action if isinstance(action, StructuredInputCorrectionAction) else StructuredInputCorrectionAction(**dict(action))
        for action in (actions or build_input_correction_actions(normalized_rows))
    )
    selected = set(int(number) for number in row_numbers) if row_numbers is not None else None
    applied: list[StructuredInputCorrectionAction] = []
    by_row = {action.row_number: action for action in available_actions if action.safe_auto_apply}
    for index, row in enumerate(normalized_rows, start=1):
        if selected is not None and index not in selected:
            continue
        action = by_row.get(index)
        if not action:
            continue
        for key, value in action.field_updates.items():
            row[key] = value
        row.setdefault("accepted_input_corrections", [])
        if isinstance(row["accepted_input_corrections"], list):
            row["accepted_input_corrections"].append(action.action_label)
        applied.append(action)
    return normalized_rows, tuple(applied)
