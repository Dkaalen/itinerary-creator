"""Presentation helpers for the Streamlit workflow shell.

The functions in this module deliberately keep business logic out of the UI.
They only translate existing session state into display-ready workflow data.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Mapping, Sequence

from itinerary_generation.common import get_row_type, group_rows_by_day, is_optional_row


@dataclass(frozen=True)
class WorkflowStep:
    number: int
    title: str
    eyebrow: str
    description: str
    status: str
    helper: str

    @property
    def css_status(self) -> str:
        return self.status.lower().replace(" ", "-")


_STATUS_LABELS = {
    "complete": "Complete",
    "active": "Current",
    "locked": "Locked",
    "attention": "Review",
}


def _session_get(session_state: Mapping[str, Any] | Any, key: str, default: Any = None) -> Any:
    if isinstance(session_state, Mapping):
        return session_state.get(key, default)
    getter = getattr(session_state, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(session_state, key, default)


def build_workflow_steps(session_state: Mapping[str, Any] | Any) -> list[WorkflowStep]:
    """Build display-only workflow steps from current project state."""

    parsed_rows = _session_get(session_state, "parsed_rows", []) or []
    output_edits = _session_get(session_state, "output_edits", {}) or {}
    has_rows = bool(parsed_rows)
    has_text = bool(output_edits)
    has_html = bool(_session_get(session_state, "itinerary_html", ""))
    pictures_added = bool(output_edits.get("pictures_added"))
    pdf_status = str(_session_get(session_state, "pdf_status", "Not created") or "Not created")
    validation_report = _session_get(session_state, "itinerary_validation_report", None)
    is_blocked = bool(getattr(validation_report, "is_blocked", False))

    return [
        WorkflowStep(
            1,
            "Input",
            "Supplier data",
            "Paste or load the raw itinerary rows.",
            "complete" if has_rows else "active",
            f"{len(parsed_rows)} rows parsed" if has_rows else "Waiting for supplier rows",
        ),
        WorkflowStep(
            2,
            "Structure Review",
            "Route, dates, services",
            "Check the generated trip structure before styling.",
            "attention" if is_blocked else ("complete" if has_rows else "locked"),
            "Structure created" if has_rows and not is_blocked else ("Resolve blockers" if is_blocked else "Available after input"),
        ),
        WorkflowStep(
            3,
            "Client Text",
            "Narrative and polish",
            "Review trip title, day copy, inclusions and notes.",
            "complete" if has_text else ("locked" if not has_rows else "active"),
            "Client wording ready" if has_text else ("Generate first" if not has_rows else "Ready to review"),
        ),
        WorkflowStep(
            4,
            "Image Review",
            "Destination imagery",
            "Add pictures and approve image matches before export.",
            "complete" if pictures_added else ("active" if has_text else "locked"),
            "Pictures active" if pictures_added else ("Add pictures when text is ready" if has_text else "Available after text"),
        ),
        WorkflowStep(
            5,
            "Preview",
            "Client-facing layout",
            "Inspect the exact final preview before PDF creation.",
            "complete" if has_html else ("locked" if not has_text else "active"),
            "Preview prepared" if has_html else ("Build the itinerary first" if not has_text else "Preview will refresh automatically"),
        ),
        WorkflowStep(
            6,
            "Export",
            "PDF delivery",
            "Create the final PDF after fatal export checks are clear.",
            "complete" if pdf_status == "Ready" else ("active" if has_html else "locked"),
            "PDF ready" if pdf_status == "Ready" else pdf_status,
        ),
    ]


def completed_step_count(steps: Sequence[WorkflowStep]) -> int:
    return sum(1 for step in steps if step.status == "complete")


def workflow_progress_percent(steps: Sequence[WorkflowStep]) -> int:
    if not steps:
        return 0
    return round(completed_step_count(steps) / len(steps) * 100)


def _unique_destinations(parsed_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    destinations: list[str] = []
    for row in parsed_rows:
        city = str(row.get("city", "")).strip()
        if city and city not in destinations:
            destinations.append(city)
    return destinations


def build_project_metrics(parsed_rows: Sequence[Mapping[str, Any]], output_edits: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return consultant-facing metrics for the UI dashboard."""

    parsed_rows = list(parsed_rows or [])
    grouped_days = group_rows_by_day(parsed_rows) if parsed_rows else {}
    destinations = _unique_destinations(parsed_rows)
    activities = [row for row in parsed_rows if get_row_type(row) == "Activity" and not is_optional_row(row)]
    hotels = [row for row in parsed_rows if get_row_type(row) == "Hotel" and not is_optional_row(row)]
    transfers = [
        row
        for row in parsed_rows
        if get_row_type(row) in {"Transfer", "Flight", "Train", "Ferry", "Cruise", "Rental Car"}
        and not is_optional_row(row)
    ]
    optional_rows = [row for row in parsed_rows if is_optional_row(row)]

    return {
        "days": len(grouped_days),
        "destinations": len(destinations),
        "destination_names": destinations,
        "activities": len(activities),
        "hotels": len(hotels),
        "transfers": len(transfers),
        "optional_rows": len(optional_rows),
        "pictures_added": bool((output_edits or {}).get("pictures_added")),
    }


def project_title(output_edits: Mapping[str, Any] | None, default: str = "New itinerary") -> str:
    value = str((output_edits or {}).get("trip_title", "")).strip()
    return value or default


def project_route_label(metrics: Mapping[str, Any]) -> str:
    destinations = list(metrics.get("destination_names", []) or [])
    if not destinations:
        return "No route detected yet"
    if len(destinations) <= 3:
        return " → ".join(destinations)
    return f"{destinations[0]} → {destinations[1]} → {destinations[2]} + {len(destinations) - 3} more"


def workflow_steps_html(steps: Sequence[WorkflowStep]) -> str:
    """Return Streamlit-safe HTML for the workflow cards.

    Keep this fragment compact and unindented. Streamlit renders ``st.markdown``
    through Markdown first, and indented sibling ``<div>`` blocks can be
    interpreted as code blocks. The compact output also works cleanly with
    ``st.html``.
    """

    cards = []
    for step in steps:
        status_label = _STATUS_LABELS.get(step.status, step.status.title())
        cards.append(
            ''.join(
                [
                    f'<div class="workflow-step-card workflow-step-{escape(step.css_status)}">',
                    '<div class="workflow-step-topline">',
                    f'<span class="workflow-step-number">{step.number}</span>',
                    f'<span class="workflow-status-pill">{escape(status_label)}</span>',
                    '</div>',
                    f'<div class="workflow-step-title">{escape(step.title)}</div>',
                    f'<div class="workflow-step-eyebrow">{escape(step.eyebrow)}</div>',
                    f'<div class="workflow-step-description">{escape(step.description)}</div>',
                    f'<div class="workflow-step-helper">{escape(step.helper)}</div>',
                    '</div>',
                ]
            )
        )
    return f'<div class="workflow-step-grid">{"".join(cards)}</div>'


def metric_card_html(label: str, value: Any, helper: str = "") -> str:
    """Return compact HTML so cards never fall back to Markdown code blocks."""

    helper_html = f'<div class="metric-card-helper">{escape(str(helper))}</div>' if helper else ""
    return ''.join(
        [
            '<div class="metric-card">',
            f'<div class="metric-card-label">{escape(label)}</div>',
            f'<div class="metric-card-value">{escape(str(value))}</div>',
            helper_html,
            '</div>',
        ]
    )
