from pathlib import Path


def test_transport_render_special_blocks_are_split_from_generic_renderer():
    generic = Path("itinerary_generation/transport_domain/render.py").read_text(encoding="utf-8")
    nutshell = Path("itinerary_generation/transport_domain/nutshell_render.py").read_text(encoding="utf-8")
    coastal = Path("itinerary_generation/transport_domain/coastal_cruise_render.py").read_text(encoding="utf-8")

    assert "def build_featured_nutshell_block" not in generic
    assert "def build_coastal_cruise_block" not in generic
    assert "def build_featured_nutshell_block" in nutshell
    assert "def build_coastal_cruise_block" in coastal
    assert len(generic.splitlines()) < 380


def test_nutshell_domain_and_parsing_do_not_import_transport_facade_or_each_other():
    domain = Path("itinerary_generation/nutshell_domain.py").read_text(encoding="utf-8")
    parsing = Path("itinerary_generation/nutshell_parsing.py").read_text(encoding="utf-8")
    labels = Path("itinerary_generation/nutshell_labels.py").read_text(encoding="utf-8")
    facade = Path("itinerary_generation/transport_norway.py").read_text(encoding="utf-8")

    assert "from itinerary_generation.nutshell_parsing import" in domain
    assert "from itinerary_generation.transport_norway import" not in domain
    assert "itinerary_generation.nutshell_domain" not in parsing
    assert "itinerary_generation.nutshell_parsing" not in labels
    assert "from itinerary_generation.nutshell_labels import _norway_nutshell_route_label" in facade
    assert "from itinerary_generation.nutshell_parsing import" in facade
