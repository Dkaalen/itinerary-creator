from app_modules.image_gateway import image_bank_is_ready_for_client_pictures
from images.remote_pack_resolver import destination_requests_from_rows


def test_nutshell_route_stops_do_not_become_required_destination_packs():
    grouped = {
        "Day 4": [
            {
                "day": "Day 4",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Oslo",
                "title": "Norway in a Nutshell to Bergen",
                "details": "Train transfer Oslo to Myrdal, Train transfer Myrdal to Flåm, Fjord Cruise Flåm to Gudvangen, Coach Transfer Gudvangen to Voss, Train transfer Voss to Bergen",
            },
            {
                "day": "Day 4",
                "type": "Hotel",
                "effective_type": "Hotel",
                "city": "Bergen",
                "title": "Radisson Blu Royal Bergen",
            },
        ]
    }

    requests = destination_requests_from_rows(grouped)

    assert [request.key for request in requests] == ["Norway/Bergen"]


def test_agent_and_customer_share_default_fallback_readiness_contract():
    default_status = {
        "full_bank_found": False,
        "missing_full_bank": True,
        "default_only": True,
        "default_image_count": 2,
        "total_image_count": 2,
    }

    assert image_bank_is_ready_for_client_pictures(default_status) is True
