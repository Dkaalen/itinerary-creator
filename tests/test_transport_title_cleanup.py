from itinerary_generation.transport import get_primary_transport_title


def test_primary_transport_title_removes_time_and_ticket_noise():
    rows = [
        {
            "type": "Transport",
            "effective_type": "Transport",
            "city": "Kakslauttanen",
            "title": "Coach Transfer to Kakslauttanen – 11:45 am – 3:02 pm – Tickets Included",
            "details": "Coach transfer to Kakslauttanen with tickets included.",
        }
    ]

    assert get_primary_transport_title(rows) == "Coach Transfer to Kakslauttanen"
