from itinerary_generation.train_details import get_train_cabin_detail


def test_train_cabin_detail_uses_specific_cabin_from_input():
    row = {
        "type": "Train",
        "effective_type": "Train",
        "title": "Overnight train",
        "details": "Cabin (private double) included on the night train",
    }

    assert get_train_cabin_detail(row).lower() == "private double sleeper cabin"


def test_train_cabin_detail_detects_sleeper_cabin_from_input():
    row = {
        "type": "Train",
        "effective_type": "Train",
        "title": "Night train with sleeper cabin",
        "details": "Sleeper cabin included",
    }

    assert get_train_cabin_detail(row) == "Sleeper cabin"


def test_train_cabin_detail_does_not_invent_cabin_for_regular_train():
    row = {
        "type": "Train",
        "effective_type": "Train",
        "title": "Train from Oslo to Bergen",
        "details": "Reserved seats included",
    }

    assert get_train_cabin_detail(row) == ""


def test_train_cabin_detail_ignores_non_train_rows():
    row = {
        "type": "Cruise",
        "effective_type": "Cruise",
        "title": "Cruise cabin",
        "details": "Cabin (outside) included",
    }

    assert get_train_cabin_detail(row) == ""
