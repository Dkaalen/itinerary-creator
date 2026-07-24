from pathlib import Path

from itinerary_generation.transport_domain import TransportRouteFacts, get_transport_route_facts
from tests.support.static_contracts import read_contract_text


def test_package_exports_the_production_route_facts_contract() -> None:
    facts = get_transport_route_facts(
        {
            "effective_type": "Train",
            "type": "Train",
            "title": "Train: Oslo to Bergen",
            "details": "Direct train Oslo to Bergen",
            "city": "Oslo",
        }
    )

    assert isinstance(facts, TransportRouteFacts)
    assert facts.display_route == "Oslo to Bergen"
    assert facts.has_transport_mode is True


def test_activity_logistics_do_not_reclassify_the_activity_as_transport() -> None:
    facts = get_transport_route_facts(
        {
            "effective_type": "Activity",
            "type": "Activity",
            "title": "Santa Claus Village visit",
            "details": "Return transfers included",
            "city": "Rovaniemi",
        }
    )

    assert facts.mode == "transfer"
    assert facts.has_transport_mode is False


def test_endpoint_contract_warning_uses_the_canonical_route_result() -> None:
    facts = get_transport_route_facts(
        {
            "effective_type": "Transfer",
            "type": "Transfer",
            "route_origin": "Self transfer",
            "route_destination": "Bergen",
            "title": "Self transfer to Bergen",
            "city": "Oslo",
        }
    )

    assert facts.display_route == "Bergen"
    assert facts.warnings == ("origin_looks_like_service_phrase",)


def test_alternate_route_facts_module_is_absent() -> None:
    assert not Path("itinerary_generation/transport_domain/facts.py").exists()


def test_real_output_qa_imports_the_production_route_owner() -> None:
    scoring = read_contract_text("scripts/real_output_qa/scoring.py")

    assert "from itinerary_generation.transport_domain.routes import get_transport_route_facts" in scoring
    assert "transport_domain.facts" not in scoring
    assert "build_transport_facts" not in scoring
