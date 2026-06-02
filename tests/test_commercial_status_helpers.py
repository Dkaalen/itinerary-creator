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


def test_mark_optional_row_sets_consistent_fields_and_prefixes_row_id_once():
    row = {"row_id": "abc123", "is_optional": False}
    mark_optional_row(row)
    mark_optional_row(row)
    assert row["is_optional"] is True
    assert row["commercial_status"] == OPTIONAL
    assert row["commercial_reason"] == "optional_text_prefix"
    assert row["row_id"] == "opt_abc123"

def test_common_text_cleanup_conservatively_fixes_commercial_and_place_typos():
    from parser_modules.text_cleanup import fix_common_text

    cleaned = fix_common_text(
        "Self Arrnaged pirce not inclueded from Tromso to Flam via "
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

