from itinerary_parser import parse_itinerary


def _row(day, row_type, city, details, nights="", start="01/01/2026", end=""):
    return "\t".join(["", day, row_type, nights, start, end, "", "", "", city, details])


def test_vipin_activity_title_survives_empty_pipe_after_city_prefix():
    raw = _row(
        "Day 6",
        "Activity",
        "Rovaniemi",
        "Rovaniemi: | Lakeside Sauna Experience |10:00 AM | 3 Hrs Pick-up / meeting point, Rovakatu 19b, Rovaniemi\n"
        "Overview: Experience the ultimate Finnish tradition.\n"
        "What's included?\nProfessional, English-speaking guide",
    )

    row = parse_itinerary(raw)[0]

    assert row["title"] == "Lakeside Sauna Experience"
    assert row["time"] == "10:00 AM"
    assert row["duration"] == "3 hours"
    assert row["parser_review_flags"] == []


def test_vipin_optional_activity_title_drops_admin_prefix_time_and_prose():
    raw = _row(
        "Day 6",
        "Activity",
        "Stockholm",
        "Optional : Stockholm: Stockholm Archipelago Dinner Cruise (19:00 - 22.00) incl. dinner in classic archipelago ship, "
        "stunning views, elegant interiors, and great food. Pre-book a three-course menu or choose your meal onboard.",
    )

    row = parse_itinerary(raw)[0]

    assert row["is_optional"] is True
    assert row["commercial_status"] == "optional"
    assert row["title"] == "Stockholm Archipelago Dinner Cruise"
    assert row["time"] == "7:00 PM - 10:00 PM"


def test_vipin_multiline_supplier_activity_uses_first_line_as_title():
    raw = _row(
        "Day 4",
        "Activity",
        "Rovaniemi",
        "Polar Explorer Icebreaker Cruise Experience in Lapland\n"
        "09:00 - 12:00 Swedish / 10:00 - 01:00 Finnish Polar Explorer Icebreaker Cruise\n"
        "Polar Explorer\nThe full Arctic Expedition. Cinema, professional photography, guided tours, dining - the complete experience.",
    )

    row = parse_itinerary(raw)[0]

    assert row["title"] == "Polar Explorer Icebreaker Cruise Experience in Lapland"
    assert "Cinema" not in row["title"]
    assert row["time"] == "9:00 AM - 12:00 PM"


def test_vipin_hyphen_train_route_gets_route_points_and_clean_title():
    raw = _row(
        "Day 8",
        "Transfer",
        "Rovaniemi",
        "Day train, Rovaniemi - Helsinki\nInterCity 24 9:22 - 17:39\nDates not yet released, timing to be confirmed in final voucher",
    )

    row = parse_itinerary(raw)[0]

    assert row["effective_type"] == "Train"
    assert row["title"] == "Train to Helsinki"
    assert row["route_origin"] == "Rovaniemi"
    assert row["route_destination"] == "Helsinki"
    assert "missing_route_origin" not in row["parser_review_flags"]
    assert "missing_route_destination" not in row["parser_review_flags"]


def test_vipin_flight_typo_o_between_places_is_treated_as_to():
    raw = _row(
        "Day 5",
        "Transfer",
        "Svolvær",
        "FLight Bergen o Svolvær self-arranged cost not included",
    )

    row = parse_itinerary(raw)[0]

    assert row["effective_type"] == "Flight"
    assert row["title"] == "Flight to Svolvær"
    assert row["route_origin"] == "Bergen"
    assert row["route_destination"] == "Svolvær"


def test_vipin_calculator_cost_rows_are_not_itinerary_rows():
    raw = "\n".join([
        _row("Day 1", "Activity", "Oslo", "Oslo: Essential Oslo Walking Tour | 10 AM | 2 Hrs"),
        _row("Day 1", "Per Pax", "Oslo", "4000"),
        _row("Day 1", "One Pax", "Oslo", "2500"),
        _row("Day 1", "4000.0", "Oslo", "Internal total"),
    ])

    rows = parse_itinerary(raw)

    assert len(rows) == 1
    assert rows[0]["title"] == "Essential Oslo Walking Tour"


def test_vipin_nutshell_part_marker_does_not_pollute_destination_title():
    raw = _row(
        "Day 9",
        "Activity",
        "Oslo",
        "Norway in a NUtshell | Flam to Oslo part 2 09:00 Flåm09:44 Myrdal Via Train10:02 Myrdal15:05 Oslo Via Train",
        start="",
    )

    row = parse_itinerary(raw)[0]

    assert row["effective_type"] == "Transport"
    assert row["title"] == "Norway in a Nutshell to Oslo"
    assert row["route_origin"] == "Flåm"
    assert row["route_destination"] == "Oslo"
