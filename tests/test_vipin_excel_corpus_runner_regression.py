import json

from scripts.vipin_excel_corpus import (
    ExcelCorpusItem,
    collect_excel_corpus_items,
    evaluate_excel_corpus,
    write_bad_outputs_jsonl,
    write_markdown_report,
)


def _item(row_type, element, *, city="Rovaniemi", day="Day 1", row=10, from_date="01/01/2026"):
    return ExcelCorpusItem(
        file="Vipin sample.xlsx",
        sheet="10000",
        row=row,
        day=day,
        row_type=row_type,
        city=city,
        element=element,
        from_date=from_date,
    )


def test_detects_overlong_supplier_activity_title_from_vipin_pattern():
    item = _item(
        "Activity",
        "Visit to Santa Claus Village with lunch, 10:00 DURATION: 7 hours 30 min "
        "Rovaniemi is the Official Hometown of Santa Claus, and the town’s most popular attraction is "
        "Santa Claus Village on the Arctic Circle. Includes lunch and return transfer.",
    )

    summary = evaluate_excel_corpus([item])

    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]


def test_detects_missing_city_even_when_activity_title_is_present():
    item = _item(
        "Activity",
        "A Finntastic Walking Tour in Helsinki | 10:30 AM | 2. 15 Hr | "
        "Professional authorised Helsinki Guide meeting Point: Senate Square",
        city="",
        row=11,
    )

    summary = evaluate_excel_corpus([item])

    assert summary["parse_errors"] == 0
    assert summary["bad_output_counts"]["missing_source_city"] == 1
    assert "missing_parsed_city" not in summary["bad_output_counts"]
    assert "missing_city" not in summary["parser_flag_counts"]


def test_logs_blank_type_rows_and_calculator_cost_rows():
    blank_type = _item(
        "",
        "Helsinki: Overnight Cruise to Stockholm - Departure from Helsinki: 5:00 pm - "
        "Arrival to Stockholm: 10:00 am - Includes: Sleeper cabin",
        city="",
        row=12,
    )
    cost_row = _item("per pax", "486.8", city="", row=13)

    summary = evaluate_excel_corpus([blank_type, cost_row])

    assert summary["parse_errors"] == 0
    assert summary["bad_output_counts"]["missing_source_type"] == 1
    assert summary["bad_output_counts"]["non_itinerary_type"] == 1
    assert summary["skipped_count"] == 2


def test_writes_machine_log_and_human_report(tmp_path):
    item = _item(
        "Activity",
        "A Finntastic Walking Tour in Helsinki | 10:30 AM | 2. 15 Hr | "
        "Professional authorised Helsinki Guide meeting Point: Senate Square",
        city="",
    )
    summary = evaluate_excel_corpus([item])
    jsonl_path = tmp_path / "bad.jsonl"
    report_path = tmp_path / "report.md"

    write_bad_outputs_jsonl(summary["bad_outputs"], jsonl_path)
    write_markdown_report(summary, report_path, bad_jsonl_path=jsonl_path)

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line)["category"] == "missing_source_city" for line in lines)
    report = report_path.read_text(encoding="utf-8")
    assert "INPUT4 Vipin Excel Corpus Regression Report" in report
    assert "missing_source_city" in report


def test_keeps_day_overview_as_day_text_not_transport_title():
    item = _item(
        "Day overview",
        "Group Tour Starts: 8-Day Holiday Package Ring Road & Landmannalaugar | "
        "Overview Discover Iceland from Reykjavík across the Golden Circle. "
        "What to expect? Your journey begins with geysers and waterfalls. Book your return flight after Day 8.",
        city="South Coast",
        row=14,
    )

    summary = evaluate_excel_corpus([item])
    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]


def test_compacts_long_day_activity_prose_titles():
    item = _item(
        "Activity",
        "Day 1: Embark on an unforgettable journey through Iceland's breathtaking landscapes "
        "on the Ultimate Icelandic Adventure Tour. Your adventure begins with a pick-up in Reykjavík, "
        "followed by a scenic drive to Þingvellir National Park.",
        city="South Coast",
        row=15,
    )

    summary = evaluate_excel_corpus([item])
    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]


def test_long_distance_bus_transfer_becomes_compact_transport_title():
    item = _item(
        "Transfer",
        "Bus : Long distance comfortable panorama coach transfer from Rovaniemi Bus Station "
        "to Saariselka - Tickets Included",
        city="Saariselka",
        row=16,
    )

    summary = evaluate_excel_corpus([item])
    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]


def test_private_transfer_route_strips_address_from_title():
    item = _item(
        "Transfer",
        "Private Transfer Fjellheisen Cable Car to The Polar Museum, Søndre Tollbodgate 11, "
        "9008 Tromsø | tickets to be bought on site, Price not included",
        city="Tromso",
        row=17,
    )

    summary = evaluate_excel_corpus([item])
    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]


def test_infers_city_from_leading_known_place_title():
    item = _item(
        "Activity",
        "Helsinki Hop on Hop off 24 Hr ticket",
        city="",
        row=18,
    )

    summary = evaluate_excel_corpus([item])
    assert summary["parse_errors"] == 0
    assert summary["bad_output_counts"]["missing_source_city"] == 1
    assert "missing_parsed_city" not in summary["bad_output_counts"]


def test_chooses_earliest_supplier_prose_boundary():
    item = _item(
        "Activity",
        "Day 2: Explore Snæfellsnes Prepare to explore amazing things like lava fields, "
        "waterfalls and black beaches. The village of Arnarstapi is your next destination.",
        city="West Iceland",
        row=19,
    )

    summary = evaluate_excel_corpus([item])

    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]


def test_compacts_repeated_subject_activity_descriptions():
    item = _item(
        "Activity",
        "Day 1: Seljalandsfoss Waterfall Seljalandsfoss, a jewel in Iceland's landscape, "
        "captivates with its ethereal beauty and interactive allure.",
        city="South Coast",
        row=20,
    )

    summary = evaluate_excel_corpus([item])

    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]


def test_compacts_vipin_transport_and_rental_titles():
    rows = [
        _item(
            "Transfer",
            "The coach from Rovaniemi bus Station to Saariselkä bus station Booking window is not opened yet, "
            "therefore final timing will be intimated in the Booking vouchers",
            city="Saariselka",
            row=21,
        ),
        _item(
            "Day overview",
            "Pick-up your rental car at the car rental office - with room for 4 luggages will be provided "
            "Suzuki Vitara 4x4 or similar • SUV Unlimited mileage • Fuel policy: Full to full",
            city="Reykjavik",
            row=22,
        ),
    ]

    summary = evaluate_excel_corpus(rows)

    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]


def test_compacts_remaining_real_corpus_title_shapes():
    rows = [
        _item(
            "Hotel",
            "4 Star, Arctic City Hotel 4xNight, 3x Classic Double Room "
            "1x STYLE TWIN ROOM STYLE TWIN ROOM ( with extra bed )",
            city="Rovaniemi",
            row=23,
        ),
        _item(
            "Activity",
            "Tromsø Cable Car Round Trip Ticket: Enjoy the spectacular view of Tromsø and its beautiful "
            "surroundings from above, daytime or evening. Tickets only, self explored.",
            city="Tromso",
            row=24,
        ),
        _item(
            "Notes",
            "Icebreaker Cruise will not be available at this date, to add icebreaker, the availability starts from 23 Nov onwards",
            city="Rovaniemi",
            row=25,
        ),
    ]

    summary = evaluate_excel_corpus(rows)

    assert summary["parse_errors"] == 0
    assert "overlong_title" not in summary["bad_output_counts"]
    assert "activity_text_used_as_title" not in summary["bad_output_counts"]
