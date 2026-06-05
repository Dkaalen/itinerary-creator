from itinerary_generation.cover_route import cover_route_html, create_cover_route_line
from itinerary_generation.day_intro_engine import create_day_intro as engine_create_day_intro
from itinerary_generation.day_intro_planner import _intro_for_title
from itinerary_generation.day_text import create_day_intro as public_create_day_intro
from itinerary_generation.titles import create_destinations_line
from normalizer import normalize_itinerary_rows
from itinerary_parser import parse_itinerary
from generator import group_rows_by_day


def test_day_text_uses_single_intro_engine_for_public_api():
    raw = """
    Day 1	Transfer		01/01/2026					Oslo	Private Airport to Hotel
    Day 1	Hotel	1	01/01/2026	02/01/2026				Oslo	Comfort Hotel Børsparken, 1xNight, 1xStandard Double Room, Incl Breakfast
    """
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    day_rows = group_rows_by_day(rows)["Day 1"]

    assert public_create_day_intro(day_rows, detail_level="Rich descriptive") == engine_create_day_intro(day_rows, detail_level="Rich descriptive")


def test_day_planner_intro_helper_comes_from_shared_engine():
    assert _intro_for_title("Fjellheisen Cable Car", "Tromsø", "single_activity_day") == "Use today for a flexible viewpoint visit in Tromsø, with Fjellheisen Cable Car arranged so you can choose the timing that suits the day."


def test_cover_route_line_and_html_share_orphan_prevention():
    rows = normalize_itinerary_rows(parse_itinerary("""
    Day 1	Hotel	1	01/01/2026	02/01/2026				Helsinki	Hotel A, 1xNight, Incl Breakfast
    Day 2	Hotel	1	02/01/2026	03/01/2026				Rovaniemi	Hotel B, 1xNight, Incl Breakfast
    Day 3	Hotel	1	03/01/2026	04/01/2026				Kakslauttenen	Hotel C, 1xNight, Incl Breakfast
    Day 4	Hotel	1	04/01/2026	05/01/2026				Ivalo	Hotel D, 1xNight, Incl Breakfast
    Day 5	Hotel	1	05/01/2026	06/01/2026				Tromso	Hotel E, 1xNight, Incl Breakfast
    Day 6	Hotel	1	06/01/2026	07/01/2026				Bergen	Hotel F, 1xNight, Incl Breakfast
    Day 7	Hotel	1	07/01/2026	08/01/2026				Oslo	Hotel G, 1xNight, Incl Breakfast
    """))

    route = create_destinations_line(rows)
    assert route == create_cover_route_line(rows)
    html = cover_route_html(route)
    assert "<br>" in html
    assert "Bergen&nbsp;·&nbsp;Oslo" in html


def test_itinerary_generation_layer_does_not_import_ui_modules():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "itinerary_generation"
    offenders = []
    for py_file in root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("ui"):
                offenders.append(f"{py_file.relative_to(root.parent)}:{node.lineno}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "ui" or alias.name.startswith("ui."):
                        offenders.append(f"{py_file.relative_to(root.parent)}:{node.lineno}")

    assert offenders == []


def test_route_only_transport_rows_populate_cover_and_glance_metadata():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows
    from generator import group_rows_by_day
    from itinerary_generation.summaries import create_trip_glance
    from itinerary_generation.titles import create_destinations_line

    raw = """
    Day 1	Transport	01/01/2026								Long distance comfortable panorama coach transfer from Rovaniemi Bus Station to Tromsø Busterminal Prostneset
    """
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    grouped = group_rows_by_day(rows)

    assert create_destinations_line(rows) == "Rovaniemi · Tromsø"
    assert create_trip_glance(rows, grouped)["Start"] == "Rovaniemi"
    assert create_trip_glance(rows, grouped)["End"] == "Tromsø"
    assert create_trip_glance(rows, grouped)["Destinations"] == "Rovaniemi · Tromsø"
