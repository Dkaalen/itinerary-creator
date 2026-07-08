"""Parse/render real Excel candidates into review snapshots."""

from __future__ import annotations

from typing import Any, Sequence

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from scripts.real_excel_fixture_bank import ExcelFixtureCandidate
from scripts.real_output_qa.models import CandidateOutputReview, CandidateRenderError, CandidateRenderResult, DayOutputSnapshot, OutputTextIssue, OutputTextScore
from scripts.real_output_qa.scoring import score_rendered_output
from scripts.real_output_qa.segments import optional_addon_line
from scripts.real_output_qa.text_utils import clean_text as _clean_text, clip as _clip

def render_candidate(candidate: ExcelFixtureCandidate) -> CandidateRenderResult:
    try:
        rows = normalize_itinerary_rows(parse_itinerary(candidate.raw_text))
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
        optional_addons=tuple(optional_addon_line(item) for item in getattr(context, "optional_addons", []) or () if optional_addon_line(item)),
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




__all__ = ["render_candidate", "render_candidate_review"]
