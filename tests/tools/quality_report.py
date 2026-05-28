"""Generate a pessimistic quality report for all real itinerary fixtures."""
from __future__ import annotations

import sys
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    class _SessionState(dict):
        def __getattr__(self, name):
            return self.get(name)
    streamlit_stub.session_state = _SessionState()
    streamlit_stub.error = lambda *args, **kwargs: None
    streamlit_stub.exception = lambda *args, **kwargs: None
    sys.modules["streamlit"] = streamlit_stub

from app_modules.itinerary_html import build_itinerary_html
from generator import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.content_validator import FixtureQualityReport, validate_html, extract_day_summaries
import ui.day_pages as day_pages


def render_fixture(fixture: Path) -> FixtureQualityReport:
    raw = fixture.read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    day_pages.select_day_images_with_overrides = lambda grouped_days, output_edits=None: {}
    day_pages.render_day_image_slot = lambda *args, **kwargs: ""
    html = build_itinerary_html(rows, grouped, output_edits={})
    return FixtureQualityReport(
        fixture_name=fixture.name,
        day_count=len(grouped),
        row_count=len(rows),
        findings=validate_html(html),
        day_summaries=extract_day_summaries(html),
    )


def main() -> int:
    fixtures = sorted((ROOT / "tests" / "fixtures" / "real_inputs").glob("*.txt"))
    reports = [render_fixture(fixture) for fixture in fixtures]
    for report in reports:
        status = "PASS" if report.passed else "FAIL"
        print(f"{status} {report.fixture_name}: {report.day_count} days, {report.row_count} parsed rows")
        for summary in report.day_summaries[:3]:
            print(f"  {summary}")
        if len(report.day_summaries) > 3:
            print(f"  ... {len(report.day_summaries) - 3} more day summaries")
        for finding in report.findings:
            print(f"  - {finding.code}: {finding.context}")
    failures = [report for report in reports if not report.passed]
    if failures:
        print(f"\n{len(failures)} fixture(s) failed the quality gate.")
        return 1
    print(f"\nAll {len(reports)} real fixtures passed the HTML quality scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
