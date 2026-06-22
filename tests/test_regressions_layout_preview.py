import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _visual_editor_frontend_source() -> str:
    frontend = ROOT / "visual_editor_component" / "frontend"
    parts = [(frontend / "index.html").read_text(encoding="utf-8")]
    for relative in (
        "styles/editor.css",
        "js/state.js",
        "js/images.js",
        "js/render.js",
        "js/serialization.js",
        "js/editor_dirty_state.js",
            "js/editor_text_tools.js",
            "js/editor_document_model.js",
            "js/editor_inspector.js",
            "js/editor_page_actions.js",
            "js/editor_warnings.js",
            "js/commands.js",
        "js/editing.js",
        "js/streamlit_bridge.js",
    ):
        parts.append((frontend / relative).read_text(encoding="utf-8"))
    return "\n".join(parts)
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from regression_test_helpers import assert_equal, assert_contains, assert_not_contains

from text_polish import (
    expand_time_with_duration,
    polish_client_text,
    polish_hotel_name,
    format_duration_display,
)
from generator import (
    create_whats_included,
    create_journey_arc,
    group_rows_by_day,
    create_day_intro,
    create_trip_glance,
)
from itinerary_generation.titles import create_trip_subtitle
from itinerary_parser import extract_duration_from_description, parse_itinerary
from normalizer import normalize_itinerary_rows
from layout_policy import (
    DEFAULT_DAY_PAGE_LAYOUT,
    DAY_PAGE_LAYOUTS,
    normalize_day_page_layout,
    is_day_packing_enabled,
    is_three_day_packing_enabled,
)

def test_layout_policy_one_day_per_page():
    assert_equal(
        DEFAULT_DAY_PAGE_LAYOUT,
        "One day per page",
        "Visual layout should default to one day per A4 page.",
    )
    assert_equal(
        DAY_PAGE_LAYOUTS,
        ["One day per page"],
        "Only one-day-per-page layout should be exposed while image placement is active.",
    )
    assert_equal(
        normalize_day_page_layout("Smart compact pages"),
        "One day per page",
        "Legacy compact page settings should normalize to one-day-per-page.",
    )
    assert_equal(
        normalize_day_page_layout("3-days per page"),
        "One day per page",
        "Legacy 3-day page settings should normalize to one-day-per-page.",
    )
    assert_equal(
        is_day_packing_enabled("Smart compact pages"),
        False,
        "Day packing should be disabled for the v36 visual layout path.",
    )
    assert_equal(
        is_three_day_packing_enabled("3-days per page"),
        False,
        "Three-day packing should be disabled for the v36 visual layout path.",
    )


def test_day_page_editorial_parity_markup():
    from ui.day_pages import render_day_page

    rows = [{
        "day": "Day 3",
        "type": "Activity",
        "city": "Rovaniemi",
        "title": "Northern Lights Hunt",
        "description": "Northern Lights Hunt",
    }]
    html = render_day_page("Day 3", rows, image_match=None)
    assert_contains(html, "DAY 3", "Day pages should render the editorial day kicker.")
    assert_contains(html, "day-kicker", "Day pages should keep the editorial day header structure.")
    assert_contains(html, "ROVANIEMI", "The day kicker city should render in uppercase for preview/PDF parity.")
    assert_not_contains(html, "Today’s setting", "The rejected setting label must not render on day pages.")

    final_html_css = (
        (ROOT / "app_modules" / "itinerary_html.py").read_text(encoding="utf-8")
        + (ROOT / "app_modules" / "itinerary_html_styles.py").read_text(encoding="utf-8")
    )
    assert_not_contains(final_html_css, ".day-image-slot::after", "Final preview should no longer draw the decorative image divider emblem.")
    assert_contains(final_html_css, "border-top: 5px solid rgba(184,149,85,.96)", "Final preview should keep one thicker solid divider attached to the image edge.")
    assert_contains(final_html_css, "box-shadow: none", "Final preview divider should not use a two-tone shadow line.")
    assert_not_contains(final_html_css, 'content: "✦";\n            position: absolute;\n            left: 50%;', "The day-image divider emblem should be fully removed.")

    editor_html = _visual_editor_frontend_source()
    assert_contains(editor_html, "day-kicker", "The visual editor preview must use the same day-kicker structure as final preview/PDF.")
    assert_contains(editor_html, "summaryStyle", "The visual editor summary page must receive the seasonal background inline.")
    assert_not_contains(editor_html, ".image-stage::after", "The visual editor should no longer draw the decorative image divider emblem.")
    assert_not_contains(editor_html, "Today’s setting", "The visual editor preview must not render the rejected setting label.")


def test_seasonal_cover_title_and_subtitle_from_dates():
    from itinerary_generation.cover_theme import detect_cover_season, get_cover_theme
    from itinerary_generation.titles import create_trip_title, create_trip_subtitle

    raw = """
	Day 1	Hotel	2	10/07/2026	12/07/2026					Helsinki 	Hotel Haven, breakfast included
	Day 2	Activity		11/07/2026					Turku 	Archipelago cruise | 10:00 AM | 3 Hrs
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)
    assert_equal(detect_cover_season(rows), "summer", "July itineraries should use the summer cover season.")
    assert_equal(create_trip_title(rows, grouped), "Finland Summer Escape", "Single-country multi-destination trips should use the country in the cover title.")
    assert_equal(create_trip_subtitle(rows, grouped), "A Finland summer journey with scenic travel and planned experiences", "Single-country cover subtitle should be seasonal and country-aware.")

    theme = get_cover_theme(rows, {"cover_season": "winter"})
    assert_equal(theme.get("season"), "winter", "Manual cover season override should beat date detection.")


def test_cover_background_assets_are_available():
    from itinerary_generation.cover_theme import get_cover_background_path

    for season in ["winter", "spring", "summer", "autumn"]:
        path = get_cover_background_path(season)
        if not path or not path.exists():
            raise AssertionError(f"Missing cover background asset for {season}: {path}")


def test_day_overview_rental_explore_and_acronym_rendering():
    from ui.day_blocks import build_day_overview_block

    rental_block = build_day_overview_block({
        "row_id": "rental",
        "details": "Pickupo Rental vehicle from Office or Airport| Pick Up Rental SUV |\nOtpions or similar category\n* Dacia Duster\nincluded\n✅ Automatic\n✅ Full insurance\nNot included : Safety deposit",
    })
    rental_html = rental_block["html"]
    assert_contains(rental_html, "Rental vehicle", "Rental overviews should get a dedicated section label.")
    assert_contains(rental_html, "Pick up your rental SUV", "Rental pick-up wording should be compressed into a client-facing sentence.")
    assert_not_contains(rental_html, "Vehicle category examples", "Day-page rental blocks should not list every vehicle example.")
    assert_contains(rental_html, "full insurance included", "Rental included items should be summarized in one sentence.")
    assert_not_contains(rental_html, "<li>included</li>", "The word included should not render as a bullet.")

    explore_block = build_day_overview_block({
        "row_id": "explore",
        "details": "Explore\n* lava fields\n* hidden cafes\nOptional:\n* horse riding",
    })
    explore_html = explore_block["html"]
    assert_contains(explore_html, "Explore at your own pace", "Explore days should not be labelled as route days.")
    assert_not_contains(explore_html, "Suggested Route", "Explore-only days should not use the route label.")

    route_block = build_day_overview_block({"row_id": "route", "details": "SOUTH COAST WATERFALLS + ATV + VIK"})
    route_html = route_block["html"]
    assert_contains(route_html, "ATV", "Common acronyms should keep their uppercase form.")
    assert_not_contains(route_html, "Atv", "Acronyms should not be title-cased.")


def test_v36c61_title_preview_and_group_tour_quality_gate():
    from itinerary_generation.titles import create_day_title
    from ui.day_blocks import build_day_blocks
    from app_modules.itinerary_html import build_itinerary_html

    fixtures = Path(__file__).resolve().parent / "fixtures" / "real_inputs"
    rows = normalize_itinerary_rows(parse_itinerary((fixtures / "iceland_group_tour_winter.txt").read_text(encoding="utf-8")))
    grouped = group_rows_by_day(rows)

    assert_equal(create_day_title(grouped["Day 1"]), "Welcome to Iceland", "Arrival transfer + hotel days should use a warm welcome title.")
    day1_intro = create_day_intro(grouped["Day 1"], detail_level="Rich descriptive")
    assert_contains(day1_intro, "Welcome to Iceland", "Arrival intro should welcome the reader warmly.")
    assert_contains(day1_intro, "arranged Flybus transfer", "Arrival intro should explain the arranged transfer.")
    assert_not_contains(day1_intro, "The arrangements in", "Arrival intro should not use mechanical logistics wording.")

    assert_equal(create_day_title(grouped["Day 2"]), "Explore Borgarfjörður Valley & Waterfalls", "Group-tour activity title should beat overview logistics snippets.")
    assert_not_contains(create_day_title(grouped["Day 2"]), "Arrival Reykjavík", "Bad raw group-tour overview snippets must not become day titles.")
    day2_intro = create_day_intro(grouped["Day 2"], detail_level="Rich descriptive")
    assert_contains(day2_intro, "Your guided group tour begins today", "First group-tour day should introduce the guided group tour.")
    assert_contains(day2_intro, "between 8:00 AM and 8:30 AM", "First group-tour day should describe the pick-up window.")
    assert_not_contains(day2_intro, "Your guided tour begins today. Your guided group tour", "First group-tour day should not duplicate guided-tour intro wording.")

    day2_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 2"]) if block)
    assert_not_contains(day2_html, "Included Today", "Group-tour overview bullets should not dump onto the day page when a real activity row exists.")
    assert_contains(day2_html, "Pick-up:</span> Between 8:00 AM and 8:30 AM", "Group-tour overview start time should flow into a clear pick-up range.")
    assert_contains(day2_html, "Breakfast included", "Group-tour accommodation should use the clear breakfast wording.")
    assert_not_contains(day2_html, "With breakfast", "Group-tour accommodation should not use 'With breakfast'.")

    day4_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 4"]) if block)
    assert_not_contains(day4_html, "Reykjavík for 1 night", "Countryside placeholder accommodation should not borrow the activity city.")

    full_html = build_itinerary_html(rows, grouped)
    assert_contains(full_html, ".cover-subtitle", "Preview HTML should include the cover subtitle CSS.")
    assert_contains(full_html, "left: 0", "Preview cover text stack should span the A4 page and center its children.")
    assert_contains(full_html, "right: 0", "Preview cover text stack should share the full A4 center axis.")
    assert_contains(full_html, "transform: none", "Preview cover alignment should not rely on a separate subtitle offset.")
    assert_contains(full_html, "text-align: center", "Preview cover subtitle should be explicitly centered.")
    assert_not_contains(full_html, "12:00 AM noon", "Important notes should not contain impossible noon wording.")


def test_v36c71_title_admin_safety_blocks_supplier_titles():
    from app_modules.itinerary_html import build_itinerary_html
    from generator import group_rows_by_day
    from itinerary_generation.content_validator import validate_html
    from ui.day_blocks import build_arrival_block

    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "city": "Oslo",
            "title": "Final timing to be shared in Voucher",
            "original_title": "Final timing to be shared in Voucher",
            "details": "Final timing to be shared in Voucher",
            "row_id": "admin-title-activity",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "city": "Oslo",
            "title": "Book today: Oslo walking tour",
            "original_title": "Book today: Oslo walking tour",
            "details": "Meet your guide for a relaxed city walking tour through central Oslo.",
            "row_id": "cta-title-activity",
        },
    ]
    html = build_itinerary_html(rows, group_rows_by_day(rows), output_edits={})

    assert_not_contains(html, "Final timing to be shared in Voucher", "Voucher timing text must not render as an activity/day title.")
    assert_not_contains(html, "Book today", "Supplier call-to-action text must not render in titles.")
    assert_contains(html, "Oslo walking tour", "CTA stripping should preserve the real walking-tour title without the call-to-action prefix.")
    assert not validate_html(html)

    arrival_html = build_arrival_block({
        "type": "Arrival",
        "city": "Reykjavík",
        "title": "Arrival Reykjavík, pick-up minibus",
        "row_id": "raw-arrival-title",
    })["html"]
    assert_not_contains(arrival_html, "Arrival Reykjavík, pick-up minibus", "Arrival block titles must not expose raw pick-up logistics.")
    assert_contains(arrival_html, "Arrival in Reykjavík", "Arrival block should fall back to a clean client-facing title.")



def test_cover_route_html_keeps_final_pair_together_for_preview():
    from itinerary_generation.cover_route import cover_route_html

    html = cover_route_html("HELSINKI · ROVANIEMI · KAKSLAUTTANEN · IVALO · TROMSØ · BERGEN · OSLO")
    assert 'cover-route-line' in html
    assert 'BERGEN&nbsp;·&nbsp;OSLO' in html
    assert html.count('cover-route-line') == 2


def test_visual_editor_keeps_edits_pending_until_save_or_pdf_export():
    editor_html = _visual_editor_frontend_source()
    bridge_py = (ROOT / "visual_editor_component" / "editor_bridge.py").read_text(encoding="utf-8")
    main_view_py = (ROOT / "app_modules" / "main_view.py").read_text(encoding="utf-8")

    assert_not_contains(editor_html, "function scheduleAutosave()", "Visual editor should not trigger expensive Streamlit autosaves while typing.")
    assert_not_contains(editor_html, "setTimeout(saveChanges, 2200)", "Text edits should stay local instead of using a delayed autosave rerun.")
    assert_not_contains(editor_html, "el.addEventListener('blur', saveChanges", "Clicking away should not force a Streamlit rerun.")
    assert_contains(editor_html, "Unsaved edits", "The editor should show that browser-local changes are pending.")
    assert_contains(editor_html, "commit_nonce", "Create PDF should be able to request one explicit save from the editor.")
    assert_contains(editor_html, "shouldCommitPendingEdits", "PDF export should commit browser edits before any redraw can wipe them.")
    assert_contains(editor_html, "Do not redraw", "The commit path should document why it returns before draw().")
    assert_contains(bridge_py, "requests a commit before PDF export", "Python bridge docs should describe the PDF-export commit flow.")
    assert_contains(main_view_py, "Create PDF applies pending page edits first", "Export copy should explain the pending-edit workflow.")
    assert_contains(main_view_py, "preview_signature", "Preview should use a signature to avoid expensive rebuilds on ordinary reruns.")
    assert_contains(main_view_py, "PDF already up to date", "PDF export should reuse an unchanged PDF instead of rebuilding it every time.")
    assert_contains(main_view_py, "editor_applied", "Editor saves should not be followed by a stale extra preview rebuild.")
