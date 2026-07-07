"""Fixture-backed reporting for daywise intro/leisure copy quality."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from itinerary_generation.day_copy_qa import find_day_copy_issues
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.day_text import create_day_intro


@dataclass(frozen=True)
class DayCopyAuditCase:
    case_id: str
    description: str
    rows: tuple[Mapping[str, Any], ...]
    expected_intent: str = ""
    legacy_risk: str = ""
    visit_context: object | None = None


@dataclass(frozen=True)
class DayCopyAuditResult:
    case_id: str
    description: str
    intent: str
    intro: str
    leisure: str
    issue_codes: tuple[str, ...]
    legacy_risk: str = ""


def audit_day_copy_case(case: DayCopyAuditCase) -> DayCopyAuditResult:
    facts = build_day_facts(case.rows, visit_context=case.visit_context)
    intent = classify_day_intent(facts)
    intro = create_day_intro(case.rows, visit_context=case.visit_context)
    leisure = write_leisure_copy(facts, intent)
    issues = find_day_copy_issues(facts=facts, intent=intent, intro=intro, leisure=leisure)
    return DayCopyAuditResult(
        case_id=case.case_id,
        description=case.description,
        intent=str(intent),
        intro=intro,
        leisure=leisure,
        issue_codes=tuple(issue.code for issue in issues),
        legacy_risk=case.legacy_risk,
    )


def audit_day_copy_cases(cases: Sequence[DayCopyAuditCase]) -> list[dict[str, Any]]:
    return [asdict(audit_day_copy_case(case)) for case in cases]


__all__ = ["DayCopyAuditCase", "DayCopyAuditResult", "audit_day_copy_case", "audit_day_copy_cases"]
