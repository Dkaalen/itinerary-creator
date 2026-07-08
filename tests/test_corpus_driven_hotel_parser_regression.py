from itinerary_parser import parse_itinerary


def _row(day, row_type, city, details, nights="", start="46158", end=""):
    return "\t".join(["", day, row_type, nights, start, end, "", "", "", city, details])


def test_hotel_name_before_night_count_is_extracted():
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


def test_hotel_name_with_embedded_star_and_night_count_is_extracted():
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


def test_suite_property_name_is_not_treated_as_room_category():
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


def test_generic_star_hotel_title_is_client_ready_when_property_missing():
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


def test_hotel_igloo_property_name_is_not_treated_as_room_category():
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


def test_multiplication_symbol_room_quantity_is_parsed():
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


def test_hotel_nights_survive_checkin_phrase_cleanup():
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


def test_star_only_hotel_name_falls_back_to_city_accommodation():
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


def test_room_category_with_meal_text_is_not_swallowed_as_meal_only():
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


def test_room_category_without_room_word_but_with_quantity_and_qualifier_is_parsed():
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


def test_snowhotel_suite_is_room_not_hotel_name_noise():
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
