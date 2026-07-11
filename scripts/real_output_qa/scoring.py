"""Deterministic scoring checks for rendered itinerary text."""

from __future__ import annotations

import re
from typing import Any, Sequence

from generator import group_rows_by_day
from itinerary_generation.transport_domain.facts import build_transport_facts
from itinerary_generation.copy.phrase_guardrails import contains_banned_generated_phrase
from itinerary_generation.quality_gate import evaluate_client_output_quality
from itinerary_generation.quality_gate_patterns import SUSPICIOUS_AM_PM_TIME_RANGE_RE
from scripts.real_output_qa.models import OutputTextIssue, OutputTextScore, TextSegment
from scripts.real_output_qa.rules import (
    ACTIVITY_TRANSPORT_EXPERIENCE_RE,
    ACTIVITY_TYPE_RE,
    GENERIC_COPY_RE,
    RAW_SUPPLIER_FRAGMENT_RE,
    SUPPLIER_TYPO_PATTERNS,
    SUSPICIOUS_PHRASES,
    TRANSFER_AS_PLACE_RE,
    TRANSPORT_PRODUCT_RE,
    WEAK_ARRIVAL_INTRO_RE,
    WEAK_FREE_TIME_RE,
    MALFORMED_TIME_RE,
)
from scripts.real_output_qa.deep_quality_checks import score_journey_overview_logic, score_unsupported_intro_theme
from scripts.real_output_qa.destination_truth_checks import score_city_currency_safety, score_destination_truth
from scripts.real_output_qa.segments import iter_output_segments
from scripts.real_output_qa.summary_quality import score_summary_quality
from scripts.real_output_qa.text_utils import add_issue as _add_issue, clean_text as _clean_text

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
    score_city_currency_safety(issues, segments, getattr(context, "destinations_line", ""))
    score_destination_truth(issues, segments, getattr(context, "destinations_line", ""))
    score_summary_quality(issues, context)
    score_journey_overview_logic(issues, context)
    _score_client_truth_contracts(issues, context)
    _score_day_copy_logic(issues, rows, days)
    _score_transport_semantics(issues, rows, days)
    _score_repetition(issues, days)
    _score_style_density(issues, segments)

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    score = max(0, 100 - (error_count * 20) - (warning_count * 5))
    return OutputTextScore(score=score, error_count=error_count, warning_count=warning_count, issues=tuple(issues))




_TRUTH_GATE_CODES = {
    "internal_copy_leak",
    "unsupported_journey_overview_fact",
    "impossible_free_time_claim",
    "day_activity_title_disagreement",
    "false_return_visit",
    "duplicate_intro_and_leisure",
    "invalid_activity_time_range",
}

def _score_client_truth_contracts(issues: list[OutputTextIssue], context: Any) -> None:
    document = getattr(context, "render_document", None)
    if document is None:
        return
    report = evaluate_client_output_quality(document)
    for issue in report.issues:
        if issue.code not in _TRUTH_GATE_CODES:
            continue
        _add_issue(
            issues,
            issue.code,
            "error" if issue.severity == "blocking" else "warning",
            issue.message,
            location="client_truth_gate",
            excerpt=str(issue.context or ""),
        )

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
        if SUSPICIOUS_AM_PM_TIME_RANGE_RE.search(segment.text):
            _add_issue(
                issues,
                "suspicious_am_pm_time_range",
                "warning",
                "Suspicious 12 AM to PM time range needs source review before client delivery.",
                location=segment.location,
                excerpt=segment.text,
            )
        if MALFORMED_TIME_RE.search(segment.text):
            _add_issue(
                issues,
                "malformed_client_time",
                "error",
                "Client-facing time text is malformed by normalization.",
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
        intro = _clean_text(getattr(day, "intro", ""))
        labels = getattr(day, "labels", {}) or {}
        title_source = _clean_text(labels.get("title_decision_source")) if isinstance(labels, dict) else ""
        intro_source = _clean_text(labels.get("intro_decision_source")) if isinstance(labels, dict) else ""
        if intro_source == "admin_fallback_intro":
            _add_issue(
                issues,
                "intro_decision_used_admin_fallback",
                "error",
                "Intro decision fell through to admin-style fallback instead of a day-brain source.",
                location=f"{day_id}.intro_decision",
                excerpt=intro,
            )
        if activity_rows and title_source in {"last_resort_title_fallback", "stay_title_fallback", "narrow_inclusion_title"}:
            _add_issue(
                issues,
                "title_decision_used_weak_source",
                "error",
                "Activity day title came from a weak/fallback source instead of product, schedule, or intent truth.",
                location=f"{day_id}.title_decision",
                excerpt=f"{title_source}: {title}",
            )
        if activity_rows and "narrow_inclusion_title" in _clean_text(labels.get("title_decision_rejected_sources")) and title_source in {"activity_product_display_title", "supplier_activity_title", "composed_activity_title", "schedule_composed_activity_title"}:
            # This is the healthy state: the trace proves narrow included items
            # were considered but could not override the broader product/day title.
            pass
        if WEAK_ARRIVAL_INTRO_RE.search(intro):
            _add_issue(
                issues,
                "weak_arrival_intro",
                "error" if day_id == "Day 1" else "warning",
                "Arrival/stay intro uses admin-style fallback copy instead of client travel prose.",
                location=f"{day_id}.intro",
                excerpt=intro,
            )
        for block in getattr(day, "blocks", []) or ():
            if _clean_text(getattr(block, "kind", "")).casefold() == "leisure" and WEAK_FREE_TIME_RE.search(_clean_text(getattr(block, "description", ""))):
                _add_issue(
                    issues,
                    "weak_free_time_copy",
                    "warning",
                    "Free-time copy is too generic and should be context-aware.",
                    location=f"{day_id}.leisure",
                    excerpt=_clean_text(getattr(block, "description", "")),
                )
                break
        if title.casefold() == "fløibanen funicular" and any("walking tour" in _clean_text(row.get("original_title") or row.get("details")).casefold() for row in activity_rows):
            _add_issue(
                issues,
                "narrow_title_overrides_broader_product",
                "error",
                "Day title selected a narrow inclusion instead of the broader source product.",
                location=f"{day_id}.title",
                excerpt=title,
            )
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
        score_unsupported_intro_theme(issues, day_id, intro, day_rows)


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
            row_type = _clean_text(row.get("effective_type") or row.get("type") or row.get("source_type"))
            row_title = _clean_text(row.get("title") or row.get("original_title") or row.get("details"))
            transport_facts = build_transport_facts(row)
            if (
                ACTIVITY_TYPE_RE.search(row_type)
                and (transport_facts.mode or TRANSPORT_PRODUCT_RE.search(row_title))
                and not ACTIVITY_TRANSPORT_EXPERIENCE_RE.search(row_title)
            ):
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
            for warning in transport_facts.warnings:
                if warning in {"origin_looks_like_service_phrase", "destination_looks_like_service_phrase"}:
                    _add_issue(
                        issues,
                        "transport_fact_service_place",
                        "warning",
                        "Canonical transport facts found a service phrase where a place should be.",
                        location=day_id,
                        excerpt=transport_facts.display_route or row_title,
                    )
            source_type = _clean_text(row.get("source_type") or row.get("type"))
            if "actvity" in source_type.casefold() or "actvity" in row_title.casefold():
                _add_issue(
                    issues,
                    "typoed_activity_type_seen",
                    "error",
                    "Typoed activity row type/title needs classification cleanup.",
                    location=day_id,
                    excerpt=f"{source_type}: {row_title}",
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


def _score_style_density(issues: list[OutputTextIssue], segments: Sequence[TextSegment]) -> None:
    generic_hits: dict[str, list[TextSegment]] = {}
    intro_openers: dict[str, list[TextSegment]] = {}
    for segment in segments:
        text = _clean_text(segment.text)
        if not text:
            continue
        if GENERIC_COPY_RE.search(text):
            generic_hits.setdefault(segment.day or segment.location, []).append(segment)
        if segment.kind == "day_intro":
            opener = " ".join(re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", text.casefold())[:5])
            if opener:
                intro_openers.setdefault(opener, []).append(segment)
    if len(generic_hits) >= 3:
        first = next(iter(generic_hits.values()))[0]
        _add_issue(
            issues,
            "generic_copy_density",
            "warning",
            "Generic fallback copy appears on several days/sections in one itinerary.",
            location=first.location,
            excerpt=first.text,
        )
    for opener, matches in intro_openers.items():
        if len(matches) >= 3:
            _add_issue(
                issues,
                "repeated_intro_opener",
                "warning",
                "Several day intros start with the same wording pattern.",
                location=matches[-1].location,
                excerpt=f"{len(matches)} intros start with: {opener}",
            )
            break


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



__all__ = ["score_rendered_output"]
