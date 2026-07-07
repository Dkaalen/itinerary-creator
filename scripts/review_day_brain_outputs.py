"""Review day-brain copy against real fixture inputs.

This is a hosted-output reality-check proxy: it exercises the same parser,
grouping, visit-context, intro and leisure writers used by preview/PDF paths,
then emits a compact JSON report for manual review.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from itinerary_generation.copy.visit_context import build_day_visit_contexts
from itinerary_generation.day_copy_qa import find_day_copy_issues
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_leisure_writer import write_leisure_copy
from itinerary_generation.day_text import create_day_intro

DEFAULT_FIXTURES = (
    "tests/fixtures/real_inputs/finland_norway_autumn_alta.txt",
    "tests/fixtures/real_inputs/finland_norway_winter_family.txt",
    "tests/fixtures/real_inputs/norway_sweden_denmark_summer.txt",
    "tests/fixtures/real_inputs/scandinavia_autumn_cruise.txt",
)


def review_fixture(path: Path) -> dict:
    raw_text = path.read_text(encoding="utf-8")
    rows = parse_itinerary(raw_text)
    grouped = group_rows_by_day(rows)
    visit_contexts = build_day_visit_contexts(grouped)
    days: list[dict] = []
    for day, day_rows in grouped.items():
        visit_context = visit_contexts.get(str(day))
        facts = build_day_facts(day_rows, visit_context=visit_context)
        intent = classify_day_intent(facts)
        intro = create_day_intro(day_rows, visit_context=visit_context)
        leisure = write_leisure_copy(facts, intent)
        issues = find_day_copy_issues(facts=facts, intent=intent, intro=intro, leisure=leisure)
        days.append(
            {
                "day": str(day),
                "intent": str(intent),
                "main_city": facts.main_city,
                "travel_load": facts.travel_load.level,
                "accommodation": {
                    "tonight_city": facts.accommodation_state.tonight_city,
                    "same_city_change": facts.accommodation_state.same_city_change,
                    "new_city_change": facts.accommodation_state.new_city_change,
                },
                "visit_number": facts.visit_number,
                "intro": intro,
                "leisure": leisure,
                "issue_codes": [issue.code for issue in issues],
            }
        )
    return {"fixture": str(path), "day_count": len(days), "days": days}


def build_report(paths: tuple[str, ...] = DEFAULT_FIXTURES) -> list[dict]:
    return [review_fixture(ROOT / path) for path in paths]


if __name__ == "__main__":
    print(json.dumps(build_report(tuple(sys.argv[1:]) or DEFAULT_FIXTURES), ensure_ascii=False, indent=2))
