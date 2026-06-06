"""Structural quality gate for parsed itinerary rows.

The app can tolerate imperfect supplier wording, but it must not silently
produce a structurally unsafe itinerary.  This module contains the conservative
checks that protect the preview/PDF pipeline from architecture-level failures:
rows leaking into optional add-ons, route/duration truncation, and missing main
itinerary content.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from itinerary_generation.day_grouping_utils import get_day_number
from itinerary_generation.row_filters import get_commercial_status, get_row_type, is_optional_row


IMPORTANT_ROW_TYPES = {
    "Hotel",
    "Activity",
    "Transfer",
    "Train",
    "Flight",
    "Cruise",
    "Ferry",
    "Transport",
    "Arrival",
    "Departure",
    "Day Overview",
}

BLOCKING = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ItineraryValidationIssue:
    """A single validation finding for the parsed itinerary model."""

    severity: str
    code: str
    message: str
    context: str = ""


@dataclass(frozen=True)
class ItineraryQualitySnapshot:
    """Small deterministic summary used by safety checks and tests."""

    row_count: int
    important_count: int
    main_count: int
    optional_count: int
    self_arranged_count: int
    excluded_count: int
    input_max_day: int
    main_max_day: int
    optional_max_day: int
    input_cities: tuple[str, ...] = field(default_factory=tuple)
    main_cities: tuple[str, ...] = field(default_factory=tuple)
    optional_cities: tuple[str, ...] = field(default_factory=tuple)

    @property
    def optional_ratio(self) -> float:
        if not self.important_count:
            return 0.0
        return self.optional_count / self.important_count


@dataclass(frozen=True)
class ItineraryQualityGateReport:
    """Validation report returned by the structural quality gate."""

    snapshot: ItineraryQualitySnapshot
    issues: tuple[ItineraryValidationIssue, ...] = field(default_factory=tuple)

    @property
    def blocking_issues(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == BLOCKING)

    @property
    def warnings(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == WARNING)

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocking_issues)


def _as_rows(rows: Iterable[dict] | None) -> list[dict]:
    return [row for row in rows or [] if isinstance(row, dict)]


def _max_day(rows: Iterable[dict]) -> int:
    values = [get_day_number(row.get("day", "")) for row in rows]
    return max(values) if values else 0


def _is_important_row(row: dict) -> bool:
    row_type = get_row_type(row)
    raw_type = row.get("type", "")
    return row_type in IMPORTANT_ROW_TYPES or raw_type in IMPORTANT_ROW_TYPES


def _important_rows(rows: Iterable[dict]) -> list[dict]:
    return [row for row in rows if _is_important_row(row)]


def _ordered_cities(rows: Iterable[dict]) -> tuple[str, ...]:
    cities: list[str] = []
    seen: set[str] = set()
    for row in rows:
        city = str(row.get("city", "")).strip()
        if city and city not in seen:
            seen.add(city)
            cities.append(city)
    return tuple(cities)


def build_quality_snapshot(parsed_rows) -> ItineraryQualitySnapshot:
    """Return stable row/day/status metrics for the parsed itinerary."""
    rows = _as_rows(parsed_rows)
    important_rows = _important_rows(rows)
    main_rows = [row for row in important_rows if not is_optional_row(row)]
    optional_rows = [row for row in important_rows if is_optional_row(row)]
    self_arranged_rows = [row for row in important_rows if get_commercial_status(row) == "self_arranged"]
    excluded_rows = [row for row in important_rows if get_commercial_status(row) == "excluded"]

    return ItineraryQualitySnapshot(
        row_count=len(rows),
        important_count=len(important_rows),
        main_count=len(main_rows),
        optional_count=len(optional_rows),
        self_arranged_count=len(self_arranged_rows),
        excluded_count=len(excluded_rows),
        input_max_day=_max_day(important_rows),
        main_max_day=_max_day(main_rows),
        optional_max_day=_max_day(optional_rows),
        input_cities=_ordered_cities(important_rows),
        main_cities=_ordered_cities(main_rows),
        optional_cities=_ordered_cities(optional_rows),
    )


def _validate_snapshot(snapshot: ItineraryQualitySnapshot) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []

    if snapshot.important_count and not snapshot.main_count:
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "no_main_itinerary_rows",
                "No included itinerary rows were available after parsing. Review row types and optional/add-on classification.",
            )
        )
        return issues

    if snapshot.input_max_day and snapshot.main_max_day and snapshot.input_max_day - snapshot.main_max_day >= 2:
        if snapshot.optional_max_day > snapshot.main_max_day:
            issues.append(
                ItineraryValidationIssue(
                    BLOCKING,
                    "main_itinerary_truncated_by_optional_rows",
                    (
                        f"Input reaches Day {snapshot.input_max_day}, but the included itinerary only reaches Day {snapshot.main_max_day}. "
                        "Later rows were classified as optional. Review optional/add-on classification before generating the PDF."
                    ),
                    context=f"optional_max_day={snapshot.optional_max_day}",
                )
            )

    if snapshot.optional_count and snapshot.optional_ratio >= 0.45 and snapshot.optional_max_day > snapshot.main_max_day:
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "too_many_late_optional_rows",
                (
                    f"{snapshot.optional_count} of {snapshot.important_count} important rows are optional and optional rows extend beyond the included itinerary. "
                    "This usually means optional status leaked from supplier text."
                ),
                context=f"optional_ratio={snapshot.optional_ratio:.2f}",
            )
        )

    if snapshot.input_cities and snapshot.main_cities:
        missing_main_cities = [city for city in snapshot.input_cities if city not in snapshot.main_cities and city not in snapshot.optional_cities]
        if missing_main_cities:
            issues.append(
                ItineraryValidationIssue(
                    WARNING,
                    "unclassified_destination_rows",
                    "Some destination rows were not classified into included or optional itinerary buckets: "
                    + ", ".join(missing_main_cities)
                    + ".",
                )
            )

    if snapshot.optional_count >= 4 and snapshot.optional_ratio >= 0.30:
        issues.append(
            ItineraryValidationIssue(
                WARNING,
                "large_optional_share",
                (
                    f"{snapshot.optional_count} of {snapshot.important_count} important rows are optional. "
                    "Check that optional add-ons are intentional and not leaked from supplier text."
                ),
                context=f"optional_ratio={snapshot.optional_ratio:.2f}",
            )
        )

    return issues


def evaluate_itinerary_quality(parsed_rows) -> ItineraryQualityGateReport:
    """Run the structural itinerary safety gate."""
    snapshot = build_quality_snapshot(parsed_rows)
    issues = tuple(_validate_snapshot(snapshot))
    return ItineraryQualityGateReport(snapshot=snapshot, issues=issues)


def validate_itinerary_integrity(parsed_rows) -> list[ItineraryValidationIssue]:
    """Compatibility wrapper returning just the validation issues."""
    return list(evaluate_itinerary_quality(parsed_rows).issues)


def blocking_validation_messages(parsed_rows) -> list[str]:
    return [issue.message for issue in evaluate_itinerary_quality(parsed_rows).blocking_issues]


# Client-output quality gate -------------------------------------------------

FORBIDDEN_CLIENT_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("forbidden_aurora_wording", r"\bAurora\b", "Use 'Northern Lights' in client-facing output."),
    ("forbidden_onward_flight", r"\bOnward\s+flight\b", "Use grounded destination or route wording."),
    ("forbidden_onward_travel", r"\bOnward\s+travel\b", "Use grounded destination or route wording."),
    ("weak_journey_arc_flight_connection", r"\bFlight\s+connection\b", "Use destination welcome wording when only a flight/check-in happens."),
    ("weak_journey_arc_travel_connection", r"\b(?:Scenic\s+)?Travel\s+connection\b", "Use the actual route or destination, not generic connection filler."),
    ("weak_onward_train", r"\bonward\s+train\b", "Describe the real experience or route, not 'onward train'."),
    ("weak_onward_connection", r"\bonward\s+connections?\b", "Describe the real destination or route instead of generic onward connections."),
    ("weak_travel_continues", r"\bTravel\s+continues\b", "Use destination welcome wording or a grounded route description."),
    ("supplier_parenthetical_unlimited", r"\(\s*unlimited\s*\)", "Remove supplier parenthetical '(unlimited)'."),
    ("supplier_parenthetical_if_snow", r"\(\s*if\s+snow\s*\)", "Remove supplier parenthetical '(if snow)'."),
    ("rough_airport_wording", r"\bto\s+Airport\b", "Use 'to the airport' or a named airport."),
)

SUPPLIER_TIME_WARNING_RE = re.compile(
    r"\b(?:before\s+departure|bring\s+warm\s+clothes|please\s+arrive|meeting\s+point|"
    r"voucher|subject\s+to|pick[-\s]?up\s+window|\d+\s*(?:min\.?|minutes?)\s+before)\b",
    flags=re.IGNORECASE,
)

RAW_SUPPLIER_FIELD_RE = re.compile(
    r"\b(?:what[’']?s\s+included|what\s+to\s+expect|booking\s+information|"
    r"please\s+note|important\s+information|supplier\s+note|operator\s+note)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ClientOutputQualityGateReport:
    """Validation report for generated client-facing render output."""

    issues: tuple[ItineraryValidationIssue, ...] = field(default_factory=tuple)

    @property
    def blocking_issues(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == BLOCKING)

    @property
    def warnings(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == WARNING)

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocking_issues)


def _append_text(parts: list[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            parts.append(value)
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _append_text(parts, item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _append_text(parts, item)
        return
    # Dataclasses/typed render objects expose useful public attributes.
    for name in getattr(value, "__dataclass_fields__", {}) or {}:
        _append_text(parts, getattr(value, name, None))


def render_document_text(render_document: Any) -> str:
    """Flatten generated render output for late client-quality validation."""

    parts: list[str] = []
    _append_text(parts, render_document)
    return "\n".join(parts)




def raw_supplier_scan_text(render_document: Any) -> str:
    """Flatten only client prose that should never contain raw supplier headings.

    Legitimate app-owned final-section titles such as "What’s included" are not
    leaks; supplier headings are leaks when they survive inside day blocks, meta
    values, descriptions, bullets, or custom paragraph content.
    """

    parts: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        _append_text(parts, getattr(day, "title", ""))
        _append_text(parts, getattr(day, "intro", ""))
        for block in getattr(day, "blocks", []) or []:
            _append_text(parts, getattr(block, "title", ""))
            _append_text(parts, getattr(block, "meta", []))
            _append_text(parts, getattr(block, "includes", []))
            _append_text(parts, getattr(block, "description", ""))
            _append_text(parts, getattr(block, "notable_sights", []))
            _append_text(parts, getattr(block, "lines", []))
            _append_text(parts, getattr(block, "extra_sections", []))
    for section in getattr(render_document, "final_sections", []) or []:
        for page in getattr(section, "pages", []) or []:
            _append_text(parts, getattr(page, "items", []))
            _append_text(parts, getattr(page, "paragraphs", []))
            _append_text(parts, getattr(page, "content_html", ""))
            for page_section in getattr(page, "sections", []) or []:
                _append_text(parts, getattr(page_section, "items", []))
    return "\n".join(parts)


def _meta_lines_with_time_warnings(render_document: Any) -> list[str]:
    findings: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            for meta in getattr(block, "meta", []) or []:
                label = str(getattr(meta, "label", "") or "")
                value = str(getattr(meta, "value", "") or "")
                if "time" in label.lower() and SUPPLIER_TIME_WARNING_RE.search(value):
                    findings.append(f"{getattr(day, 'day', '')} / {getattr(block, 'title', '')}: {value}")
    return findings


def _bare_activity_blocks(render_document: Any) -> list[str]:
    findings: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            if str(getattr(block, "kind", "") or "") != "activity":
                continue
            title = str(getattr(block, "title", "") or "").strip()
            has_supporting_text = bool(
                getattr(block, "includes", None)
                or str(getattr(block, "description", "") or "").strip()
                or getattr(block, "notable_sights", None)
                or getattr(block, "extra_sections", None)
            )
            if title and not has_supporting_text:
                findings.append(f"{getattr(day, 'day', '')}: {title}")
    return findings


def _image_payload_is_default(match: Mapping[str, Any]) -> bool:
    if bool(match.get("is_default") or match.get("is_generic")):
        return True
    city = str(match.get("city", "") or "").strip().lower()
    filename = str(match.get("filename", "") or "").strip().lower()
    path = str(match.get("path", "") or "").replace("\\", "/").lower()
    return city in {"default", "defoult"} or "/default/" in path or filename.startswith("default_")


def _image_match_issues(day_images: Mapping[str, Mapping[str, Any] | None] | None) -> list[ItineraryValidationIssue]:
    issues: list[ItineraryValidationIssue] = []
    for day, match in (day_images or {}).items():
        if not isinstance(match, Mapping) or not _image_payload_is_default(match):
            continue
        audit = match.get("audit") if isinstance(match.get("audit"), Mapping) else {}
        stronger_available = bool(match.get("stronger_candidate_available") or audit.get("stronger_candidate_available"))
        if stronger_available:
            issues.append(
                ItineraryValidationIssue(
                    BLOCKING,
                    "default_image_used_despite_stronger_match",
                    "Default image was selected even though a stronger image-bank match was available.",
                    context=str(day),
                )
            )
    return issues


def _image_bank_status_issues(image_bank_status: Mapping[str, Any] | None) -> list[ItineraryValidationIssue]:
    if not isinstance(image_bank_status, Mapping):
        return []
    missing = bool(
        image_bank_status.get("missing_full_bank")
        or image_bank_status.get("default_only")
        or image_bank_status.get("is_default_only")
        or not image_bank_status.get("full_bank_found", image_bank_status.get("using_full_destination_bank", False))
    )
    if not missing:
        return []
    message = str(
        image_bank_status.get("blocking_message")
        or "Full destination image bank is missing; default-only picture selection cannot be approved."
    )
    return [
        ItineraryValidationIssue(
            BLOCKING,
            "image_bank_full_missing",
            message,
            context=str(image_bank_status.get("source_path") or image_bank_status.get("paths") or ""),
        )
    ]


def evaluate_client_output_quality(
    render_document: Any,
    *,
    day_images: Mapping[str, Mapping[str, Any] | None] | None = None,
    image_bank_status: Mapping[str, Any] | None = None,
) -> ClientOutputQualityGateReport:
    """Validate final generated client output after parsing/normalization."""

    issues: list[ItineraryValidationIssue] = []
    text = render_document_text(render_document)

    for code, pattern, message in FORBIDDEN_CLIENT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            issues.append(ItineraryValidationIssue(BLOCKING, code, message))

    if RAW_SUPPLIER_FIELD_RE.search(raw_supplier_scan_text(render_document)):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "raw_supplier_field_leak",
                "Raw supplier section labels leaked into generated client output.",
            )
        )

    for context in _meta_lines_with_time_warnings(render_document):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "supplier_warning_in_time_field",
                "Supplier warning text leaked into a Time field.",
                context=context,
            )
        )

    for context in _bare_activity_blocks(render_document):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "bare_activity_inclusion_heading",
                "Activity block has a heading but no supporting client-facing text.",
                context=context,
            )
        )

    issues.extend(_image_match_issues(day_images))
    issues.extend(_image_bank_status_issues(image_bank_status))
    return ClientOutputQualityGateReport(issues=tuple(issues))


def blocking_client_output_messages(render_document: Any, **kwargs: Any) -> list[str]:
    return [issue.message for issue in evaluate_client_output_quality(render_document, **kwargs).blocking_issues]
