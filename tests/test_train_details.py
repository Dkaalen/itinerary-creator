from itinerary_generation.train_details import get_train_cabin_detail


def test_train_cabin_detail_uses_specific_cabin_from_input():
    row = {
        "type": "Train",
        "effective_type": "Train",
        "title": "Overnight train",
        "details": "Cabin (private double) included on the night train",
    }

    assert get_train_cabin_detail(row) == "Private Double sleeper cabin"


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


def test_train_cabin_detail_preserves_supplier_quantity_and_category():
    row = {
        "type": "Transfer",
        "effective_type": "Train",
        "title": "Overnight Train to Helsinki",
        "details": "Overnight Train Transfer with the Santa Claus Express to Helsinki - 21:00 pm - 09:00 am - 4 x downstairs cabin for two people",
    }

    assert get_train_cabin_detail(row) == "4 x downstairs cabin for two people"
