from itinerary_parser import parse_itinerary


def _row(day, row_type, city, details, nights="", start="46158", end=""):
    return "\t".join(["", day, row_type, nights, start, end, "", "", "", city, details])


def test_input5_city_column_survives_when_details_cell_is_blank():
    raw = _row("Day 4", "Activity", "Kiruna", "")

    row = parse_itinerary(raw)[0]

    assert row["city"] == "Kiruna"
    assert row["title"] == "Time in Kiruna"
    assert "missing_city" not in row["parser_review_flags"]


def test_input5_product_prefix_is_not_misread_as_city():
    raw = _row(
        "Day 3",
        "Activity",
        "Tromso",
        "fjellheisen Cable Car: Tickets Included Round Trip Ticket: "
        "Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, "
        "daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car",
    )

    row = parse_itinerary(raw)[0]

    assert row["city"] == "Tromsø"
    assert row["title"] == "Fjellheisen Cable Car"
    assert len(row["title"]) < 100


def test_input5_activity_prose_title_is_shortened_before_duration_body_text():
    raw = _row(
        "Day 2",
        "Activity",
        "Rovaniemi",
        "Visit to Santa Claus Village with lunch, 10:00 DURATION: 7 hours 30 min "
        "Rovaniemi is the Official Hometown of Santa Claus, and the town’s most popular attraction is "
        "Santa Claus Village on the Arctic Circle. Includes lunch and return transfer.",
    )

    row = parse_itinerary(raw)[0]

    assert row["title"] == "Visit to Santa Claus Village with lunch"
    assert len(row["title"]) < 100
    assert "Official Hometown" not in row["title"]


def test_input5_activity_city_can_be_inferred_from_title_when_source_city_is_blank():
    raw = _row(
        "Day 2",
        "Activity",
        "",
        "A Finntastic Walking Tour in Helsinki | 10:30 AM | 2.15 Hr | "
        "Professional authorised Helsinki Guide meeting Point: Senate Square",
    )

    row = parse_itinerary(raw)[0]

    assert row["city"] == "Helsinki"
    assert row["title"] == "A Finntastic Walking Tour in Helsinki"
    assert "missing_city" not in row["parser_review_flags"]


def test_input5_shared_supplier_suffix_does_not_become_title():
    raw = _row(
        "Day 5",
        "Activity",
        "Kakslauttanen",
        "2H Reindeer Safari 2 Hours, Shared, includes hot drink, Transfers, thermal clothing, "
        "winter boots and gloves are provided.",
    )

    row = parse_itinerary(raw)[0]

    assert row["title"] == "2H Reindeer Safari 2 Hours"
    assert "thermal clothing" not in row["title"]
