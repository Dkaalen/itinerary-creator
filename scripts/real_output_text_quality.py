"""Shared real-output text review and scoring helpers.

The checks in this module are intentionally deterministic.  They are not meant
as style opinions; they surface client-facing text patterns that deserve a human
look before we trust a random real-Excel sample.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.copy.phrase_guardrails import contains_banned_generated_phrase
from itinerary_parser import parse_itinerary
from scripts.real_excel_fixture_bank import ExcelFixtureCandidate

CURRENCY_CODES = frozenset({"DKK", "EUR", "GBP", "ISK", "NOK", "SEK", "USD"})

SUPPLIER_TYPO_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"\bDate dependant\b", "date-dependent typo leaked", "error"),
    (r"\bFunicual\b", "funicular typo leaked", "error"),
    (r"\bProfesional\b", "professional typo leaked", "error"),
    (r"\bFree wifi\b", "WiFi capitalization typo leaked", "error"),
    (r"\baiport\b", "airport typo leaked", "error"),
    (r"\bdoulbe\b", "double typo leaked", "error"),
    (r"\bmilage\b", "mileage typo leaked", "error"),
    (r"\bActvity\b", "activity typo leaked", "error"),
    (r"\bCentraly\b", "centrally typo leaked", "warning"),
    (r"\bGuest Hose\b", "guest house typo leaked", "warning"),
)

SUSPICIOUS_PHRASES: tuple[str, ...] = (
    "unhurried",
    "the day’s arrangements are listed below",
    "the day's arrangements are listed below",
    "planned experience in",
)

RAW_SUPPLIER_FRAGMENT_RE = re.compile(
    r"\s-\s(?:Time|Meeting point|End point|Duration|Departure from|Departing from|Arrival|Start time):",
    flags=re.IGNORECASE,
)
TRANSFER_AS_PLACE_RE = re.compile(
    r"\b(?:travel|transfer|shuttle transfer)\s+from\s+(?:shuttle transfer|self transfer)\b",
    flags=re.IGNORECASE,
)
TRANSPORT_PRODUCT_RE = re.compile(
    r"\b(?:coach|bus|shuttle|transfer|train|flight|ferry|cruise transfer|airport transfer|arctic route)\b",
    flags=re.IGNORECASE,
)
ACTIVITY_TYPE_RE = re.compile(r"\bactivity\b", flags=re.IGNORECASE)


@dataclass(frozen=True)
class TextSegment:
    """A small client-facing text unit with enough location data for reports."""

    location: str
    kind: str
    text: str
    day: str = ""


@dataclass(frozen=True)
class OutputTextIssue:
    code: str
    severity: str
    message: str
    location: str = ""
    excerpt: str = ""


@dataclass(frozen=True)
class OutputTextScore:
    score: int
    error_count: int
    warning_count: int
    issues: tuple[OutputTextIssue, ...] = ()

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issue_count": self.issue_count,
            "ok": self.ok,
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True)
class DayOutputSnapshot:
    day: str
    title: str
    city: str
    intro: str
    source_rows: tuple[str, ...] = ()
    transport: tuple[str, ...] = ()
    accommodation: tuple[str, ...] = ()
    activities: tuple[str, ...] = ()
    leisure: tuple[str, ...] = ()
    optional_experiences: tuple[str, ...] = ()
    other_blocks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateOutputReview:
    fixture: dict[str, Any]
    parsed_row_count: int
    rendered_day_count: int
    trip_title: str
    trip_subtitle: str
    route: str
    journey_arc: tuple[dict[str, str], ...] = ()
    days: tuple[DayOutputSnapshot, ...] = ()
    included: tuple[str, ...] = ()
    optional_addons: tuple[str, ...] = ()
    not_included: tuple[str, ...] = ()
    render_warnings: tuple[str, ...] = ()
    score: OutputTextScore = field(default_factory=lambda: OutputTextScore(score=0, error_count=1, warning_count=0))

    @property
    def ok(self) -> bool:
        return self.score.ok

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score"] = self.score.to_dict()
        data["ok"] = self.ok
        return data


@dataclass(frozen=True)
class CandidateRenderResult:
    candidate: ExcelFixtureCandidate
    rows: tuple[dict[str, Any], ...]
    grouped_rows: dict[str, list[dict[str, Any]]]
    context: Any


class CandidateRenderError(RuntimeError):
    """Raised when a fixture cannot be parsed or rendered for output review."""


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clip(value: str, *, limit: int = 180) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _add_issue(
    issues: list[OutputTextIssue],
    code: str,
    severity: str,
    message: str,
    *,
    location: str = "",
    excerpt: str = "",
) -> None:
    issues.append(OutputTextIssue(code=code, severity=severity, message=message, location=location, excerpt=_clip(excerpt)))


def render_candidate(candidate: ExcelFixtureCandidate) -> CandidateRenderResult:
    try:
        rows = parse_itinerary(candidate.raw_text)
    except Exception as exc:  # pragma: no cover - CLI defensive boundary
        raise CandidateRenderError(f"Parser crashed: {type(exc).__name__}: {exc}") from exc
    if not rows:
        raise CandidateRenderError("No itinerary rows parsed from fixture.")
    try:
        grouped = group_rows_by_day(rows)
        context = build_itinerary_render_context(rows, grouped, {"output_brand": "booknordics_customer"})
    except Exception as exc:  # pragma: no cover - CLI defensive boundary
        raise CandidateRenderError(f"Render context crashed: {type(exc).__name__}: {exc}") from exc
    return CandidateRenderResult(candidate=candidate, rows=tuple(rows), grouped_rows=grouped, context=context)


def render_candidate_review(candidate: ExcelFixtureCandidate) -> CandidateOutputReview:
    try:
        result = render_candidate(candidate)
    except CandidateRenderError as exc:
        score = OutputTextScore(
            score=0,
            error_count=1,
            warning_count=0,
            issues=(
                OutputTextIssue(
                    code="candidate_render_failed",
                    severity="error",
                    message=str(exc),
                    location=candidate.fixture_id,
                ),
            ),
        )
        return CandidateOutputReview(
            fixture=candidate.summary(),
            parsed_row_count=0,
            rendered_day_count=0,
            trip_title="",
            trip_subtitle="",
            route="",
            score=score,
        )

    context = result.context
    score = score_rendered_output(result.rows, context, source_text=candidate.raw_text, fixture_id=candidate.fixture_id)
    days = tuple(_build_day_snapshot(day, result.grouped_rows.get(str(getattr(day, "day", "")), [])) for day in getattr(context.render_document, "days", []) or [])
    return CandidateOutputReview(
        fixture=candidate.summary(),
        parsed_row_count=len(result.rows),
        rendered_day_count=len(days),
        trip_title=_clean_text(getattr(context, "trip_title", "")),
        trip_subtitle=_clean_text(getattr(context, "trip_subtitle", "")),
        route=_clean_text(getattr(context, "destinations_line", "") or getattr(context.render_document, "route", "")),
        journey_arc=tuple(dict(item) for item in getattr(context, "journey_arc", []) or ()),
        days=days,
        included=tuple(_clean_text(item) for item in getattr(context, "whats_included", []) or () if _clean_text(item)),
        optional_addons=tuple(_optional_addon_line(item) for item in getattr(context, "optional_addons", []) or () if _optional_addon_line(item)),
        not_included=tuple(_clean_text(item) for item in getattr(context, "whats_not_included", []) or () if _clean_text(item)),
        render_warnings=tuple(_clean_text(item) for item in getattr(context.render_document, "warnings", []) or () if _clean_text(item)),
        score=score,
    )


def _source_row_excerpt(row: dict[str, Any]) -> str:
    row_type = _clean_text(row.get("source_type") or row.get("type") or row.get("effective_type") or "Row")
    city = _clean_text(row.get("city") or "")
    title = _clean_text(row.get("title") or row.get("original_title") or row.get("details") or "")
    parts = [row_type]
    if city:
        parts.append(city)
    if title:
        parts.append(title)
    return _clip(" — ".join(parts), limit=220)


def _build_day_snapshot(day: Any, day_rows: Sequence[dict[str, Any]]) -> DayOutputSnapshot:
    transport: list[str] = []
    accommodation: list[str] = []
    activities: list[str] = []
    leisure: list[str] = []
    optional: list[str] = []
    other: list[str] = []
    for block in getattr(day, "blocks", []) or []:
        line = _block_line(block)
        if not line:
            continue
        kind = _clean_text(getattr(block, "kind", "")).casefold()
        if kind in {"travel_sequence", "transport", "transfer"}:
            transport.append(line)
        elif kind == "accommodation":
            accommodation.append(line)
        elif kind == "activity":
            activities.append(line)
        elif kind == "leisure":
            leisure.append(line)
        elif kind == "optional_experience":
            optional.append(line)
        else:
            other.append(line)
    return DayOutputSnapshot(
        day=_clean_text(getattr(day, "day", "")),
        title=_clean_text(getattr(day, "title", "")),
        city=_clean_text(getattr(day, "city", "")),
        intro=_clean_text(getattr(day, "intro", "")),
        source_rows=tuple(_source_row_excerpt(row) for row in day_rows[:8]),
        transport=tuple(transport),
        accommodation=tuple(accommodation),
        activities=tuple(activities),
        leisure=tuple(leisure),
        optional_experiences=tuple(optional),
        other_blocks=tuple(other),
        warnings=tuple(_clean_text(item) for item in getattr(day, "warnings", []) or () if _clean_text(item)),
    )


def _block_line(block: Any) -> str:
    parts: list[str] = []
    section = _clean_text(getattr(block, "section_title", ""))
    title = _clean_text(getattr(block, "title", ""))
    description = _clean_text(getattr(block, "description", ""))
    lines = [_clean_text(item) for item in getattr(block, "lines", []) or () if _clean_text(item)]
    includes = [_clean_text(item) for item in getattr(block, "includes", []) or () if _clean_text(item)]
    meta = [f"{_clean_text(getattr(item, 'label', ''))}: {_clean_text(getattr(item, 'value', ''))}" for item in getattr(block, "meta", []) or ()]
    meta = [item for item in meta if not item.startswith(":") and item.split(":", 1)[-1].strip()]
    if section:
        parts.append(section)
    if title:
        parts.append(title)
    if lines:
        parts.append("; ".join(lines))
    if description:
        parts.append(description)
    if meta:
        parts.append("; ".join(meta))
    if includes:
        parts.append("Includes: " + "; ".join(includes[:4]))
    return _clip(" — ".join(parts), limit=420)


def _optional_addon_line(item: Any) -> str:
    if isinstance(item, dict):
        day = _clean_text(item.get("day"))
        title = _clean_text(item.get("title"))
        city = _clean_text(item.get("city"))
        description = _clean_text(item.get("description"))
        includes = [_clean_text(value) for value in item.get("includes", []) or () if _clean_text(value)]
        parts = [part for part in (day, city, title, description) if part]
        if includes:
            parts.append("Includes: " + "; ".join(includes[:4]))
        return _clip(" — ".join(parts), limit=420)
    return _clip(str(item), limit=420)


def iter_output_segments(context: Any) -> tuple[TextSegment, ...]:
    segments: list[TextSegment] = []
    render_document = getattr(context, "render_document", None)
    _append_segment(segments, "cover.trip_title", "trip_title", getattr(context, "trip_title", ""))
    _append_segment(segments, "cover.trip_subtitle", "trip_subtitle", getattr(context, "trip_subtitle", ""))
    _append_segment(segments, "cover.route", "route", getattr(context, "destinations_line", "") or getattr(render_document, "route", ""))
    for index, arc in enumerate(getattr(context, "journey_arc", []) or (), start=1):
        if isinstance(arc, dict):
            _append_segment(segments, f"journey_arc[{index}]", "journey_arc", " · ".join(_clean_text(value) for value in arc.values() if _clean_text(value)))
    for index, item in enumerate(getattr(context, "whats_included", []) or (), start=1):
        _append_segment(segments, f"included[{index}]", "included", item)
    for index, item in enumerate(getattr(context, "optional_addons", []) or (), start=1):
        _append_segment(segments, f"optional_addons[{index}]", "optional_addon", _optional_addon_line(item))
    for index, item in enumerate(getattr(context, "whats_not_included", []) or (), start=1):
        _append_segment(segments, f"not_included[{index}]", "not_included", item)
    for day in getattr(render_document, "days", []) or ():
        day_id = _clean_text(getattr(day, "day", ""))
        _append_segment(segments, f"{day_id}.title", "day_title", getattr(day, "title", ""), day=day_id)
        _append_segment(segments, f"{day_id}.city", "day_city", getattr(day, "city", ""), day=day_id)
        _append_segment(segments, f"{day_id}.intro", "day_intro", getattr(day, "intro", ""), day=day_id)
        for block_index, block in enumerate(getattr(day, "blocks", []) or (), start=1):
            block_kind = _clean_text(getattr(block, "kind", "block")) or "block"
            base = f"{day_id}.{block_kind}[{block_index}]"
            _append_segment(segments, f"{base}.section", f"{block_kind}_section", getattr(block, "section_title", ""), day=day_id)
            _append_segment(segments, f"{base}.title", f"{block_kind}_title", getattr(block, "title", ""), day=day_id)
            _append_segment(segments, f"{base}.description", f"{block_kind}_description", getattr(block, "description", ""), day=day_id)
            for line_index, line in enumerate(getattr(block, "lines", []) or (), start=1):
                _append_segment(segments, f"{base}.line[{line_index}]", f"{block_kind}_line", line, day=day_id)
            for include_index, include in enumerate(getattr(block, "includes", []) or (), start=1):
                _append_segment(segments, f"{base}.include[{include_index}]", f"{block_kind}_include", include, day=day_id)
            for meta_index, meta in enumerate(getattr(block, "meta", []) or (), start=1):
                _append_segment(
                    segments,
                    f"{base}.meta[{meta_index}]",
                    f"{block_kind}_meta",
                    f"{_clean_text(getattr(meta, 'label', ''))}: {_clean_text(getattr(meta, 'value', ''))}",
                    day=day_id,
                )
    return tuple(segments)


def _append_segment(segments: list[TextSegment], location: str, kind: str, text: object, *, day: str = "") -> None:
    cleaned = _clean_text(text)
    if cleaned:
        segments.append(TextSegment(location=location, kind=kind, text=cleaned, day=day))


def rendered_output_text(context: Any) -> str:
    return "\n".join(segment.text for segment in iter_output_segments(context))


def score_rendered_output(
    rows: Sequence[dict[str, Any]],
    context: Any,
    *,
    source_text: str = "",
    fixture_id: str = "",
) -> OutputTextScore:
    issues: list[OutputTextIssue] = []
    segments = iter_output_segments(context)
    full_text = "\n".join(segment.text for segment in segments)
    days = tuple(getattr(getattr(context, "render_document", None), "days", []) or ())

    if not days:
        _add_issue(issues, "no_rendered_days", "error", "Render context produced no days.", location=fixture_id)
    if not _clean_text(getattr(context, "trip_title", "")):
        _add_issue(issues, "missing_trip_title", "error", "Trip title is empty.", location="cover.trip_title")
    if not _clean_text(getattr(context, "trip_subtitle", "")):
        _add_issue(issues, "missing_trip_subtitle", "warning", "Trip subtitle is empty.", location="cover.trip_subtitle")

    _score_segment_text(issues, segments)
    _score_hotel_star_safety(issues, source_text, full_text)
    _score_city_currency_safety(issues, segments, getattr(context, "destinations_line", ""))
    _score_day_copy_logic(issues, rows, days)
    _score_transport_semantics(issues, rows, days)
    _score_repetition(issues, days)

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    score = max(0, 100 - (error_count * 20) - (warning_count * 5))
    return OutputTextScore(score=score, error_count=error_count, warning_count=warning_count, issues=tuple(issues))


def _score_segment_text(issues: list[OutputTextIssue], segments: Sequence[TextSegment]) -> None:
    for segment in segments:
        if contains_banned_generated_phrase(segment.text):
            _add_issue(
                issues,
                "banned_generated_phrase",
                "error",
                "Generated output contains a banned weak phrase.",
                location=segment.location,
                excerpt=segment.text,
            )
        for pattern, label, severity in SUPPLIER_TYPO_PATTERNS:
            match = re.search(pattern, segment.text, flags=re.IGNORECASE)
            if match:
                _add_issue(
                    issues,
                    "supplier_typo_leaked",
                    severity,
                    f"Supplier typo leaked into output: {label}.",
                    location=segment.location,
                    excerpt=segment.text,
                )
        lowered = segment.text.casefold()
        for phrase in SUSPICIOUS_PHRASES:
            if phrase in lowered:
                _add_issue(
                    issues,
                    "suspicious_generated_phrase",
                    "warning",
                    f"Suspicious or generic phrase needs review: {phrase!r}.",
                    location=segment.location,
                    excerpt=segment.text,
                )
                break
        if segment.kind.startswith("optional") and RAW_SUPPLIER_FRAGMENT_RE.search(segment.text):
            _add_issue(
                issues,
                "raw_optional_supplier_blob",
                "warning",
                "Optional experience still contains supplier-style field blobs.",
                location=segment.location,
                excerpt=segment.text,
            )
        if TRANSFER_AS_PLACE_RE.search(segment.text):
            _add_issue(
                issues,
                "transfer_phrase_treated_as_place",
                "warning",
                "Transfer text appears to use a transfer phrase as a place name.",
                location=segment.location,
                excerpt=segment.text,
            )


def _score_hotel_star_safety(issues: list[OutputTextIssue], source_text: str, full_text: str) -> None:
    if "3/4-star" not in source_text:
        return
    if "3/4-star" in full_text:
        return
    if re.search(r"(?<!3/)\b4-star hotel\b", full_text, flags=re.IGNORECASE):
        _add_issue(
            issues,
            "uncertain_hotel_star_range_upgraded",
            "error",
            "3/4-star source was rendered as definite 4-star hotel.",
            excerpt="4-star hotel",
        )


def _score_city_currency_safety(issues: list[OutputTextIssue], segments: Sequence[TextSegment], route_text: object) -> None:
    route_parts = {part.strip().upper() for part in re.split(r"[·,>\-/]+", _clean_text(route_text)) if part.strip()}
    bad_route_codes = sorted(route_parts & CURRENCY_CODES)
    for code in bad_route_codes:
        _add_issue(issues, "currency_code_used_as_city", "error", "Currency code appears in route/destination line.", location="cover.route", excerpt=code)
    for segment in segments:
        if segment.kind == "day_city" and segment.text.upper() in CURRENCY_CODES:
            _add_issue(
                issues,
                "currency_code_used_as_day_city",
                "error",
                "Currency code appears as a day city.",
                location=segment.location,
                excerpt=segment.text,
            )


def _score_day_copy_logic(issues: list[OutputTextIssue], rows: Sequence[dict[str, Any]], days: Sequence[Any]) -> None:
    grouped_rows = group_rows_by_day(rows)
    seen_cities: set[str] = set()
    for day in days:
        day_id = _clean_text(getattr(day, "day", ""))
        day_rows = grouped_rows.get(day_id, [])
        activity_rows = [row for row in day_rows if _clean_text(row.get("effective_type") or row.get("type")).casefold() == "activity"]
        transfer_rows = [row for row in day_rows if _clean_text(row.get("effective_type") or row.get("type")).casefold() in {"transfer", "transport", "train", "flight", "ferry"}]
        day_text = _day_text(day)
        day_city = _clean_text(getattr(day, "city", ""))
        title = _clean_text(getattr(day, "title", ""))
        if day_city and day_city in seen_cities and title.casefold().startswith(f"welcome to {day_city}".casefold()):
            _add_issue(
                issues,
                "return_visit_welcome_title",
                "warning",
                "Return visit uses first-arrival welcome wording.",
                location=f"{day_id}.title",
                excerpt=title,
            )
        if day_city:
            seen_cities.add(day_city)
        if len(activity_rows) >= 2 and "rest of the day is open" in day_text.casefold():
            _add_issue(
                issues,
                "multi_activity_false_open_time",
                "error",
                "Multi-activity day says the rest of the day is open.",
                location=day_id,
                excerpt=day_text,
            )
        if activity_rows and re.search(r"\btoday is open for independent time\b", day_text, flags=re.IGNORECASE):
            _add_issue(
                issues,
                "activity_day_full_leisure_wording",
                "warning",
                "Day with arranged activity uses full-leisure wording.",
                location=day_id,
                excerpt=day_text,
            )
        if not activity_rows and not transfer_rows and re.search(r"\bremaining time\b", day_text, flags=re.IGNORECASE):
            _add_issue(
                issues,
                "full_leisure_day_remaining_time",
                "warning",
                "Full leisure day uses remaining-time wording.",
                location=day_id,
                excerpt=day_text,
            )
        _score_city_activity_mismatch(issues, day_id, day_text, activity_rows)


def _score_city_activity_mismatch(issues: list[OutputTextIssue], day_id: str, day_text: str, activity_rows: Sequence[dict[str, Any]]) -> None:
    if len({ _clean_text(row.get("city")) for row in activity_rows if _clean_text(row.get("city")) }) < 1:
        return
    # Catch obvious forms like "Walk through Rovaniemi with A Finntastic Walking Tour in Helsinki".
    match = re.search(r"\b(?:walk through|explore|discover|experience)\s+([^,.;]+?)\s+with\s+.+?\bin\s+([^,.;]+)", day_text, flags=re.IGNORECASE)
    if match:
        first_city = _clean_text(match.group(1))
        second_city = _clean_text(match.group(2)).rstrip(".")
        if first_city and second_city and first_city.casefold() != second_city.casefold():
            _add_issue(
                issues,
                "activity_city_mismatch",
                "warning",
                "Activity sentence appears to attach an activity to the wrong city.",
                location=day_id,
                excerpt=match.group(0),
            )


def _score_transport_semantics(issues: list[OutputTextIssue], rows: Sequence[dict[str, Any]], days: Sequence[Any]) -> None:
    grouped_rows = group_rows_by_day(rows)
    day_texts = {_clean_text(getattr(day, "day", "")): _day_text(day) for day in days}
    for day_id, day_rows in grouped_rows.items():
        for row in day_rows:
            row_type = _clean_text(row.get("source_type") or row.get("type") or row.get("effective_type"))
            row_title = _clean_text(row.get("title") or row.get("original_title") or row.get("details"))
            if ACTIVITY_TYPE_RE.search(row_type) and TRANSPORT_PRODUCT_RE.search(row_title):
                rendered = day_texts.get(day_id, "")
                if "planned experience" in rendered.casefold() or row_title.casefold() in rendered.casefold():
                    _add_issue(
                        issues,
                        "transport_product_rendered_as_activity",
                        "warning",
                        "Transport-like product is typed/rendered as an activity.",
                        location=day_id,
                        excerpt=row_title,
                    )
            if "actvity" in row_type.casefold() or "actvity" in row_title.casefold():
                _add_issue(
                    issues,
                    "typoed_activity_type_seen",
                    "error",
                    "Typoed activity row type/title needs classification cleanup.",
                    location=day_id,
                    excerpt=f"{row_type}: {row_title}",
                )


def _score_repetition(issues: list[OutputTextIssue], days: Sequence[Any]) -> None:
    seen_intros: dict[str, str] = {}
    for day in days:
        day_id = _clean_text(getattr(day, "day", ""))
        intro = _clean_text(getattr(day, "intro", ""))
        if len(intro) < 40:
            continue
        previous = seen_intros.get(intro.casefold())
        if previous:
            _add_issue(
                issues,
                "repeated_day_intro",
                "warning",
                "Day intro repeats another day exactly.",
                location=day_id,
                excerpt=f"Same as {previous}: {intro}",
            )
        else:
            seen_intros[intro.casefold()] = day_id


def _day_text(day: Any) -> str:
    parts = [_clean_text(getattr(day, "title", "")), _clean_text(getattr(day, "intro", ""))]
    for block in getattr(day, "blocks", []) or []:
        parts.extend(
            [
                _clean_text(getattr(block, "section_title", "")),
                _clean_text(getattr(block, "title", "")),
                _clean_text(getattr(block, "description", "")),
            ]
        )
        parts.extend(_clean_text(line) for line in getattr(block, "lines", []) or ())
    return "\n".join(part for part in parts if part)


def reviews_to_json(reviews: Sequence[CandidateOutputReview]) -> str:
    return json.dumps([review.to_dict() for review in reviews], ensure_ascii=False, indent=2)
