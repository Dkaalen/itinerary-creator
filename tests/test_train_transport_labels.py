from itinerary_generation.transport import get_premium_transport_phrase


def test_train_transport_phrase_mentions_supported_sleeper_cabin():
    row = {
        "type": "Train",
        "effective_type": "Train",
        "title": "Overnight train from Stockholm to Kiruna",
        "details": "Cabin (private double) included on the night train",
        "city": "Kiruna",
    }

    phrase = get_premium_transport_phrase(row)

    assert "sleeper cabin" in phrase.lower()
    assert "private double sleeper cabin" in phrase.lower()


def test_train_transport_phrase_does_not_invent_sleeper_cabin():
    row = {
        "type": "Train",
        "effective_type": "Train",
        "title": "Train from Oslo to Bergen",
        "details": "Reserved seats included",
        "city": "Bergen",
    }

    phrase = get_premium_transport_phrase(row)

    assert "sleeper cabin" not in phrase.lower()
