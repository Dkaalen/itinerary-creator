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


def test_nutshell_truth_is_owned_by_neutral_domain_and_generation_files_are_facades():
    domain = read_contract_text("itinerary_domain/nutshell_domain.py")
    parsing = read_contract_text("itinerary_domain/nutshell_parsing.py")
    labels = read_contract_text("itinerary_domain/nutshell_labels.py")
    transport = read_contract_text("itinerary_domain/transport_norway.py")
    generation_facades = [
        read_contract_text("itinerary_generation/nutshell_domain.py"),
        read_contract_text("itinerary_generation/nutshell_parsing.py"),
        read_contract_text("itinerary_generation/transport_norway.py"),
    ]

    assert "from itinerary_domain.nutshell_parsing import" in domain
    assert "itinerary_domain.transport_norway" not in domain
    assert "itinerary_domain.nutshell_domain" not in parsing
    assert "itinerary_domain.nutshell_parsing" not in labels
    assert "from itinerary_domain.nutshell_labels import _norway_nutshell_route_label" in transport
    assert "from itinerary_domain.nutshell_parsing import" in transport
    assert all('_import_module("itinerary_domain.' in facade for facade in generation_facades)
    assert not (Path(__file__).resolve().parents[1] / "itinerary_generation" / "nutshell_labels.py").exists()
