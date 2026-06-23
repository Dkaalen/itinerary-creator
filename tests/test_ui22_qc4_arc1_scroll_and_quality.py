from pathlib import Path

from app_modules.itinerary_render_context import build_itinerary_render_context
from generator import group_rows_by_day
from itinerary_generation.quality_gate import evaluate_itinerary_quality
from parser_modules.parser_main import parse_itinerary


NORWAY_INPUT = """
Day 1	Arrival	01.08.2026		Oslo: Welcome to Norway
Day 1	Transfer	01.08.2026		Oslo: Self transfer to your accommodation
Day 1	Hotel	01.08.2026	03.08.2026	Oslo: Check in to your accommodation for a 2 night stay - Thon Hotel Opera - 1 x Double Room, 1 x Single Room - Breakfast included
Day 1	Leisure	01.08.2026		Oslo: Spend time at leisure
Day 2	Activity	02.08.2026		Oslo: Fjord Sightseeing Cruise onboard Electric Boat - Time: 11:00 am - 01:00 pm - Meeting point: Platform E, behind Fisketorget by ‘’TROLLCRUISE’’ sign - Includes: Electric fjord cruise with audio guidance, Access to outdoor deck and blankets, Charging ports and free Wi-FI, Comfortable seating, Panoramic windows, Accessibility features, Onboard toilets - Description: Embark on a 2-hr Oslofjord Sightseeing Cruise, where history, culture, and natural beauty intertwine.
Day 2	Leisure	02.08.2026		Oslo: Spend time at leisure
Day 3	Transfer	03.08.2026		Oslo: Self Transfer to Oslo Central Station
Day 3	Train	03.08.2026		Oslo: Scenic Train Transfer to Kristiansand - Time: 11:23 am - 3:53 pm - Meeting point: Oslo Central Station - Includes: Tickets
Day 3	Transfer	03.08.2026		Kristiansand: Self transfer to your accommodation
Day 3	Hotel	03.08.2026	05.08.2026	Kristiansand: Check in to your accommodation for a 2 night stay - Clarion Hotel Ernst - 1 x Double Room, 1 x Single Room - Breakfast included
Day 4	Activity	04.08.2026		Kristiansand: Guided Kayaking on the Otra River - Time: 11:00 am - 2:00 pm - Meeting point: Odderøyveien 5 - Includes: Pick-up from meeting point to starting point, Professional, English-speaking guide, All equipment is included - Description: This is a peaceful, beautiful and safe tour.
Day 5	Transfer	05.08.2026		Kristiansand: Self transfer to Kristinsand Station
Day 5	Train	05.08.2026		Kristiansand: Scenic train transfer to Stavanger - Time: 12:00 pm - 3:18 pm - Meeting point: Kristiansand Station - Includes: Tickets
Day 5	Transfer	05.08.2026		Stavanger: Self transfer to your accommodation
Day 5	Hotel	05.08.2026	07.08.2026	Stavanger: Check in to your accommodation for a 2 night stay - Thon Hotel Maritim - 2 x Double Room - Breakfast included
Day 6	Activity	06.08.2026		Stavanger: Lysefjord & Preikestolen Fjord Cruise - Time: 12:30 pm - 4:30 pm - Meeteing point: Strandkaien - Includes: Sustainable, quiet & scenic fjord cruise, Boat tour aboard & luxurious catamaran, Spacious cabin with comfortable leather seats, Panoramic windows & large viewing decks, Audio guiding & free Wi-Fi on board, Licensed café serving snacks & drinks - Description: Discover magical Lysefjord. Gaze up at spectacular Preikestolen (Pulpit Rock), majestic waterfalls and amazing mountains on our half-day fjord cruise!
Day 7	Cruise	07.08.2026		Stavanger: Atlantic Coastal Cruise Transfer to Bergen - Time: 07:30 am - 1:00 pm - Meeting point: Stavanger Crusie Port - Includes: Tickets, Fjord Lounge
Day 7	Hotel	07.08.2026	09.08.2026	Bergen: Check in to your accommodation for a 2 night stay - Thon Hotel Rosenkrantz Bergen - 1 x Double Room, 1 x Small Double Room - Breakfast included
Day 8	Activity	08.08.2026		Bergen: Guided Walking Tour of Bergen Past & Present - Time: 10:00 am - 12:00 pm - Meeting point: Bradbenken 1 - Includes: Profesional Guide - Description: Discover the stories, landscapes and local life that shaped Bergen from the Middle Ages to today.
Day 8	Activity	08.08.2026		Bergen: Fløybanen Funicluar Experience - Time: Flexible - Meeting point: Fløybanen - Includes: Tickets valid for the day - Description: Take the funicular Fløibanen to the top of Mount Fløyen and experience spectacular views of the city, the fjord and the surrounding mountains.
Day 9	Transfer	09.08.2026		Bergen: Self transfer to Bergen Train Station
Day 9	Activity	09.08.2026		Bergen: Norway in a Nutshell to Oslo - Time: 08:29 am - 10:27 pm - Meeting point: Bergen Train Station - Includes: Train transfer Bergen to Voss (08:29 am - 09:41 am), Coach transfer Voss to Gudvangen (10:10 am - 11:10 am), Fjord Cruise Gudvangen to Flåm (12:10 am - 2:10 pm), Train transfer Flåm to Myrdal (4:00 pm - 4:57 pm), Train Transfer Myrdal to Oslo (5:40 pm - 10:27 pm)
Day 9	Hotel	09.08.2026	12.08.2026	Oslo: Check in to your accommodation for a 2 night stay - Thon Hotel Opera - 1 x Double Room, 1 x Single Room - Breakfast included
Day 10	Activity	10.08.2026		Oslo: Norwegian Food Tour with Stops at Hidden City Gems - Time: 12:00 pm - 3:00 pm - Meeting point: Oslo Central Station, Jernbanetorget 1 - Includes: Local English-speaking guide, Explore hidden gems of Oslo, Public transport ticket, Food, skip the line entrance - Description: Experience an authentic Norwegian athmosphere and hidden gems.
Day 12	Transfer	12.08.2026		Oslo: Self transfer to Oslo Airport
Day 12	Departure	12.08.2026		Oslo: Departure home
""".strip()


def _render_context():
    rows = parse_itinerary(NORWAY_INPUT)
    grouped = group_rows_by_day(rows)
    return rows, build_itinerary_render_context(rows, grouped, {})


def test_ui22_frontend_preserves_canvas_scroll_across_autosave_and_redraw():
    source = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in [
            "visual_editor_component/frontend/js/state.js",
            "visual_editor_component/frontend/js/editing.js",
            "visual_editor_component/frontend/js/render.js",
        ]
    )

    assert "function captureEditorScrollState" in source
    assert "function restoreEditorScrollState" in source
    assert "captureEditorScrollState(stateName)" in source
    assert "restoreEditorScrollState();" in source
    assert "allowNextDrawToResetScroll" in source


def test_qc4_uses_date_derived_hotel_nights_and_flags_source_conflict():
    rows = parse_itinerary(NORWAY_INPUT)
    final_oslo = [row for row in rows if row.get("type") == "Hotel" and row.get("day") == "Day 9"][0]
    report = evaluate_itinerary_quality(rows)
    codes = {issue.code for issue in report.issues}

    assert final_oslo["hotel_nights"] == "3"
    assert final_oslo["source_hotel_nights"] == "2"
    assert "hotel_nights_date_mismatch" in codes
    assert "suspicious_am_pm_time_range" in codes


def test_qc4_source_typos_are_corrected_without_losing_logistics_or_aliases():
    rows, context = _render_context()
    text = "\n".join(
        [context.trip_title, context.trip_subtitle]
        + [day.title + "\n" + day.intro for day in context.render_document.days]
        + [block.description for day in context.render_document.days for block in day.blocks]
    )
    day6 = next(day for day in context.render_document.days if day.day == "Day 6")
    day8 = next(day for day in context.render_document.days if day.day == "Day 8")
    day6_activity = next(block for block in day6.blocks if block.kind == "activity")
    day8_funicular = [block for block in day8.blocks if block.kind == "activity"][-1]

    assert any(meta.label == "Meeting point" and meta.value == "Strandkaien" for meta in day6_activity.meta)
    assert "Preikestolen (Pulpit Rock)" in day6_activity.description
    assert "Preikestolen (Preikestolen)" not in text
    assert "Mount Fløyen" in day8_funicular.description
    assert "Mount Fløibanen" not in text
    assert "Funicluar" not in text
    assert "athmosphere" not in text
    assert len(day6_activity.includes) == 7
    assert "Licensed café serving snacks & drinks" in day6_activity.includes


def test_arc1_journey_arc_uses_real_highlights_not_generic_destination_fillers():
    _rows, context = _render_context()
    arc = context.journey_arc
    experiences = [row["experience"] for row in arc]

    assert experiences == [
        "Oslofjord cruise and capital welcome",
        "Otra River kayaking and southern coast",
        "Lysefjord and Preikestolen cruise",
        "Historic Bergen and Fløibanen views",
        "Norway in a Nutshell and Oslo food tour",
    ]
    assert not any("Capital and fjords" in value or "coastal charm" in value for value in experiences)


def test_ui23_quiet_known_typo_corrections_and_better_activity_intros():
    rows, context = _render_context()
    report = evaluate_itinerary_quality(rows)
    codes = {issue.code for issue in report.issues}
    day4 = next(day for day in context.render_document.days if day.day == "Day 4")
    day6 = next(day for day in context.render_document.days if day.day == "Day 6")
    day10 = next(day for day in context.render_document.days if day.day == "Day 10")

    assert "source_typo_corrected" not in codes
    assert "known typo" not in "\n".join(issue.message for issue in report.issues).lower()
    assert "explore Kristiansand from the water" in day4.intro
    assert "main arranged experience" not in day4.intro
    assert "Sail from Stavanger" in day6.intro
    assert "Today brings you closer" not in day6.intro
    assert "Taste your way through Oslo" in day10.intro


def test_nin1_self_transfer_to_train_station_does_not_become_fake_train_route():
    rows, context = _render_context()
    self_transfer = next(row for row in rows if row.get("day") == "Day 9" and row.get("type") == "Transfer" and row.get("city") == "Bergen")
    day9 = next(day for day in context.render_document.days if day.day == "Day 9")
    travel_lines = [line for block in day9.blocks if block.kind == "travel_sequence" for line in block.lines]
    joined = "\n".join(travel_lines)

    assert self_transfer["effective_type"] == "Transfer"
    assert self_transfer["title"].startswith("Bergen: Self-arranged transfer")
    assert "Train to Bergen Bergen" not in joined
    assert "Self-arranged transfer to Bergen Railway Station" in joined
    assert "Bergen: Self-arranged transfer" not in joined
    assert "Norway in a Nutshell to Oslo" in joined


def test_page2_page_actions_are_centered_inside_canvas_not_right_edge():
    css = Path("visual_editor_component/frontend/styles/editor.css").read_text(encoding="utf-8")
    assert "UI23: compact editor chrome and centered page actions" in css
    assert "grid-template-columns: 1fr auto 1fr" in css
    assert ".page-header-row .page-controls" in css
    assert "justify-self: center" in css
    assert "max-width: calc(var(--page-w) - 260px)" in css


def test_ui23_editor_toolbar_is_compact_but_keeps_advanced_status_available():
    source = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    css = Path("visual_editor_component/frontend/styles/editor.css").read_text(encoding="utf-8")

    assert "toolbar-copy compact" in source
    assert "toolbar-legacy-label" in source
    assert "${studioStatusStripHtml()}" in source
    assert "Advanced tools" in source
    assert "grid-template-columns: minmax(180px, 1fr) auto" in css
