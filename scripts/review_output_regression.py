"""Review real generated output for known product-quality regressions."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_parser import parse_itinerary

DEFAULT_FIXTURE = ROOT / "tests/fixtures/real_inputs/norway_sub_brain_sample.txt"


def _day_text(day: Any) -> str:
    parts = [getattr(day, "title", ""), getattr(day, "intro", "")]
    for block in getattr(day, "blocks", []) or []:
        parts.extend([getattr(block, "title", ""), getattr(block, "description", "")])
    return "\n".join(str(part or "") for part in parts)


def review_fixture(path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    rows = parse_itinerary(path.read_text(encoding="utf-8"))
    grouped = group_rows_by_day(rows)
    context = build_itinerary_render_context(rows, grouped, {"output_brand": "booknordics_customer"})
    days = {day.day: day for day in context.render_document.days}
    full_text = "\n".join(_day_text(day) for day in context.render_document.days)
    issues: list[str] = []

    if context.trip_title == "Western Norway Scenic Escape" or "Western Norway" in context.trip_title:
        issues.append("trip_title_mislabels_tromso_route")
    if "3/4-star hotel" not in full_text:
        issues.append("hotel_star_range_missing")
    if re.search(r"(?<!3/)\b4-star hotel\b", full_text):
        issues.append("uncertain_hotel_star_range_upgraded")
    if days.get("Day 4") and getattr(days["Day 4"], "title", "") != "Arrival in Tromsø & Northern Lights Cruise":
        issues.append("mixed_travel_activity_title_wrong")
    day5_text = _day_text(days.get("Day 5")) if days.get("Day 5") else ""
    if "rest of the day is open" in day5_text.lower():
        issues.append("multi_activity_day_false_open_time")
    if "between arranged experiences" not in day5_text:
        issues.append("multi_activity_gap_not_explained")
    if any(bad in full_text for bad in ("Date dependant", "Funicual", "Profesional", "Free wifi")):
        issues.append("supplier_cleanup_regression")

    return {
        "fixture": str(path.relative_to(ROOT)),
        "trip_title": context.trip_title,
        "trip_subtitle": context.trip_subtitle,
        "day_titles": {key: getattr(day, "title", "") for key, day in days.items()},
        "issue_count": len(issues),
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    paths = [Path(arg) for arg in (argv if argv is not None else sys.argv[1:])]
    reports = [review_fixture(path if path.is_absolute() else ROOT / path) for path in (paths or [DEFAULT_FIXTURE])]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 1 if any(report["issue_count"] for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
