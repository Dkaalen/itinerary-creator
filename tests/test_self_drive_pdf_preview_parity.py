import base64
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from regression_test_helpers import assert_contains, assert_not_contains


SELF_DRIVE_SOURCE = """Day 1	Car	09.06.2026								Oslo	Pick up your rental car at the aiport car rental office - Suzuki S-Cross AWD (automatic) or similar - Includes: Airport service charge, Collision damage waiver, Fuel information, Unlimited mileage, Vehicle licence fee / road fund licence, Theft protection, Vat, Other taxes and service charges, Supplementary liability insurance, Cancellation fee
Day 1	Drive	09.06.2026								Oslo	Drive to Voss - Time: 08:30 am - 2:30 pm (without stops)
Day 1	Hotel	09.06.2026	10.06.2026							Voss	Check in to your accommodation for a 1 night stay - Scandic Voss - 2 x Standard Room - Breakfast included
Day 2	Drive	10.06.2026								Voss	Drive to Bergen - 3:00 pm - 5:30 pm (without stops)
Day 2	Hotel	10.06.2026	11.06.2026							Bergen	Check in to your accommodation for a 1 night stay - Radisson Blu Royal Bergen - 2 x Standard Room - Breakfast included
Day 3	Hotel	11.06.2026	12.06.2026							Stavanger	Check in to your accommodation for a 1 night stay - Radisson Blu Atlantic Stavanger - 1 x Standard room, 1 x single room - Breakfast included
Day 5	Hotel	13.06.2026								Oslo	Deliver your rental car at the airport car rental office
"""


def _rows_and_grouped():
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows
    from generator import group_rows_by_day

    rows = normalize_itinerary_rows(parse_itinerary(SELF_DRIVE_SOURCE))
    return rows, group_rows_by_day(rows)


def test_self_drive_rows_are_routes_not_included_today():
    from ui.day_blocks import build_day_blocks

    _, grouped = _rows_and_grouped()
    day1_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 1"]) if block)
    day2_html = "\n".join(block["html"] for block in build_day_blocks(grouped["Day 2"]) if block)

    assert_contains(day1_html, "Rental vehicle", "Rental pickup should render as a rental vehicle block.")
    assert_contains(day1_html, "Self-drive route", "Drive rows should render as self-drive route guidance.")
    assert_contains(day1_html, "Oslo to Voss", "Drive rows should show origin and destination.")
    assert_contains(day2_html, "Voss to Bergen", "Later drive rows should keep origin and destination.")
    assert_not_contains(day1_html, "<div class=\"section-title\">Included Today</div><ul class=\"detail-list\"><li>Drive to Voss", "Drives are not inclusions.")
    assert_not_contains(day2_html, "Included Today", "Plain self-drive rows should not appear as Included Today.")


def test_self_drive_inclusions_preserve_room_quantities_and_rental_section():
    from itinerary_generation.inclusion_sections import create_categorized_inclusions

    rows, grouped = _rows_and_grouped()
    sections = create_categorized_inclusions(rows, grouped)
    all_text = "\n".join("\n".join(section.get("items", [])) for section in sections)
    accommodation_text = "\n".join("\n".join(section.get("items", [])) for section in sections if section.get("title") == "Accommodation")
    rental_text = "\n".join("\n".join(section.get("items", [])) for section in sections if section.get("title") == "Rental vehicle")

    assert_contains(accommodation_text, "2 x Standard Room", "Accommodation inclusions should preserve room quantities.")
    assert_contains(accommodation_text, "1 x Standard Room, 1 x Single Room", "Mixed room quantities should be preserved.")
    assert_contains(rental_text, "Suzuki S-Cross AWD", "Rental inclusion should mention the example vehicle.")
    assert_contains(rental_text, "collision damage waiver", "Rental inclusion should summarize included rental services.")
    assert_not_contains(accommodation_text, "Deliver your rental car", "Rental return must not be listed as accommodation.")
    assert_not_contains(all_text, "Cancellation fee", "Operational rental fees should not be client-facing inclusions.")


def test_pdf_day_image_uses_embedded_preview_image_when_path_is_unavailable():
    from PIL import Image
    from pdf_exporter import export_html_to_pdf

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "preview_source.png"
        image = Image.new("RGB", (320, 190), (10, 180, 80))
        image.save(source_path, format="PNG")
        data_uri = "data:image/png;base64," + base64.b64encode(source_path.read_bytes()).decode("ascii")

        html_path = tmp_path / "preview.html"
        pdf_path = tmp_path / "preview.pdf"
        html_path.write_text(
            '<html><body>'
            '<div class="a4-page day-page single-day-page" data-day="Day 1">'
            '<section class="day-section">'
            '<div class="day-kicker">DAY 1 ✦ VOSS ✦ 9th of June</div>'
            '<div class="day-title">Voss Image Test</div>'
            '<div class="intro">A short day with enough room for a lower-half image.</div>'
            '</section>'
            '<div class="day-image-slot" data-image-path="missing/external/image.webp">'
            f'<img class="day-image-preview-img" src="{data_uri}" alt="embedded" />'
            '</div>'
            '</div>'
            '</body></html>',
            encoding="utf-8",
        )

        export_html_to_pdf(html_path, pdf_path)
        try:
            import fitz
        except Exception as exc:  # pragma: no cover - local dependency guard
            raise AssertionError(f"PyMuPDF/fitz is required for PDF image checks: {exc}")
        document = fitz.open(pdf_path)
        try:
            images = document.load_page(0).get_images(full=True)
            if not images:
                raise AssertionError("PDF should use the embedded preview image when the file path is unavailable.")
        finally:
            document.close()
