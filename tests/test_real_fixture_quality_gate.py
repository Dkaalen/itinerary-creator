import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import types

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
from itinerary_generation.content_validator import compact_html, validate_html
from scripts.test_group_catalog.quality import REAL_FIXTURE_QUALITY_FILES

FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "real_inputs"
FIXTURES = tuple(FIXTURE_ROOT / name for name in REAL_FIXTURE_QUALITY_FILES)

SPECIFIC_CHECKS = {
    "iceland_group_tour_winter.txt": {
        "must_contain": ["Hvalfjörður", "Kirkjufell", "Pick-up: Between 8:00 AM and 8:30 AM"],
        "must_not_contain": ["Join a whale watching experience", "Join a guided glacier experience"],
    },
    "norway_finland_family_autumn.txt": {
        "must_contain": ["Self-arranged flight to Tromsø (not included)", "City Highlights & Suomenlinna Day Tour"],
        "must_not_contain": ["<li>Local</li>", "Duration:</span> 5–8 minutes"],
    },
    "iceland_self_drive_summer.txt": {
        "must_not_contain": ["CAR · DRIVE", "Destinations Keflavík · Reykjavík · Jökulsárlón · Car · Drive"],
    },
}

_MISSING = object()


def _restore_attr(module, name: str, value):
    if value is _MISSING:
        if hasattr(module, name):
            delattr(module, name)
    else:
        setattr(module, name, value)


def render_fixture_html_text(fixture_name: str) -> str:
    raw = (ROOT / "tests" / "fixtures" / "real_inputs" / fixture_name).read_text(encoding="utf-8")
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    import ui.day_pages as day_pages
    import ui.day_page_sections as day_page_sections

    original_day_pages_selector = getattr(day_pages, "select_day_images_with_overrides", _MISSING)
    original_day_pages_slot = getattr(day_pages, "render_day_image_slot", _MISSING)
    original_sections_selector = getattr(day_page_sections, "select_day_images_with_overrides", _MISSING)
    original_sections_slot = getattr(day_page_sections, "render_day_image_slot", _MISSING)
    try:
        day_pages.select_day_images_with_overrides = lambda grouped_days, output_edits=None: {}
        day_pages.render_day_image_slot = lambda *args, **kwargs: ""
        day_page_sections.select_day_images_with_overrides = lambda grouped_days, output_edits=None: {}
        day_page_sections.render_day_image_slot = lambda *args, **kwargs: ""
        return build_itinerary_html(rows, grouped, output_edits={})
    finally:
        _restore_attr(day_pages, "select_day_images_with_overrides", original_day_pages_selector)
        _restore_attr(day_pages, "render_day_image_slot", original_day_pages_slot)
        _restore_attr(day_page_sections, "select_day_images_with_overrides", original_sections_selector)
        _restore_attr(day_page_sections, "render_day_image_slot", original_sections_slot)


def fixture_quality_failures(fixture_name: str) -> list[str]:
    html = render_fixture_html_text(fixture_name)
    plain = compact_html(html)
    failures = [
        f"{fixture_name}: {finding.code}: {finding.context}"
        for finding in validate_html(html)
    ]
    checks = SPECIFIC_CHECKS.get(fixture_name, {})
    for required in checks.get("must_contain", []):
        if compact_html(required) not in plain:
            failures.append(f"{fixture_name}: missing required text {required!r}")
    for forbidden in checks.get("must_not_contain", []):
        has_forbidden = (
            forbidden in html
            if forbidden.startswith("<")
            else compact_html(forbidden) in plain or forbidden in html
        )
        if has_forbidden:
            failures.append(f"{fixture_name}: contains fixture-forbidden text {forbidden!r}")
    return failures


def assert_fixture_quality(fixture_name: str) -> None:
    failures = fixture_quality_failures(fixture_name)
    if failures:
        raise AssertionError("Real fixture quality gate failures:\n" + "\n".join(failures))


def test_real_fixture_global_quality_gate():
    missing = [fixture.name for fixture in FIXTURES if not fixture.exists()]
    if missing:
        raise AssertionError(f"Missing real fixture files: {missing}")
    failures = [
        failure
        for fixture in FIXTURES
        for failure in fixture_quality_failures(fixture.name)
    ]
    if failures:
        raise AssertionError("Real fixture quality gate failures:\n" + "\n".join(failures))


def _install_direct_fixture_checks() -> None:
    for fixture_name in REAL_FIXTURE_QUALITY_FILES:
        function_name = f"check_real_fixture_quality_{Path(fixture_name).stem.replace('-', '_')}"

        def _check(name: str = fixture_name) -> None:
            assert_fixture_quality(name)

        _check.__name__ = function_name
        _check.__qualname__ = function_name
        globals()[function_name] = _check


_install_direct_fixture_checks()
