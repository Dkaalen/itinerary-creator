from parser_modules.commercial_status import (
    EXCLUDED,
    INCLUDED,
    OPTIONAL,
    SELF_ARRANGED,
    infer_commercial_status,
    infer_optional_row_type,
    initial_commercial_state,
    mark_optional_row,
)


def test_initial_commercial_state_is_included_by_default():
    assert initial_commercial_state(False) == (INCLUDED, "default_included")
    assert initial_commercial_state(True) == (OPTIONAL, "explicit_optional")


def test_infer_optional_row_type_uses_leading_title_only():
    description = "Longyearbyen: Second Walrus Safari Boat Tour - Includes: transfer to/from the harbour"
    assert infer_optional_row_type(description) == "Activity"


def test_infer_optional_row_type_detects_leading_transport_optional():
    assert infer_optional_row_type("Transfer to Tromsø Airport - private car") == "Transfer"
    assert infer_optional_row_type("Flight Oslo to Kirkenes - luggage included") == "Flight"


def test_infer_commercial_status_detects_self_arranged_and_excluded_transport():
    assert infer_commercial_status(False, "Transfer", "Self Transfer Hotel to Airport", "") == (
        SELF_ARRANGED,
        "self_transfer",
    )
    assert infer_commercial_status(False, "Flight", "Flight Tromsø to Bergen", "cost not included") == (
        SELF_ARRANGED,
        "cost_not_included",
    )
    assert infer_commercial_status(False, "Transfer", "Coach transfer", "tickets not included") == (
        EXCLUDED,
        "not_included_marker",
    )


def test_activity_not_included_prose_does_not_exclude_entire_activity():
    assert infer_commercial_status(False, "Activity", "Food tour", "drinks not included") == (
        INCLUDED,
        "default_included",
    )


def test_mixed_rental_deposit_note_does_not_exclude_rental_vehicle_row():
    assert infer_commercial_status(
        False,
        "Day Overview",
        "Pick-up Rental vehicle from Office or Airport",
        "included automatic full insurance gravel protection not included: safety deposit",
    ) == (INCLUDED, "default_included")


def test_mark_optional_row_sets_consistent_fields_and_prefixes_row_id_once():
    row = {"row_id": "abc123", "is_optional": False}
    mark_optional_row(row)
    mark_optional_row(row)
    assert row["is_optional"] is True
    assert row["commercial_status"] == OPTIONAL
    assert row["commercial_reason"] == "optional_text_prefix"
    assert row["row_id"] == "opt_abc123"

def test_common_text_cleanup_conservatively_fixes_commercial_and_place_typos():
    from shared.source_text_cleanup import fix_common_text

    cleaned = fix_common_text(
        "Self Arrnaged pirce not inclueded Excurssion transfere crusie Chocholate "
        "Desctiption Krongborg Rosklide St Nickolas from Tromso to Flam via "
        "Svolvaer, Reykjavik, Malmo, Hofn and Kakslauttenen at Staion"
    )

    assert "self-arranged price not included" in cleaned
    assert "Tromsø" in cleaned
    assert "Flåm" in cleaned
    assert "Svolvær" in cleaned
    assert "Reykjavík" in cleaned
    assert "Malmö" in cleaned
    assert "Höfn" in cleaned
    assert "Kakslauttanen" in cleaned
    assert "Station" in cleaned
    assert "Excursion" in cleaned
    assert "transfer" in cleaned
    assert "cruise" in cleaned
    assert "chocolate" in cleaned
    assert "Description" in cleaned
    assert "Kronborg" in cleaned
    assert "Roskilde" in cleaned
    assert "St Nicholas" in cleaned



def test_self_arranged_markers_are_shared_between_parser_and_generation_filters():
    from itinerary_generation.row_filters import is_self_arranged

    marker_cases = [
        "self arranged",
        "self-arranged",
        "self arrange",
        "self arrnage",
        "own arrangement",
        "cost not included",
        "price not included",
        "ticket to be bought on site",
        "ticket to be bought on spot",
        "to be paid locally",
        "CostNot Included",
    ]

    for marker in marker_cases:
        parser_status = infer_commercial_status(False, "Flight", "Flight Oslo to Bergen", marker)
        generator_row = {"type": "Flight", "title": f"Flight Oslo to Bergen {marker}", "details": ""}

        assert parser_status == (SELF_ARRANGED, "cost_not_included")
        assert is_self_arranged(generator_row)


def test_activity_exclusion_text_stays_included_in_generation_filter():
    from itinerary_generation.row_filters import is_self_arranged

    row = {"type": "Activity", "title": "Food tour", "details": "drinks cost not included"}

    assert not is_self_arranged(row)
