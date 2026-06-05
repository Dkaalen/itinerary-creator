import sys
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
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
from itinerary_generation.output_contract import (
    extract_output_layout_signature,
    validate_output_layout_contract,
)
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


def _html_from_raw(raw: str, output_edits=None) -> str:
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    return build_itinerary_html(rows, grouped, output_edits or {"days": {}, "pictures_added": False})


def test_output_layout_contract_preserves_client_page_order_for_issue_fixture():
    raw = """
Day 1	Transfer	27/10/2026		Helsinki	Private Airport to Hotel
Day 1	Hotel	27/10/2026	29/10/2026	Helsinki	Hotel Arthur, 2xNight, 1xStandard Double Room, Incl Breakfast
Day 2	Activity	28/10/2026		Helsinki	Excursion to Tallinn - Helsinki Port transfers included - Self guided tour of Old Town Tallinn - Time: 10:30 am - 07:30 pm
Day 2	Transfer	28/10/2026		Helsinki	Overnight Train : Overnight Train Transfer with the Santa Claus Express to Rovaniemi - 11:13 pm - 10:59 am - 1 x downstairs cabin for two people
Day 3	Hotel	29/10/2026	31/10/2026	Rovaniemi	Scandic Rovaniemi City, 2xNight, 1xStandard Double Room, Incl Breakfast
Day 3	Activity	29/10/2026		Rovaniemi	Rovaniemi: Northern Lights Unlimited Mileage Photo Tour | 20:00 | 5 Hrs | What's included? Pick-up/drop-off in central Rovaniemi Professional DSLR photography
Day 4	Activity	02/11/2026		Tromso	Round Trip Ticket: Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening.
Day 5	Activity	05/11/2026		Oslo	Oslo : Essential Oslo, City Center Guided Walking Tour | 10 AM | 2 Hrs
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    html = build_itinerary_html(rows, grouped, {"days": {}, "pictures_added": False})

    signature = extract_output_layout_signature(html)
    issues = validate_output_layout_contract(html, expected_day_count=len(grouped))

    assert not issues
    assert signature.page_types[:2] == ("cover", "summary")
    assert signature.day_count == len(grouped) == 5
    assert signature.included_page_count >= 1
    assert signature.not_included_page_count >= 1
    assert signature.final_page_titles[-1] == "Important travel notes"
    assert signature.final_page_titles.index("What’s included") < signature.final_page_titles.index("What’s not included")


def test_output_layout_contract_requires_final_list_structure():
    html = """
    <div class="preview-background">
      <div class="a4-page cover-page"></div>
      <div class="a4-page summary-page"></div>
      <div class="a4-page day-page single-day-page"></div>
      <div class="a4-page final-list-page categorized-inclusions-page">
        <div class="final-page-title">What’s included</div>
        <div class="content-block inclusion-category-block"><div class="section-title">Activities</div><ul><li>Guided walk</li></ul></div>
      </div>
      <div class="a4-page final-list-page categorized-exclusions-page">
        <div class="final-page-title">What’s not included</div>
        International flights unless specifically listed Self-arranged flights Travel insurance Meals unless specifically stated Personal expenses
      </div>
      <div class="a4-page final-list-page important-notes-page"><div class="final-page-title">Important travel notes</div><ul><li>Check vouchers.</li></ul></div>
    </div>
    """

    issues = validate_output_layout_contract(html, expected_day_count=1)
    codes = {issue.code for issue in issues}

    assert "whats_not_included_has_no_list_structure" in codes
    assert "collapsed_whats_not_included" in codes


def test_output_layout_contract_detects_day_count_drift():
    html = """
    <div class="a4-page cover-page"></div>
    <div class="a4-page summary-page"></div>
    <div class="a4-page day-page single-day-page"></div>
    <div class="a4-page final-list-page categorized-inclusions-page"><div class="final-page-title">What’s included</div><ul><li>A</li></ul></div>
    <div class="a4-page final-list-page categorized-exclusions-page"><div class="final-page-title">What’s not included</div><ul><li>B</li></ul></div>
    <div class="a4-page final-list-page important-notes-page"><div class="final-page-title">Important travel notes</div><ul><li>C</li></ul></div>
    """

    issues = validate_output_layout_contract(html, expected_day_count=2)

    assert any(issue.code == "day_page_count_mismatch" for issue in issues)
