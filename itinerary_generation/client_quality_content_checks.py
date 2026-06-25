"""Meaning, activity-support and timing checks for client output."""

from typing import Any, Mapping
from itinerary_generation.client_text_decisions import is_weak_journey_arc_phrase
from itinerary_generation.generation_quality_gate import BLOCKING, ItineraryValidationIssue
from itinerary_generation.quality_gate_patterns import SUPPLIER_TIME_WARNING_RE


def meta_lines_with_time_warnings(document: Any) -> list[str]:
    findings = []
    for day in getattr(document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            for meta in getattr(block, "meta", []) or []:
                label, value = str(getattr(meta, "label", "") or ""), str(getattr(meta, "value", "") or "")
                if "time" in label.lower() and SUPPLIER_TIME_WARNING_RE.search(value): findings.append(f"{getattr(day, 'day', '')} / {getattr(block, 'title', '')}: {value}")
    return findings


def journey_arc_phrase_issues(document: Any) -> list[ItineraryValidationIssue]:
    issues = []
    for row in getattr(getattr(document, "summary", None), "journey_arc", []) or []:
        chapter = str(row.get("chapter", "") or "") if isinstance(row, Mapping) else str(getattr(row, "chapter", "") or "")
        experience = row.get("experience", "") if isinstance(row, Mapping) else getattr(row, "experience", "")
        if is_weak_journey_arc_phrase(experience): issues.append(ItineraryValidationIssue(BLOCKING, "weak_journey_arc_meaning", "Journey Arc contains generic logistics filler instead of a destination, route, or real experience.", context=f"{chapter}: {experience}"))
    return issues


def bare_activity_blocks(document: Any) -> list[str]:
    findings = []
    for day in getattr(document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            if str(getattr(block, "kind", "") or "") != "activity": continue
            title = str(getattr(block, "title", "") or "").strip()
            if title and not (getattr(block, "includes", None) or str(getattr(block, "description", "") or "").strip() or getattr(block, "notable_sights", None) or getattr(block, "extra_sections", None)): findings.append(f"{getattr(day, 'day', '')}: {title}")
    return findings
