from pathlib import Path
from tests.support.static_contracts import read_contract_text


def test_transport_render_special_blocks_are_split_from_generic_renderer():
    generic = read_contract_text("itinerary_generation/transport_domain/render.py")
    nutshell = read_contract_text("itinerary_generation/transport_domain/nutshell_render.py")
    coastal = read_contract_text("itinerary_generation/transport_domain/coastal_cruise_render.py")

    assert "def build_featured_nutshell_block" not in generic
    assert "def build_coastal_cruise_block" not in generic
    assert "def build_featured_nutshell_block" in nutshell
    assert "def build_coastal_cruise_block" in coastal
    assert len(generic.splitlines()) < 380


def test_nutshell_domain_and_parsing_do_not_import_transport_facade_or_each_other():
    domain = read_contract_text("itinerary_generation/nutshell_domain.py")
    parsing = read_contract_text("itinerary_generation/nutshell_parsing.py")
    labels = read_contract_text("itinerary_generation/nutshell_labels.py")
    facade = read_contract_text("itinerary_generation/transport_norway.py")

    assert "from itinerary_generation.nutshell_parsing import" in domain
    assert "from itinerary_generation.transport_norway import" not in domain
    assert "itinerary_generation.nutshell_domain" not in parsing
    assert "itinerary_generation.nutshell_parsing" not in labels
    assert "from itinerary_generation.nutshell_labels import _norway_nutshell_route_label" in facade
    assert "from itinerary_generation.nutshell_parsing import" in facade
