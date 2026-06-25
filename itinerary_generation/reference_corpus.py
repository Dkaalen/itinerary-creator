"""Versioned reference corpus loaders and data-quality diagnostics.

The corpus is intentionally read-only and is not consulted by the production
parser yet.  It supplies stable source material for characterization tests and
future domain work without creating a second runtime source of truth.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import hashlib
import re
from typing import Iterable

from itinerary_generation.reference_corpus_loaders import (
    CORPUS_ROOT,
    CORPUS_VERSION,
    SCHEMA_VERSION,
    clean_activity_references,
    iceland_reference_payload,
    reference_corpus_manifest,
    standard_input_templates,
)
from itinerary_generation.reference_corpus_models import (
    CleanActivityReference,
    ReferenceCorpusIssue,
    ReferenceCorpusSummary,
    StandardInputTemplate,
)

_ALLOWED_STANDARD_TYPES = frozenset({"Hotel", "Leisure", "Transfer", "Flight", "Cruise", "Train", "Coach"})
_ALLOWED_PLACEHOLDERS = frozenset({"X", "HotelName", "RoomCategory", "BedType", "MealPlan", "Destination", "Time"})
_EXPECTED_ICELAND_SHEETS = frozenset(
    f"{days}D {kind}"
    for kind in ("SD", "GTS", "GTW")
    for days in (5, 6, 7, 8, 10)
)
_EXPECTED_GROUP_TYPES = frozenset(
    {
        "Arrival",
        "Transfer",
        "Hotel",
        "Leisure",
        "Activity",
        "Group Tour",
        "Departure",
        "Transfer package",
        "Activity Upgrade",
        "Single Supplement Fee",
        "Extra Hotel Night",
        "x",
    }
)
_EXPECTED_SELF_DRIVE_TYPES = frozenset(
    {"Arrival", "Car", "Drive", "Hotel", "Leisure", "Departure", "Activity Upgrade", "Extra Hotel Night", "x"}
)
_PLACEHOLDER_RE = re.compile(r"\[([^\[\]]+)\]")
_ACTIVITY_PREFIX_RE = re.compile(r"^\s*([^:]+?)\s*:")
_TIME_FIELD_RE = re.compile(r"\bTime\s*:\s*(.*?)(?=\s+-\s+(?:Meeting point|Includes|Description|Note)\s*:|$)", re.I | re.S)
_CLOCK_RE = re.compile(r"(?<!\d)(\d{1,2})(?::\s*(\d{2}))?\s*(am|pm)(?!\w)", re.I)
_PACKAGE_DAY_RE = re.compile(r"^\s*Day\s*(\d+)\b", re.I)
_DAY_LABEL_RE = re.compile(r"^\s*Day\s*(\d+)\s*$", re.I)
_SPACE_RE = re.compile(r"\s+")


def _normalized(value: str) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip().lower())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def destination_capability_map() -> dict[str, frozenset[str]]:
    capabilities: dict[str, set[str]] = defaultdict(set)
    for entry in standard_input_templates():
        capabilities[entry.canonical_destination].add(entry.service_type)
    return {destination: frozenset(types) for destination, types in capabilities.items()}


def unresolved_placeholders(value: str) -> tuple[str, ...]:
    """Return unresolved bracket placeholders found in client-facing text."""

    return tuple(dict.fromkeys(match.strip() for match in _PLACEHOLDER_RE.findall(str(value or ""))))


def _issue(code: str, severity: str, corpus: str, record_id: str, message: str) -> ReferenceCorpusIssue:
    return ReferenceCorpusIssue(code=code, severity=severity, corpus=corpus, record_id=record_id, message=message)


def _validate_standard_templates(entries: Iterable[StandardInputTemplate]) -> list[ReferenceCorpusIssue]:
    issues: list[ReferenceCorpusIssue] = []
    seen: set[tuple[str, str, str]] = set()
    required_by_type = {
        "Hotel": {"X", "HotelName", "RoomCategory", "BedType", "MealPlan"},
        "Leisure": set(),
        "Transfer": {"Destination"},
        "Flight": {"Destination", "Time"},
        "Cruise": {"Destination", "Time"},
        "Train": {"Destination", "Time"},
        "Coach": {"Destination", "Time"},
    }
    for entry in entries:
        if entry.service_type not in _ALLOWED_STANDARD_TYPES:
            issues.append(_issue("unsupported_standard_service_type", "error", "standard_templates", entry.record_id, entry.service_type))
        if not entry.source_destination or not entry.canonical_destination:
            issues.append(_issue("missing_standard_destination", "error", "standard_templates", entry.record_id, "Destination is blank"))
        prefix_match = _ACTIVITY_PREFIX_RE.match(entry.template_text)
        if not prefix_match:
            issues.append(_issue("standard_template_missing_destination_prefix", "error", "standard_templates", entry.record_id, entry.template_text))
        elif _normalized(prefix_match.group(1)) != _normalized(entry.source_destination):
            issues.append(_issue("standard_template_destination_mismatch", "error", "standard_templates", entry.record_id, entry.template_text))
        unknown = set(entry.placeholders) - _ALLOWED_PLACEHOLDERS
        if unknown:
            issues.append(_issue("unknown_standard_placeholder", "error", "standard_templates", entry.record_id, ", ".join(sorted(unknown))))
        missing = required_by_type.get(entry.service_type, set()) - set(entry.placeholders)
        if missing:
            issues.append(_issue("missing_required_standard_placeholder", "error", "standard_templates", entry.record_id, ", ".join(sorted(missing))))
        key = (entry.service_type, entry.canonical_destination, _normalized(entry.template_text))
        if key in seen:
            issues.append(_issue("duplicate_standard_template", "warning", "standard_templates", entry.record_id, entry.template_text))
        seen.add(key)
    return issues


def _time_minutes(hour: int, minute: int, meridiem: str) -> int:
    hour %= 12
    if meridiem.lower() == "pm":
        hour += 12
    return hour * 60 + minute


def _activity_time_issues(entry: CleanActivityReference) -> list[ReferenceCorpusIssue]:
    issues: list[ReferenceCorpusIssue] = []
    match = _TIME_FIELD_RE.search(entry.activity_text)
    if not match:
        if _CLOCK_RE.search(entry.activity_text) and not re.search(r"\bDeparture from\b|\bDeparture\s+from\b", entry.activity_text, flags=re.I):
            issues.append(_issue("activity_missing_time_label", "warning", "clean_activities", entry.record_id, entry.activity_text))
        return issues
    time_text = match.group(1).strip()
    if re.search(r"\d{1,2}:\s+\d{2}\s*(?:am|pm)", time_text, flags=re.I):
        issues.append(_issue("malformed_activity_time_spacing", "warning", "clean_activities", entry.record_id, time_text))
    clocks = [(int(hour), int(minute or 0), meridiem.lower()) for hour, minute, meridiem in _CLOCK_RE.findall(time_text)]
    if (("/" in time_text and len(clocks) not in {2, 4}) or len(clocks) > 4
            or (len(clocks) == 4 and (time_text.count("/") != 2 or time_text.count("-") > 1))):
        issues.append(_issue("ambiguous_activity_time_options", "warning", "clean_activities", entry.record_id, time_text))
    if len(clocks) == 2:
        start = _time_minutes(*clocks[0])
        end = _time_minutes(*clocks[1])
        duration = end - start if end >= start else end + 24 * 60 - start
        overnight_signal = any(marker in entry.activity_text.lower() for marker in ("overnight", "next day", "unlimited", "stay"))
        if duration > 12 * 60 and not overnight_signal:
            issues.append(_issue("suspicious_activity_time_range", "warning", "clean_activities", entry.record_id, time_text))
    return issues


def _validate_clean_activities(entries: Iterable[CleanActivityReference]) -> list[ReferenceCorpusIssue]:
    issues: list[ReferenceCorpusIssue] = []
    seen: dict[tuple[str, str], str] = {}
    for entry in entries:
        if entry.record_type.lower() != "activity":
            issues.append(_issue("non_activity_reference_row", "error", "clean_activities", entry.record_id, entry.record_type))
        if not entry.source_city or not entry.activity_text:
            issues.append(_issue("incomplete_activity_reference", "error", "clean_activities", entry.record_id, "City or text is blank"))
        if unresolved_placeholders(entry.activity_text):
            issues.append(_issue("placeholder_in_clean_activity", "error", "clean_activities", entry.record_id, entry.activity_text))
        if not entry.activity_location:
            issues.append(_issue("activity_missing_location_prefix", "warning", "clean_activities", entry.record_id, entry.activity_text))
        elif entry.canonical_city and entry.canonical_activity_location and entry.canonical_city != entry.canonical_activity_location:
            issues.append(
                _issue(
                    "activity_location_differs_from_catalogue_city",
                    "warning",
                    "clean_activities",
                    entry.record_id,
                    f"{entry.source_city} -> {entry.activity_location}",
                )
            )
        key = (entry.canonical_city, _normalized(entry.activity_text))
        if key in seen:
            issues.append(
                _issue(
                    "duplicate_clean_activity",
                    "warning",
                    "clean_activities",
                    entry.record_id,
                    f"duplicates {seen[key]}",
                )
            )
        else:
            seen[key] = entry.record_id
        issues.extend(_activity_time_issues(entry))
    return issues


def _row_type_counts(sheet: dict) -> Counter[str]:
    return Counter(str(row.get("type", "")) for row in sheet.get("rows", []) if row.get("type"))


def _validate_iceland_reference(payload: dict) -> list[ReferenceCorpusIssue]:
    issues: list[ReferenceCorpusIssue] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("iceland_schema_version_mismatch", "error", "iceland", "payload", str(payload.get("schema_version"))))
    if payload.get("corpus_version") != CORPUS_VERSION:
        issues.append(_issue("iceland_corpus_version_mismatch", "error", "iceland", "payload", str(payload.get("corpus_version"))))
    sheets = payload.get("sheets") or []
    names = {sheet.get("sheet_name") for sheet in sheets}
    for missing in sorted(_EXPECTED_ICELAND_SHEETS - names):
        issues.append(_issue("missing_iceland_reference_sheet", "error", "iceland", missing, missing))
    for unexpected in sorted(names - _EXPECTED_ICELAND_SHEETS):
        issues.append(_issue("unexpected_iceland_reference_sheet", "error", "iceland", str(unexpected), str(unexpected)))

    for sheet in sheets:
        sheet_name = str(sheet.get("sheet_name") or "")
        kind = str(sheet.get("itinerary_kind") or "")
        season = str(sheet.get("season") or "")
        duration = int(sheet.get("duration_days") or 0)
        metadata_season = str((sheet.get("metadata") or {}).get("season") or "").lower()
        counts = _row_type_counts(sheet)
        rows = list(sheet.get("rows") or [])
        expected_types = _EXPECTED_SELF_DRIVE_TYPES if kind == "self_drive" else _EXPECTED_GROUP_TYPES
        unknown_types = set(counts) - expected_types
        if unknown_types:
            issues.append(_issue("unexpected_iceland_row_type", "error", "iceland", sheet_name, ", ".join(sorted(unknown_types))))
        if metadata_season and metadata_season not in {season, "all"}:
            issues.append(_issue("iceland_sheet_season_mismatch", "error", "iceland", sheet_name, f"{metadata_season} != {season}"))
        for row in rows:
            travel_element = str(row.get("travel_element") or "")
            placeholders = unresolved_placeholders(travel_element)
            if placeholders:
                issues.append(_issue("placeholder_in_iceland_reference", "error", "iceland", f"{sheet_name}:{row.get('excel_row')}", ", ".join(placeholders)))
        if kind == "self_drive":
            if counts.get("Drive", 0) != duration:
                issues.append(_issue("self_drive_day_count_mismatch", "error", "iceland", sheet_name, f"{counts.get('Drive', 0)} != {duration}"))
            if counts.get("Group Tour", 0):
                issues.append(_issue("group_tour_row_in_self_drive_sheet", "error", "iceland", sheet_name, str(counts.get("Group Tour"))))
        elif kind == "group_tour":
            expected_package_days = duration - 2
            if counts.get("Activity", 0) != 1:
                issues.append(_issue("group_tour_master_count_mismatch", "error", "iceland", sheet_name, str(counts.get("Activity", 0))))
            if counts.get("Group Tour", 0) != expected_package_days:
                issues.append(_issue("group_tour_day_count_mismatch", "error", "iceland", sheet_name, f"{counts.get('Group Tour', 0)} != {expected_package_days}"))
            group_rows = [row for row in rows if row.get("type") == "Group Tour"]
            package_days: list[int] = []
            itinerary_days: list[int] = []
            for row in group_rows:
                package_match = _PACKAGE_DAY_RE.match(str(row.get("travel_element") or ""))
                day_match = _DAY_LABEL_RE.match(str(row.get("day") or ""))
                if not package_match:
                    issues.append(_issue("group_tour_day_number_missing", "error", "iceland", f"{sheet_name}:{row.get('excel_row')}", str(row.get("travel_element") or "")))
                else:
                    package_days.append(int(package_match.group(1)))
                if day_match:
                    itinerary_days.append(int(day_match.group(1)))
            if package_days != list(range(1, expected_package_days + 1)):
                issues.append(_issue("group_tour_package_day_sequence_mismatch", "error", "iceland", sheet_name, str(package_days)))
            if itinerary_days != list(range(2, duration)):
                issues.append(_issue("group_tour_itinerary_day_sequence_mismatch", "error", "iceland", sheet_name, str(itinerary_days)))
            master_text = " ".join(str(row.get("travel_element") or "") for row in rows if row.get("type") == "Activity").lower()
            if season not in master_text:
                issues.append(_issue("group_tour_master_missing_season", "warning", "iceland", sheet_name, season))
    return issues


def _validate_manifest(manifest: dict) -> list[ReferenceCorpusIssue]:
    issues: list[ReferenceCorpusIssue] = []
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("corpus_version") != CORPUS_VERSION:
        issues.append(_issue("reference_manifest_version_mismatch", "error", "manifest", "manifest", str(manifest)))
    for file_record in manifest.get("files") or []:
        name = str(file_record.get("name") or "")
        path = CORPUS_ROOT / name
        if not path.exists():
            issues.append(_issue("reference_manifest_file_missing", "error", "manifest", name, name))
            continue
        if file_record.get("sha256") != _sha256(path):
            issues.append(_issue("reference_manifest_checksum_mismatch", "error", "manifest", name, name))
    return issues


@lru_cache(maxsize=1)
def validate_reference_corpus() -> tuple[ReferenceCorpusIssue, ...]:
    issues: list[ReferenceCorpusIssue] = []
    issues.extend(_validate_manifest(reference_corpus_manifest()))
    issues.extend(_validate_standard_templates(standard_input_templates()))
    issues.extend(_validate_clean_activities(clean_activity_references()))
    issues.extend(_validate_iceland_reference(iceland_reference_payload()))
    return tuple(issues)


def blocking_reference_corpus_issues() -> tuple[ReferenceCorpusIssue, ...]:
    return tuple(issue for issue in validate_reference_corpus() if issue.severity == "error")


def reference_corpus_summary() -> ReferenceCorpusSummary:
    iceland_payload = iceland_reference_payload()
    issues = validate_reference_corpus()
    return ReferenceCorpusSummary(
        version=CORPUS_VERSION,
        standard_template_count=len(standard_input_templates()),
        clean_activity_count=len(clean_activity_references()),
        iceland_sheet_count=len(iceland_payload.get("sheets") or []),
        iceland_row_count=sum(len(sheet.get("rows") or []) for sheet in iceland_payload.get("sheets") or []),
        issue_count=len(issues),
        blocking_issue_count=sum(issue.severity == "error" for issue in issues),
    )


def clear_reference_corpus_cache() -> None:
    standard_input_templates.cache_clear()
    clean_activity_references.cache_clear()
    iceland_reference_payload.cache_clear()
    reference_corpus_manifest.cache_clear()
    validate_reference_corpus.cache_clear()
