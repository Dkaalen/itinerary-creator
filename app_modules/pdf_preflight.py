"""Pure PDF preflight checks for the export workflow.

The export screen needs one simple decision: can the user create the PDF now?
This module keeps that decision separate from advisory review metadata.  Issues
with severity ``critical`` are true export blockers; issues with severity
``review`` are advisory and must not block PDF creation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from itinerary_generation.itinerary_health_checks import build_itinerary_health_issues
from ui.picture_workflow import pictures_are_added


@dataclass(frozen=True)
class PdfPreflightIssue:
    code: str
    severity: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PdfPreflightReport:
    status_label: str
    issues: tuple[PdfPreflightIssue, ...]

    @property
    def blocking_issues(self) -> tuple[PdfPreflightIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "critical")

    @property
    def advisory_issues(self) -> tuple[PdfPreflightIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "review")

    @property
    def critical_count(self) -> int:
        return len(self.blocking_issues)

    @property
    def blocking_count(self) -> int:
        return self.critical_count

    @property
    def review_count(self) -> int:
        return len(self.advisory_issues)

    @property
    def advisory_count(self) -> int:
        return self.review_count

    @property
    def can_export(self) -> bool:
        return self.critical_count == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "status_label": self.status_label,
            "issues": [issue.as_dict() for issue in self.issues],
            "blocking_issues": [issue.as_dict() for issue in self.blocking_issues],
            "advisory_issues": [issue.as_dict() for issue in self.advisory_issues],
        }


def _issue(code: str, severity: str, message: str) -> PdfPreflightIssue:
    return PdfPreflightIssue(code=code, severity=severity, message=message)




def _warning_value(warning: Any, key: str, default: str = "") -> str:
    if isinstance(warning, Mapping):
        return str(warning.get(key, default) or default)
    return str(getattr(warning, key, default) or default)


def _client_warning_preflight_severity(warning: Any) -> str:
    severity = _warning_value(warning, "severity", "review").lower()
    code = _warning_value(warning, "code", "client_output_warning").lower()
    if severity in {"critical", "error", "blocking"}:
        return "critical"
    if code in {"client_price_or_currency_leak", "client_raw_supplier_fragment", "raw_supplier_fragment"}:
        return "critical"
    return "review"


def build_pdf_preflight_report(
    state: Mapping[str, Any],
    image_status: Mapping[str, Any] | None = None,
) -> PdfPreflightReport:
    image_status = image_status or {}
    issues: list[PdfPreflightIssue] = []

    if not state.get("itinerary_html") or not state.get("parsed_rows"):
        issues.append(_issue("missing_document", "critical", "Generate an itinerary before exporting."))

    output_edits = state.get("output_edits") or {}
    if not pictures_are_added(output_edits):
        issues.append(_issue("missing_pictures", "critical", "Add destination pictures before creating the PDF."))

    if not image_bank_is_ready_for_client_pictures(image_status):
        issues.append(_issue("image_bank_missing", "critical", "Connect the real destination image bank before creating the PDF."))

    for health_issue in build_itinerary_health_issues(
        state.get("parsed_rows", []) or [],
        parser_diagnostics=state.get("parser_diagnostics", []) or [],
    ):
        if health_issue.severity == "critical":
            issues.append(_issue(health_issue.code, "critical", health_issue.message))
        elif health_issue.severity == "review":
            issues.append(_issue(health_issue.code, "review", health_issue.message))

    latest_warnings = state.get("latest_client_output_warnings", [])
    if not latest_warnings and isinstance(output_edits, Mapping):
        # Backward compatibility for older saved projects. New editor payloads
        # keep derived warning metadata out of durable output_edits so render
        # cache signatures stay stable.
        latest_warnings = (output_edits or {}).get("latest_client_output_warnings", [])
    for warning in latest_warnings[:8]:
        message = _warning_value(warning, "message", str(warning)).strip()
        if message:
            issues.append(_issue(_warning_value(warning, "code", "client_output_warning") or "client_output_warning", _client_warning_preflight_severity(warning), message))

    seen: set[tuple[str, str]] = set()
    unique: list[PdfPreflightIssue] = []
    for issue in issues:
        key = (issue.code, issue.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)

    if any(issue.severity == "critical" for issue in unique):
        status = "Blocked"
    elif any(issue.severity == "review" for issue in unique):
        status = "Warnings"
    else:
        status = "Clear"
    return PdfPreflightReport(status_label=status, issues=tuple(unique))
