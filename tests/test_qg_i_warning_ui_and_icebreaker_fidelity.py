import sys
import types

streamlit_stub = sys.modules.get("streamlit") or types.ModuleType("streamlit")
streamlit_stub.session_state = getattr(streamlit_stub, "session_state", {})
components_stub = sys.modules.get("streamlit.components") or types.ModuleType("streamlit.components")
components_v1_stub = sys.modules.get("streamlit.components.v1") or types.ModuleType("streamlit.components.v1")
components_v1_stub.html = getattr(components_v1_stub, "html", lambda *args, **kwargs: None)
components_v1_stub.declare_component = getattr(components_v1_stub, "declare_component", lambda *args, **kwargs: (lambda **component_kwargs: None))
components_stub.v1 = components_v1_stub
streamlit_stub.components = components_stub
sys.modules["streamlit"] = streamlit_stub
sys.modules["streamlit.components"] = components_stub
sys.modules["streamlit.components.v1"] = components_v1_stub

from generator import group_rows_by_day
from itinerary_generation.activity_descriptions import client_activity_description
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from ui.day_blocks import build_day_blocks
from itinerary_generation.content_validator import compact_html
from visual_editor_component.editor_workflow import build_visual_editor_payload


def _normalize(text: str):
    rows = normalize_itinerary_rows(parse_itinerary(text))
    return rows, group_rows_by_day(rows)


def test_meeting_point_snowmobile_park_does_not_rename_northern_lights_minibus_tour():
    rows, grouped = _normalize('''
	Day 5	Activity	27/12/2026						Rovaniemi	"Rovaniemi: Northern Lights Hunt by Minibus at the Arctic Circle | 8 PM | 3 Hrs | Pick up / meeting point ,Arctic City Snowmobile Park office, Koskikatu 8, Rovaniemi | Pick-up/drop off in central Rovaniemi ,Professional, English-speaking guide ,Winter overalls, boots and gloves ,Warm juice and cookies"
''')
    activity = next(row for row in rows if row.get("effective_type") == "Activity")

    assert activity["title"] == "Northern Lights Hunt"
    assert "Snowmobile" not in activity["title"]

    day_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 5"]) if block)
    plain = compact_html(day_html)

    assert "Northern Lights Hunt" in plain
    assert "Snowmobile Evening Safari" not in plain


def test_icebreaker_products_stay_distinct():
    cases = [
        ("Polar Explorer Icebreaker Cruise | 10 AM | 3 Hrs", "Polar Explorer Icebreaker Cruise", "Polar Explorer Icebreaker"),
        ("Finnish Arctic Explorer Icebreaker Cruise | Pickup 11:10 AM from Rovaneimi | Drop 17:30 Rovaniemi", "Finnish Arctic Explorer Icebreaker Cruise", "Arctic Explorer Icebreaker"),
        ("Sampo Icebreaker Cruise | 9 AM | 4 Hrs", "Sampo Icebreaker Cruise", "Sampo Icebreaker"),
        ("Arktis Icebreaker Cruise | 9 AM | 3 Hrs", "Arktis Icebreaker Cruise", "Arktis Icebreaker"),
    ]
    for raw, expected_title, expected_description_name in cases:
        rows, _grouped = _normalize(f'\n\tDay 4\tActivity\t26/12/2026\t\t\t\t\t\tRovaniemi\t"{raw} Icebreaker cruise includes floating in survival suits, walk on the frozen sea, complimentary hot drink and certificate."\n')
        activity = next(row for row in rows if row.get("effective_type") == "Activity")
        assert activity["title"] == expected_title
        description = client_activity_description(activity)
        assert expected_description_name in description


def test_visual_editor_warning_payload_and_assets_are_actionable():
    text = '''
	Day 1	Activity	24/12/2026						Oslo	"Oslo: Fjord Cruise with Silent Electric Ship | 01:30 AM | 2 Hrs | What's included? Cruise on the Oslo Fjord"
'''
    rows, grouped = _normalize(text)
    document = build_itinerary_document(rows, grouped)
    assert document.warnings

    payload = build_visual_editor_payload(rows, grouped, {})
    warnings = payload["client_output_warnings"]

    assert warnings
    assert any(warning.get("page_label") for warning in warnings)
    assert any("Day 1" in warning.get("page_label", "") for warning in warnings)
