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


def test_input5_decimal_nights_are_not_misread_as_city_prefix():
    raw = _row(
        "Day 9",
        "Hotel",
        "",
        "Bergen: Check in to your accommodation for a 2 night stay - Centrally located 3/4-star hotel - Standard Room - Breakfast included",
        nights="2.0",
        start="46207",
        end="46209",
    )

    row = parse_itinerary(raw)[0]

    assert row["city"] == "Bergen"
    assert row["city"] != "2.0"
    assert "missing_city" not in row["parser_review_flags"]


def test_input5_sparse_departure_uses_same_day_city_context():
    raw = "\n".join([
        _row("Day 11", "Transfer", "", "Bergen: Private transfer to Bergen Airport", start="46209"),
        _row("Day 11", "Transfer", "", "Departure", start="46209"),
    ])

    rows = parse_itinerary(raw)

    assert rows[1]["city"] == "Bergen"
    assert "missing_city" not in rows[1]["parser_review_flags"]


def test_input5_sparse_transfer_before_hotel_is_backfilled_from_same_day_city():
    raw = "\n".join([
        _row("Day 1", "Transfer", "", "Private Airport to Hotel", start="46194"),
        _row("Day 1", "Hotel", "Reykjavik", "3 Star , Klettur Hotel, 1x Standard Double Room, Incl Breakfast", start="46194", end="46195"),
    ])

    rows = parse_itinerary(raw)

    assert rows[0]["city"] == "Reykjavík"
    assert "missing_city" not in rows[0]["parser_review_flags"]


def test_input5_sparse_activity_uses_recent_city_context():
    raw = "\n".join([
        _row("Day 4", "Activity", "", "Rovaniemi: Northern Lights Unlimited Mileage Photo Tour with 97% Success Rate", start="46366"),
        _row("Day 5", "Activity", "", "City Highlights, Santa Village & Husky-Reindeer Safari | 08:20 AM | 7 Hrs | meeting point: Nordic Unique Travels Office, Maakuntakatu 29, Rovaniemi", start="46367"),
    ])

    rows = parse_itinerary(raw)

    assert rows[1]["city"] == "Rovaniemi"
    assert "missing_city" not in rows[1]["parser_review_flags"]


def test_input5_blank_fixed_excel_details_do_not_turn_dates_into_titles():
    raw = _row("Day 8", "Hotel", "", "", nights="2.0", start="46165", end="46167")

    rows = parse_itinerary(raw)

    assert rows == []


def test_input5_meeting_point_city_can_supply_sparse_activity_city():
    raw = _row(
        "Day 5",
        "Activity",
        "",
        "City Highlights, Santa Village & Husky-Reindeer Safari | 08:20 AM | 7 Hrs | "
        "meeting point: Nordic Unique Travels Office, Maakuntakatu 29, Rovaniemi",
        start="46367",
    )

    row = parse_itinerary(raw)[0]

    assert row["city"] == "Rovaniemi"
    assert "missing_city" not in row["parser_review_flags"]


def test_input5_sparse_departure_summary_does_not_require_route_points():
    raw = _row("Day 11", "Transfer", "", "Departure", start="46209")

    row = parse_itinerary(raw)[0]

    assert row["title"] == "Departure"
    assert "missing_city" not in row["parser_review_flags"]
    assert "missing_route_origin" not in row["parser_review_flags"]
    assert "missing_route_destination" not in row["parser_review_flags"]


def test_input5_hotel_name_before_night_count_is_extracted():
    raw = _row(
        "Day 3",
        "Hotel",
        "Rovaniemi",
        "3 Star , Hotel Aakenus 2xNight , 3x Tirple Room, Incl Brekafast",
        nights="2.0",
        start="46342",
        end="46344",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Hotel Aakenus"
    assert row["hotel_nights"] == "2"
    assert row["title"] == "Hotel Aakenus"
    assert "missing_hotel_name" not in row["parser_review_flags"]


def test_input5_hotel_name_with_embedded_star_and_night_count_is_extracted():
    raw = _row(
        "Day 1",
        "Hotel",
        "Oslo",
        "4 Star , Comfort Hotel Grand Central 2xNight , 1xSuperior Doubel Room, Incl Brekafast |Room size 28 Sq metre",
        nights="2.0",
        start="46281",
        end="46283",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Comfort Hotel Grand Central"
    assert row["hotel_nights"] == "2"
    assert row["room_category"] == "Superior Double Room"
    assert "missing_hotel_name" not in row["parser_review_flags"]


def test_input5_suite_property_name_is_not_treated_as_room_category():
    raw = _row(
        "Day 4",
        "Hotel",
        "Rovaniemi",
        "4Star, Golden Circle Suites , 2xNight , 1xSuperior suite with Sauna , Incl Brekafast",
        nights="2.0",
        start="46344",
        end="46346",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Golden Circle Suites"
    assert row["room_category"] == "Superior suite with Sauna"
    assert "missing_hotel_name" not in row["parser_review_flags"]


def test_input5_generic_star_hotel_title_is_client_ready_when_property_missing():
    raw = _row(
        "Day 5",
        "Hotel",
        "Aarhus",
        "3 Star , 1xNight , 1xStandard Triple Room, Incl Brekafast",
        nights="1.0",
        start="46158",
        end="46159",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "3-star hotel in Aarhus"
    assert row["title"] == "3-star hotel in Aarhus"
    assert "missing_hotel_name" not in row["parser_review_flags"]


def test_input5_hotel_igloo_property_name_is_not_treated_as_room_category():
    raw = _row(
        "Day 3",
        "Hotel",
        "Rovaniemi",
        "Arctic SnowHotel & Glass Igloos , 1xnight , 1xDouble Glass Igloo twin beds Adult: 2 , incl breakfast",
        nights="1.0",
        start="46335",
        end="46336",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Arctic SnowHotel & Glass Igloos"
    assert row["title"] == "Arctic SnowHotel & Glass Igloos"
    assert "missing_hotel_name" not in row["parser_review_flags"]


def test_input5_norway_in_a_nutshell_route_points_are_extracted():
    raw = _row(
        "Day 2",
        "Activity",
        "Voss",
        "Oslo to Flåm: Norway in a Nutshell Part 1 | Train 08:23 Oslo - 13:04 Myrdal | Bus 17:25 Gudvangen - 18:25 Voss",
        start="46200",
    )

    row = parse_itinerary(raw)[0]

    assert row["effective_type"] == "Transport"
    assert row["route_origin"] == "Oslo"
    assert row["route_destination"] == "Voss"
    assert "missing_route_origin" not in row["parser_review_flags"]
    assert "missing_route_destination" not in row["parser_review_flags"]


def test_input5_timed_multileg_transport_route_points_are_extracted():
    raw = _row(
        "Day 7",
        "Transfer",
        "Trondheim",
        "Bus 07.11 Ålesund - 09.17 Åndalsnes + Train 16:29 Åndalsnes stasjon- 20:55 Trondheim S (platform change less than 100 m)",
        start="46200",
    )

    row = parse_itinerary(raw)[0]

    assert row["route_origin"] == "Ålesund"
    assert row["route_destination"] == "Trondheim S"
    assert "missing_route_origin" not in row["parser_review_flags"]
    assert "missing_route_destination" not in row["parser_review_flags"]


def test_input5_local_transfer_summaries_do_not_require_route_points():
    raw = _row(
        "Day 1",
        "Transfer",
        "Reykjavik",
        "Keflavik: Pick up your rental car at the car rental office - Includes: Unlimited mileage",
        start="46200",
    )

    row = parse_itinerary(raw)[0]

    assert row["title"] == "Pick-up rental car"
    assert "missing_route_origin" not in row["parser_review_flags"]
    assert "missing_route_destination" not in row["parser_review_flags"]

def test_input5_cost_row_after_transfer_does_not_pollute_transfer_title():
    raw = "\n".join([
        _row("Day 9", "Transfer", "Tromso", "Private Hotel to Airport", start="46411"),
        _row("3000", "per pax", "650.0", "486.8"),
    ])

    rows = parse_itinerary(raw)

    assert len(rows) == 1
    assert rows[0]["title"] == "Private transfer from your hotel to Tromsø Airport"
    assert rows[0].get("parser_review_flags") == []

def test_input5_nutshell_schedule_without_dashes_extracts_first_and_last_place():
    raw = _row(
        "Day 3",
        "Activity",
        "Gudvangen",
        "Norway in a Nutshell Part 1 09:18 Oslo 14:20 Myrdal via train 14:41 Myrdal 15:39 Flåm Via train 17:30 Flåm 19:20 Gudvangen Via Cruise",
        start="46200",
    )

    row = parse_itinerary(raw)[0]

    assert row["effective_type"] == "Transport"
    assert row["route_origin"] == "Oslo"
    assert row["route_destination"] == "Gudvangen"
    assert "missing_route_origin" not in row.get("parser_review_flags", [])
    assert "missing_route_destination" not in row.get("parser_review_flags", [])


def test_input5_timed_airport_flight_extracts_route_points():
    raw = _row(
        "Day 4",
        "Transfer",
        "Oslo",
        "Flight: 14:20 Copenhagen Airport Direct 15:30 Oslo Airport with 8xcabin, 23x checkin luggages",
        start="46200",
    )

    row = parse_itinerary(raw)[0]

    assert row["effective_type"] == "Flight"
    assert row["route_origin"] == "Copenhagen Airport"
    assert row["route_destination"] == "Oslo Airport"


def test_input5_self_arranged_flight_without_route_points_is_not_review_noise():
    raw = _row(
        "Day 4",
        "Transfer",
        "Oslo",
        "Flight self-arranged, cost not included",
        start="46200",
    )

    row = parse_itinerary(raw)[0]

    assert row["effective_type"] == "Flight"
    assert "missing_route_origin" not in row.get("parser_review_flags", [])
    assert "missing_route_destination" not in row.get("parser_review_flags", [])

def test_input5_multiplication_symbol_room_quantity_is_parsed():
    raw = _row(
        "Day 4",
        "Hotel",
        "Kiruna",
        "3 Star Camp Ripan, Kiruna, 1xNight, 5 × Kiruna Chalet, Incl Breakfast",
        nights="1.0",
        start="46200",
        end="46201",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Camp Ripan"
    assert row["room_category"] == "Kiruna Chalet"
    assert "missing_room_category" not in row.get("parser_review_flags", [])


def test_input5_hotel_nights_survive_checkin_phrase_cleanup():
    raw = _row(
        "Day 5",
        "Hotel",
        "Myvatn",
        "4 Star, Mývatn: Fosshotel Mývatn, Check in to your accommodation for a 1 night stay - 2 × Standard Double Room full double bed - breakfast included",
        start="46200",
        end="46201",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_nights"] == "1"
    assert row["room_category"] == "Standard Double Room full double bed"
    assert "missing_hotel_nights" not in row.get("parser_review_flags", [])


def test_input5_star_only_hotel_name_falls_back_to_city_accommodation():
    raw = _row(
        "Day 1",
        "Hotel",
        "Helsinki",
        "3/4 Star, 1xNight, 1xStandard Double Room, Incl Breakfast",
        nights="1.0",
        start="46200",
        end="46201",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "3/4-star hotel in Helsinki"
    assert "weak_title" not in row.get("parser_review_flags", [])

def test_input5_room_category_with_meal_text_is_not_swallowed_as_meal_only():
    raw = _row(
        "Day 1",
        "Hotel",
        "Stockholm",
        "4 Star, Victory Hotel, 3xNight, 2 × Double Captain’s room Incl Breakfast",
        nights="3.0",
        start="46200",
        end="46203",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Victory Hotel"
    assert row["room_category"] == "Double Captain’s room"
    assert row["meal_plan"] == "breakfast"


def test_input5_room_category_without_room_word_but_with_quantity_and_qualifier_is_parsed():
    raw = _row(
        "Day 1",
        "Hotel",
        "Helsinki",
        "4 Star, Scandic Grand Marina Hotel or similar, 2xNight, 1xSuperior Quad King and Sofa bed, Incl Breakfast",
        nights="2.0",
        start="46200",
        end="46202",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Scandic Grand Marina Hotel"
    assert row["room_category"] == "Superior Quad King and Sofa bed"

def test_input5_snowhotel_suite_is_room_not_hotel_name_noise():
    raw = _row(
        "Day 1",
        "Hotel",
        "Rovaniemi",
        "Arctic Snow Hotel, 1xnight, 2xSnowHotel Double Suite, incl Breakfast",
        nights="1.0",
        start="46200",
        end="46201",
    )

    row = parse_itinerary(raw)[0]

    assert row["hotel_name"] == "Arctic Snow Hotel"
    assert row["room_category"] == "SnowHotel Double Suite"
