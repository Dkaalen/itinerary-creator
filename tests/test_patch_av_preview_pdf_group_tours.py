from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image

from app_modules.itinerary_render_context import build_itinerary_render_context
from images.preview_image_contract import day_image_matches_from_preview_html, merge_preview_image_contract
from itinerary_generation.common import group_rows_by_day
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows
from itinerary_generation.render_model import RenderDay, RenderDocument
from pdf_exporter_modules.typed_exporter import export_render_document_to_pdf


GROUP_TOUR_SOURCE = """
Day 1	Transfer 	01/10/2026							Reykjavik	Shuttle/FLybus  Airport to City Centre 
Day 1	Hotel	01/10/2026	02/10/2026					Reykjavik	3 Star , Fosshotel Raudara  , 1xNight , 1xStandard Double Room, Incl Brekafast 
Day 2	Day overview	02/10/2026							Reykjavik	"Reykjavík: 6-Day Holiday Package Ring Road Tour & Blue Lagoon |9 AM | 6 DAY GROUP TOUR STARTS  Overview
What's included?
Pick-up/drop-off in central Reykjavik
5 nights hotel accommodation incl. breakfast
Day 1: The Golden Circle and South Coast
Day 2: The South Coast and Jökulsarlon
Day 3: Eastern Iceland and Egilsstadir
Day 4: The North-East and Akureyri
Day 5: Western Iceland and Laugarbakki
Day 6: Western Iceland and Blue Lagoon"
Day 2	Activity	02/10/2026							SOUTH COAST	"Day 1: Explore the Golden Circle & South Coast
Embark on an unforgettable journey through Iceland's breathtaking landscapes. Visit Þingvellir National Park, Geysir, Gullfoss, Seljalandsfoss and Skógafoss."
Day 3	Activity	03/10/2026							Höfn	"Day 2: Discover Glaciers, Ice Caves & Diamond Beach
After breakfast, visit Vík, the Katla Ice Cave, Jökulsárlón glacier lagoon and Diamond Beach. Alternatively, enjoy free time if conditions require changes."
Day 4	Activity	04/10/2026							Egilsstaðir	"Day 3: Visit Eastern Villages & Relax at Vök Baths
Drive through the Eastfjords, visit Djúpivogur, Borgarfjörður Eystri and Vök Baths."
Day 5	Activity	05/10/2026							Akureyri	"Day 4: Admire Canyons, Waterfalls & Geothermal Wonders
After enjoying breakfast, visit Stuðlagil Canyon, Dettifoss, Mývatn and Goðafoss."
Day 6	Activity	06/10/2026							Laugarbakki	"Day 5: Spot Whales & Explore Historic Sites
Start your day with whale watching before continuing towards Laugarbakki."
Day 7	Activity	07/10/2026							Reykjavik	"Day 6: Hike Craters, See Waterfalls & Relax at Blue Lagoon
Return to Reykjavík via waterfalls before relaxing at the Blue Lagoon."
Day 7	Hotel	07/10/2026	08/10/2026					Reykjavik	3 Star ,Center Hotels Skjaldbreið, 1xNight , 1xStandard Double Room, Incl Brekafast 
Day 8	Transfer 	08/10/2026								Shuttle / Flybus : City centre to Airport
"""


def _group_tour_rows():
    return normalize_itinerary_rows(parse_itinerary(GROUP_TOUR_SOURCE))


def test_patch_av_group_tour_days_are_not_misclassified_as_leisure():
    rows = _group_tour_rows()
    by_day = group_rows_by_day(rows)
    context = build_itinerary_render_context(rows, by_day, {"pictures_added": False})

    day3 = next(day for day in context.render_document.days if day.day == "Day 3")
    day5 = next(day for day in context.render_document.days if day.day == "Day 5")
    day8 = next(day for day in context.render_document.days if day.day == "Day 8")

    assert day3.title == "Discover Glaciers, Ice Caves & Diamond Beach"
    assert "leisure" not in day3.title.lower()
    assert any(block.kind == "activity" for block in day3.blocks)
    assert day5.title == "Admire Canyons, Waterfalls & Geothermal Wonders"
    assert day8.city == "Reykjavík"
    assert day8.title == "Departure from Reykjavík"


def test_patch_av_group_tour_route_uses_programme_cities_not_flybus_service_label():
    rows = _group_tour_rows()
    context = build_itinerary_render_context(rows, group_rows_by_day(rows), {"pictures_added": False})
    glance = {line.label: line.value for line in context.render_document.summary.trip_glance}

    assert glance["Start"] == "Reykjavík"
    assert glance["End"] == "Reykjavík"
    assert "Shuttle" not in glance["Destinations"]
    assert "Flybus" not in glance["Destinations"]
    assert "South Coast" in glance["Destinations"]
    assert "Höfn" in glance["Destinations"]
    assert "Akureyri" in glance["Destinations"]


def test_patch_av_preview_image_contract_preserves_reviewed_picture_data_uri(tmp_path):
    source = tmp_path / "correct_preview.png"
    Image.new("RGB", (80, 40), (20, 120, 40)).save(source, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(source.read_bytes()).decode("ascii")
    html = (
        '<div class="a4-page day-page single-day-page" data-day="Day 1">'
        '<div class="day-image-slot" data-image-path="/remote/full-bank/Iceland/Reykjavik.webp" '
        'data-image-crop-focus="center" data-image-score="123" data-image-reason="city folder match" data-image-city="Reykjavík">'
        f'<img class="day-image-preview-img" src="{data_uri}" />'
        '</div></div>'
    )

    contract = day_image_matches_from_preview_html(html)
    merged = merge_preview_image_contract({"Day 1": {"path": "wrong/default.webp"}}, contract)

    assert merged["Day 1"]["path"].endswith("Reykjavik.webp")
    assert merged["Day 1"]["data_uri"] == data_uri
    assert merged["Day 1"]["reason"] == "city folder match"


def test_patch_av_typed_pdf_uses_preview_contract_data_uri_when_path_is_unavailable(tmp_path):
    source = tmp_path / "preview_source.png"
    Image.new("RGB", (320, 190), (10, 180, 80)).save(source, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(source.read_bytes()).decode("ascii")
    document = RenderDocument(
        title="Image parity test",
        days=[RenderDay(day="Day 1", number="1", city="Reykjavík", title="Preview Image", intro="Short intro.")],
    )
    pdf_path = tmp_path / "preview.pdf"

    export_render_document_to_pdf(
        document,
        pdf_path,
        day_images={"Day 1": {"path": str(tmp_path / "missing.webp"), "data_uri": data_uri}},
        day_image_crop_focus={"Day 1": "center"},
    )

    import fitz

    pdf = fitz.open(pdf_path)
    try:
        assert any(pdf.load_page(index).get_images(full=True) for index in range(pdf.page_count))
    finally:
        pdf.close()
