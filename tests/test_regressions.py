import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from text_polish import (
    expand_time_with_duration,
    polish_client_text,
    polish_hotel_name,
    format_duration_display,
)
from generator import (
    create_whats_included,
    create_journey_arc,
    group_rows_by_day,
    create_day_intro,
    create_trip_glance,
)
from itinerary_parser import extract_duration_from_description, parse_itinerary
from normalizer import normalize_itinerary_rows
from image_matcher import scan_image_bank, select_day_image, select_day_images, get_image_bank_diagnostics
from layout_policy import (
    DEFAULT_DAY_PAGE_LAYOUT,
    DAY_PAGE_LAYOUTS,
    normalize_day_page_layout,
    is_day_packing_enabled,
    is_three_day_packing_enabled,
)
from pdf_exporter import calculate_day_image_layout, export_html_to_pdf, make_cover_cropped_image
from reportlab.lib.units import mm


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(
            f"{label}\nExpected: {expected!r}\nActual:   {actual!r}"
        )


def assert_contains(text, expected, label):
    if expected not in text:
        raise AssertionError(
            f"{label}\nExpected to find: {expected!r}\nActual text: {text!r}"
        )


def assert_not_contains(text, unexpected, label):
    if unexpected in text:
        raise AssertionError(
            f"{label}\nDid not expect to find: {unexpected!r}\nActual text: {text!r}"
        )


def count_pdf_pages(pdf_path):
    content = Path(pdf_path).read_bytes()
    return content.count(b"/Type /Page") - content.count(b"/Type /Pages")


def test_time_expansion():
    assert_equal(
        expand_time_with_duration("10:00 AM", "5 hours"),
        "10:00 AM - 3:00 PM",
        "Start time + duration should become a visible time range.",
    )

    assert_equal(
        extract_duration_from_description(
            "Tromsø: Fjord Tour | 9 AM | 5.5 Hrs | What's included?"
        ),
        "5 hours 30 minutes",
        "Parser should preserve decimal hour durations before display formatting.",
    )

    assert_equal(
        expand_time_with_duration("9:00 AM", "5.5 hours"),
        "9:00 AM - 2:30 PM",
        "Decimal hour durations should calculate the correct end time.",
    )

    assert_equal(
        expand_time_with_duration("10:00 AM", "1.5 hours"),
        "10:00 AM - 11:30 AM",
        "1.5 hours should calculate as 1 hour 30 minutes.",
    )

    assert_equal(
        expand_time_with_duration("8:00 PM", "6.5 hours"),
        "8:00 PM - 2:30 AM",
        "Decimal durations should cross midnight correctly.",
    )

    assert_equal(
        format_duration_display("5.5 Hrs"),
        "5 hours 30 minutes",
        "Decimal hour durations should display as clean hours and minutes.",
    )

    assert_equal(
        format_duration_display("1.5 Hrs"),
        "1 hour 30 minutes",
        "Singular duration wording should be clean.",
    )

    assert_equal(
        expand_time_with_duration("8:00 PM", "4 hours"),
        "8:00 PM - 12:00 AM",
        "Evening start time + duration should cross midnight correctly.",
    )

    assert_equal(
        expand_time_with_duration("10:30 AM - 7:30 PM", "2 hours"),
        "10:30 AM - 7:30 PM",
        "Existing time ranges should not be overwritten.",
    )

    assert_equal(
        expand_time_with_duration("10:30 AM / 1:30 PM", "2 hours"),
        "10:30 AM / 1:30 PM",
        "Alternative time options should not be overwritten.",
    )


def test_full_pasted_row_decimal_duration():
    raw = """
\tDay 9\tActivity\t\t04/10/2026\t\t\t\t\t\t\t\tTromso\t\"Tromsø: Fjord Tour of Kvaløya & Sommarøy  | 9 AM | 5.5 Hrs | What's included?

Pick-up/drop-off in central Tromsø
Knowledgeable, multilingual guide
Free photographs from the trip
2-course meal with coffee or tea\"
"""
    rows = parse_itinerary(raw)
    assert_equal(len(rows), 1, "The full pasted activity row should parse as one row.")
    assert_equal(rows[0].get("time"), "9:00 AM", "Pipe-style activity time should be extracted.")
    assert_equal(
        rows[0].get("duration"),
        "5 hours 30 minutes",
        "Full pasted rows should preserve decimal duration through parsing.",
    )
    normalized_rows = normalize_itinerary_rows(rows)
    assert_equal(
        normalized_rows[0].get("display_time"),
        "9:00 AM - 2:30 PM",
        "Display normalization should produce the final activity time range.",
    )
    assert_equal(
        normalized_rows[0].get("display_duration"),
        "5 hours 30 minutes",
        "Display normalization should preserve clean decimal duration wording.",
    )


def test_activity_includes_do_not_absorb_description_label():
    raw = """
Day 2	Activity	16.01.2027		Oslo: Oslo Center Guided Walking Tour - Time: 10:00 am - 12:00 pm - Meeting point: Near the University of Oslo - Includes: Guided walking tour, Local guide, City landmarks - Description: Explore central Oslo with a local guide, taking in key landmarks, city stories, and the atmosphere of the Norwegian capital.
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    assert_equal(len(rows), 1, "The activity row should parse as one row.")
    includes = rows[0].get("includes", [])
    assert_equal(
        includes,
        ["Guided walking tour", "Local guide", "City landmarks"],
        "Includes should stop before the Description label instead of turning prose into bullets.",
    )
    assert_not_contains(
        "\n".join(includes).lower(),
        "description",
        "Description labels should not leak into inclusion bullets.",
    )


def test_text_polish_regressions():
    assert_equal(
        polish_client_text("hot drinks & snacks or cookies"),
        "Hot drinks and snacks or cookies",
        "Hot drinks inclusion should be client-facing and capitalized.",
    )

    assert_equal(
        polish_hotel_name("Santa's Hotel Santa Claus Korkalonkatu 29"),
        "Santa's Hotel Santa Claus",
        "Hotel street address should be removed from the hotel name.",
    )


def test_whats_included_nights_wording():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Test City",
            "hotel_name": "Test Hotel",
            "hotel_nights": "1",
            "meal_plan": "breakfast",
            "title": "Test Hotel",
            "details": "Breakfast included",
        },
        {
            "day": "Day 2",
            "type": "Departure",
            "effective_type": "Departure",
            "city": "Test City",
            "title": "Departure from Test City",
            "details": "Transfer to the airport",
        },
    ]

    grouped = group_rows_by_day(rows)
    included = create_whats_included(rows, grouped)
    joined = "\n".join(included)

    assert_contains(
        joined,
        "1 night as specified",
        "Hotel nights wording should be singular when there is 1 night.",
    )

    assert_not_contains(
        joined,
        "1 nights as specified",
        "Hotel nights wording should not use plural for 1 night.",
    )

    assert_not_contains(
        joined,
        "travel nights",
        "Hotel nights wording should not mention travel nights.",
    )


def test_journey_arc_normal_hotel_not_experience():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Helsinki",
            "hotel_name": "Scandic Grand Marina",
            "title": "Scandic Grand Marina",
            "details": "Standard Double Room - Breakfast included",
        }
    ]

    grouped = group_rows_by_day(rows)
    arc = create_journey_arc(grouped)
    text = " ".join(item.get("experience", "") for item in arc)

    assert_not_contains(
        text.lower(),
        "comfortable hotel stay",
        "Normal hotel stays should not be marketed as journey arc experiences.",
    )


def test_activity_intro_variation_not_templated():
    rows = [
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Helsinki",
            "title": "City Highlights Tour",
            "details": "Guided city sightseeing",
        }
    ]
    intro = create_day_intro(rows, detail_level="Rich descriptive")
    assert_not_contains(
        intro,
        "Today, you will enjoy",
        "Activity-led day intros should not use repeated templated wording.",
    )
    assert_not_contains(
        intro,
        "adding a meaningful experience",
        "Activity-led day intros should avoid generic filler wording.",
    )


def test_trip_glance_normal_hotels_are_arranged_accommodation():
    rows = [
        {
            "day": "Day 1",
            "type": "Hotel",
            "effective_type": "Hotel",
            "city": "Helsinki",
            "hotel_name": "Scandic Grand Marina",
            "title": "Scandic Grand Marina",
            "details": "Standard Double Room - Breakfast included",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Helsinki",
            "title": "City Highlights Tour",
            "details": "Guided city sightseeing",
        },
    ]
    grouped = group_rows_by_day(rows)
    glance = create_trip_glance(rows, grouped)
    assert_contains(
        glance.get("Travel Style", ""),
        "arranged accommodation",
        "Travel style should mention arranged accommodation for normal hotels.",
    )
    assert_not_contains(
        glance.get("Travel Style", ""),
        "comfortable hotel stays",
        "Normal hotels should not be marketed as comfortable hotel stays.",
    )
    assert_equal(
        glance.get("Duration", ""),
        "2 days / 1 night",
        "Trip glance should use singular night wording when appropriate.",
    )


def test_image_bank_matching_is_destination_specific():
    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        oslo_dir = bank / "Norway" / "Oslo"
        oslo_dir.mkdir(parents=True)
        (oslo_dir / "Oslo_Opera_House.jpg").write_bytes(b"fake image for matcher")

        candidates = scan_image_bank(bank)
        assert_equal(len(candidates), 1, "Image bank scanner should find image files by extension.")

        oslo_rows = [
            {
                "day": "Day 13",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Oslo",
                "title": "Oslo City Center Walking Tour",
                "details": "Guided walking tour near the University of Oslo, Parliament and City Hall.",
            }
        ]
        oslo_match = select_day_image("Day 13", oslo_rows, bank)
        if not oslo_match:
            raise AssertionError("Oslo day should find a suitable Oslo image.")
        assert_contains(
            str(oslo_match.get("path", "")).replace("\\", "/").lower(),
            "norway/oslo",
            "Oslo day image should come from the Oslo destination folder.",
        )

        bergen_rows = [
            {
                "day": "Day 10",
                "type": "Activity",
                "effective_type": "Activity",
                "city": "Bergen",
                "title": "Bergen Walking Tour",
                "details": "Harbour and city walk.",
            }
        ]
        assert_equal(
            select_day_image("Day 10", bergen_rows, bank),
            None,
            "Wrong-destination images should not be used as generic fallbacks.",
        )


def test_image_bank_missing_folder_is_safe():
    match = select_day_image(
        "Day 1",
        [{"city": "Oslo", "title": "Oslo City Center Walking Tour", "details": ""}],
        ROOT / "image_bank_missing",
    )
    assert_equal(match, None, "Missing image bank should fail safely without an image.")


def test_day_image_selection_does_not_reuse_images_and_prefers_available_season():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        oslo_dir = bank / "Norway" / "Oslo"
        oslo_dir.mkdir(parents=True)
        for name in [
            "Oslo_Summer_Opera_House.jpg",
            "Oslo_Summer_Parliament_City_Centre.jpg",
            "Oslo_Winter_Opera_House.jpg",
        ]:
            Image.new("RGB", (40, 25), (20, 40, 60)).save(oslo_dir / name, format="JPEG")

        grouped = {
            "Day 1": [
                {
                    "day": "Day 1",
                    "date": "15.07.2027",
                    "city": "Oslo",
                    "title": "Oslo Opera House Visit",
                    "details": "Waterfront walk",
                }
            ],
            "Day 2": [
                {
                    "day": "Day 2",
                    "date": "16.07.2027",
                    "city": "Oslo",
                    "title": "Oslo City Walking Tour",
                    "details": "Parliament and city centre",
                }
            ],
        }

        matches = select_day_images(grouped, bank)
        paths = [match["path"] for match in matches.values() if match]
        assert_equal(len(paths), 2, "Two Oslo days should receive two images when available.")
        assert_equal(len(set(paths)), 2, "The same image file should not be reused across days.")
        if not all("Summer" in Path(path).name for path in paths):
            raise AssertionError("Summer-dated itineraries should prefer available Summer images.")

        winter_match = select_day_image(
            "Day 3",
            [
                {
                    "day": "Day 3",
                    "date": "15.01.2027",
                    "city": "Oslo",
                    "title": "Oslo Opera House Visit",
                    "details": "Waterfront walk",
                }
            ],
            bank,
        )
        if not winter_match or "Winter" not in Path(winter_match["path"]).name:
            raise AssertionError("Winter-dated itineraries should prefer available Winter images.")



def test_root_default_fallback_is_used_when_destination_missing_and_is_relevant():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (5, 20, 70)).save(
            default_dir / "Default_Winter_Northern_Lights_01.jpg", format="JPEG"
        )
        Image.new("RGB", (40, 25), (40, 100, 140)).save(
            default_dir / "Default_Summer_Scenic_Fjord_View_01.jpg", format="JPEG"
        )

        match = select_day_image(
            "Day 1",
            [
                {
                    "day": "Day 1",
                    "date": "15.01.2027",
                    "city": "Narvik",
                    "title": "Northern lights evening experience",
                    "details": "Aurora viewing and winter sky photography.",
                }
            ],
            bank,
        )
        if not match:
            raise AssertionError("Missing destination should fall back to the root Default image bank.")
        assert_contains(
            Path(match["path"]).name,
            "Northern_Lights",
            "Default fallback should choose a semi-relevant northern-lights image when the day mentions aurora.",
        )
        assert_contains(
            str(match.get("reason", "")),
            "global default fallback",
            "Default fallback matches should explain that they came from the global default pool.",
        )


def test_destination_specific_image_wins_over_default_fallback():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        oslo_dir = bank / "Norway" / "Oslo"
        default_dir = bank / "Default"
        oslo_dir.mkdir(parents=True)
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (20, 40, 60)).save(oslo_dir / "Oslo_Summer_Opera_House_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (20, 40, 60)).save(default_dir / "Default_Summer_City_Sunset_Skyline_01.jpg", format="JPEG")

        match = select_day_image(
            "Day 1",
            [
                {
                    "day": "Day 1",
                    "date": "15.07.2027",
                    "city": "Oslo",
                    "title": "Oslo Opera House and city waterfront",
                    "details": "City sightseeing near the harbour.",
                }
            ],
            bank,
        )
        if not match:
            raise AssertionError("Oslo day should receive an Oslo image.")
        assert_contains(
            str(match.get("path", "")).replace("\\", "/"),
            "Norway/Oslo",
            "Destination-specific folders should beat the root Default fallback.",
        )


def test_default_fallback_does_not_reuse_images_until_needed():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        for name in [
            "Default_Summer_Scenic_Fjord_View_01.jpg",
            "Default_Summer_Aerial_Fjord_View_01.jpg",
        ]:
            Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / name, format="JPEG")

        grouped = {
            "Day 1": [{"day": "Day 1", "date": "15.07.2027", "city": "Geilo", "title": "Scenic fjord route", "details": "Fjord views."}],
            "Day 2": [{"day": "Day 2", "date": "16.07.2027", "city": "Lillehammer", "title": "Fjord viewpoint", "details": "Scenic landscape."}],
        }
        matches = select_day_images(grouped, bank)
        paths = [match["path"] for match in matches.values() if match]
        assert_equal(len(paths), 2, "Two missing destinations should receive two Default fallback images when available.")
        assert_equal(len(set(paths)), 2, "Default fallback images should not be reused within the same itinerary.")


def test_multi_country_external_image_bank_paths_are_supported():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        local_bank = Path(tmp) / "local_image_bank"
        external_bank = Path(tmp) / "external_image_bank"
        (local_bank / "Default").mkdir(parents=True)
        (external_bank / "Finland" / "Helsinki").mkdir(parents=True)
        Image.new("RGB", (40, 25), (40, 100, 140)).save(local_bank / "Default" / "Default_Summer_City_Sunset_Skyline_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (20, 40, 60)).save(external_bank / "Finland" / "Helsinki" / "Helsinki_Summer_City_Centre_01.jpg", format="JPEG")

        match = select_day_image(
            "Day 1",
            [
                {
                    "day": "Day 1",
                    "date": "15.07.2027",
                    "city": "Helsinki",
                    "title": "Helsinki city centre walking tour",
                    "details": "Guided sightseeing in Finland.",
                }
            ],
            [external_bank, local_bank],
        )
        if not match:
            raise AssertionError("Multi-country external image bank should be scanned.")
        assert_contains(
            str(match.get("path", "")).replace("\\", "/"),
            "Finland/Helsinki",
            "Exact country/destination matches in an external image bank should work for future Nordic countries.",
        )

def test_swedish_itinerary_uses_root_default_when_no_sweden_images_exist():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        local_bank = Path(tmp) / "image_bank"
        default_dir = local_bank / "Default"
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (5, 20, 70)).save(default_dir / "Default_Winter_Northern_Lights_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Winter_Reindeer_Winter_Forest_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Summer_City_Sunset_Skyline_01.jpg", format="JPEG")

        grouped = {
            "Day 1": [
                {
                    "day": "Day 1",
                    "date": "10.02.2027",
                    "city": "Stockholm",
                    "title": "Old Town and Waterfront Walking Tour",
                    "details": "Historic streets, colourful buildings, harbourfront views and island scenery.",
                }
            ],
            "Day 2": [
                {
                    "day": "Day 2",
                    "date": "11.02.2027",
                    "city": "Kiruna",
                    "title": "Northern Lights Evening Search",
                    "details": "Arctic night sky, aurora viewing and snowy landscapes.",
                }
            ],
        }
        matches = select_day_images(grouped, local_bank)
        if not matches.get("Day 1") or not matches.get("Day 2"):
            raise AssertionError("Swedish destinations without Sweden folders should still receive root Default fallback images.")
        assert_contains(
            str(matches["Day 2"].get("path", "")).replace("\\", "/"),
            "Default/Default_Winter_Northern_Lights",
            "Northern lights text should pick a relevant root Default aurora image.",
        )


def test_image_bank_diagnostics_counts_root_default_images():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        (bank / "Default").mkdir(parents=True)
        (bank / "Norway" / "Oslo").mkdir(parents=True)
        Image.new("RGB", (40, 25), (5, 20, 70)).save(bank / "Default" / "Default_Winter_Northern_Lights_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (20, 40, 60)).save(bank / "Norway" / "Oslo" / "Oslo_Summer_Opera_House_01.jpg", format="JPEG")

        diagnostics = get_image_bank_diagnostics(bank)
        assert_equal(diagnostics["total_images"], 2, "Diagnostics should count all scanned images.")
        assert_equal(diagnostics["default_images"], 1, "Diagnostics should count root Default images.")
        assert_equal(diagnostics["destination_images"], 1, "Diagnostics should count destination images separately.")

def test_layout_policy_one_day_per_page():
    assert_equal(
        DEFAULT_DAY_PAGE_LAYOUT,
        "One day per page",
        "Premium visual layout should default to one day per A4 page.",
    )
    assert_equal(
        DAY_PAGE_LAYOUTS,
        ["One day per page"],
        "Only one-day-per-page layout should be exposed while image placement is active.",
    )
    assert_equal(
        normalize_day_page_layout("Smart compact pages"),
        "One day per page",
        "Legacy compact page settings should normalize to one-day-per-page.",
    )
    assert_equal(
        normalize_day_page_layout("3-days per page"),
        "One day per page",
        "Legacy 3-day page settings should normalize to one-day-per-page.",
    )
    assert_equal(
        is_day_packing_enabled("Smart compact pages"),
        False,
        "Day packing should be disabled for the v36 visual layout path.",
    )
    assert_equal(
        is_three_day_packing_enabled("3-days per page"),
        False,
        "Three-day packing should be disabled for the v36 visual layout path.",
    )


def test_pdf_day_image_layout_rules():
    content_height = 720
    minimum = 40 * mm

    light_day_layout = calculate_day_image_layout(
        used_height=120,
        content_height=content_height,
        gap=15,
        half_offset=7.5,
        min_height=minimum,
    )
    if not light_day_layout:
        raise AssertionError("Light days should have room for a lower-half image.")
    spacer, image_height = light_day_layout
    assert_equal(
        round(120 + spacer, 1),
        367.5,
        "Image should not start above the halfway point plus offset.",
    )
    if image_height < minimum:
        raise AssertionError("Image height should respect the minimum height threshold.")

    bleed_layout = calculate_day_image_layout(
        used_height=120,
        content_height=content_height,
        gap=15,
        half_offset=7.5,
        min_height=minimum,
        bottom_bleed=62.4,
    )
    if not bleed_layout:
        raise AssertionError("Bottom-bleed image layout should still be allowed when there is room.")
    _, bleed_image_height = bleed_layout
    if bleed_image_height <= image_height:
        raise AssertionError("Bottom-bleed images should extend below the normal content area to the page edge.")

    heavy_day_layout = calculate_day_image_layout(
        used_height=650,
        content_height=content_height,
        gap=15,
        half_offset=7.5,
        min_height=minimum,
    )
    assert_equal(
        heavy_day_layout,
        None,
        "Text-heavy days should skip images when there is not enough usable space.",
    )


def test_pdf_export_places_day_image_from_current_page_story():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        image_path = tmp_path / "Oslo_Test_Image.jpg"
        image = Image.new("RGB", (320, 190))
        pixels = image.load()
        for x in range(320):
            for y in range(190):
                pixels[x, y] = (x % 256, y % 256, (x * y) % 256)
        image.save(image_path, format="JPEG", quality=88)

        html_path = tmp_path / "preview.html"
        pdf_path = tmp_path / "preview.pdf"
        html_content = (
            '<html><body>'
            '<div class="a4-page cover-page">'
            '<div class="cover-kicker">Curated Travel Itinerary</div>'
            '<div class="cover-title">Image Test</div>'
            '</div>'
            '<div class="a4-page day-page single-day-page" data-day="Day 1">'
            '<section class="day-section">'
            '<div class="day-label">Day 1</div>'
            '<div class="day-title">Oslo Image Test</div>'
            '<div class="city">Oslo</div>'
            '<div class="intro">A short Oslo day with enough room for a lower-half image.</div>'
            '<div class="content-block"><div class="block-heading">Morning Experience</div><div class="block-title">Oslo City Walk</div></div>'
            '</section>'
            f'<div class="day-image-slot" data-image-path="{image_path}"></div>'
            '</div>'
            '</body></html>'
        )
        html_path.write_text(html_content, encoding="utf-8")

        export_html_to_pdf(html_path, pdf_path)
        if pdf_path.stat().st_size < 10_000:
            raise AssertionError("PDF day image should be inserted when the current page has enough room.")
        assert_equal(
            count_pdf_pages(pdf_path),
            2,
            "Day image rendering should not create an image-only continuation page.",
        )

        try:
            import fitz
        except Exception as exc:  # pragma: no cover - local dependency guard
            raise AssertionError(f"PyMuPDF/fitz is required for rendered PDF image smoke checks: {exc}")

        document = fitz.open(pdf_path)
        try:
            day_page = document.load_page(1)
            pixmap = day_page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            bottom_center = pixmap.pixel(pixmap.width // 2, pixmap.height - 1)
            page_bg = (244, 239, 232)
            if sum(abs(int(bottom_center[i]) - page_bg[i]) for i in range(3)) < 20:
                raise AssertionError("Day image should touch the physical lower page edge, not stop above the margin.")
        finally:
            document.close()


def test_cover_crop_protects_upper_image_content():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "Aurora_Portrait.jpg"
        image = Image.new("RGB", (100, 300), (0, 0, 180))
        pixels = image.load()
        for x in range(100):
            for y in range(300):
                if y < 80:
                    pixels[x, y] = (0, 220, 80)  # bright upper sky detail
                elif y > 220:
                    pixels[x, y] = (80, 45, 20)
        image.save(source_path, format="JPEG", quality=95)

        cropped_path = make_cover_cropped_image(source_path, 400, 200, tmp_path)
        if not cropped_path:
            raise AssertionError("Cover crop should create a temporary image.")

        with Image.open(cropped_path) as cropped:
            top_pixel = cropped.getpixel((cropped.width // 2, 5))
            if top_pixel[1] < 120:
                raise AssertionError(
                    "Vertical cover crop should preserve upper sky/aurora detail better than a center crop."
                )



def test_cover_crop_focus_options_change_vertical_crop():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "Tall_Image.jpg"
        image = Image.new("RGB", (100, 300), (0, 0, 0))
        pixels = image.load()
        for x in range(100):
            for y in range(300):
                if y < 80:
                    pixels[x, y] = (0, 220, 80)
                elif y > 220:
                    pixels[x, y] = (220, 60, 20)
                else:
                    pixels[x, y] = (20, 20, 180)
        image.save(source_path, format="JPEG", quality=95)

        top_path = make_cover_cropped_image(source_path, 400, 200, tmp_path, crop_focus="top")
        bottom_path = make_cover_cropped_image(source_path, 400, 200, tmp_path, crop_focus="bottom")
        if not top_path or not bottom_path:
            raise AssertionError("Cover crop should create focus-specific temporary images.")

        with Image.open(top_path) as top_crop, Image.open(bottom_path) as bottom_crop:
            top_pixel = top_crop.getpixel((top_crop.width // 2, 5))
            bottom_pixel = bottom_crop.getpixel((bottom_crop.width // 2, bottom_crop.height - 5))
            if top_pixel[1] < 120:
                raise AssertionError("Top crop focus should keep upper sky/aurora detail visible.")
            if bottom_pixel[0] < 120:
                raise AssertionError("Bottom crop focus should keep lower foreground detail visible.")




def test_day_rendering_packing_helpers_are_self_contained_after_split():
    from ui.day_rendering import can_pack_days, can_pack_three_days

    rows = [
        {
            "day": "Day 1",
            "type": "Leisure",
            "effective_type": "Leisure",
            "city": "Oslo",
            "title": "Spend time at leisure",
            "details": "Relaxed day.",
        }
    ]

    assert_equal(
        can_pack_days("Day 1", rows, "Day 2", rows, {"day_page_layout": "One day per page"}),
        False,
        "Day packing helper should be self-contained and disabled for the current one-day layout.",
    )
    assert_equal(
        can_pack_three_days([("Day 1", rows), ("Day 2", rows), ("Day 3", rows)], {"day_page_layout": "One day per page"}),
        False,
        "Three-day packing helper should be self-contained and disabled for the current one-day layout.",
    )

def test_apply_output_edits_preserves_activity_time_range_after_split():
    import types

    sys.modules.setdefault("streamlit", types.SimpleNamespace(session_state={}))
    from ui.output_edits import apply_output_edits

    rows = [
        {
            "day": "Day 1",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Tromsø",
            "title": "Fjord Tour",
            "time": "9:00 AM",
            "duration": "5 hours 30 minutes",
        }
    ]

    edited_rows = apply_output_edits(rows, {"rows": {}})
    assert_equal(
        edited_rows[0].get("time"),
        "9:00 AM - 2:30 PM",
        "Output edit application should keep activity time ranges working after module split.",
    )

def test_visual_editor_html_sanitizer():
    from ui.editor_sanitizer import clean_visual_editor_html

    dirty = '<div class="content-block" onclick="bad()" style="color:red"><script>alert(1)</script><div class="section-title">Travel Arrangements</div><div class="body-text">Safe text</div></div>'
    clean = clean_visual_editor_html(dirty)
    assert_contains(clean, "Travel Arrangements", "Sanitizer should preserve editable day content.")
    assert_contains(clean, "Safe text", "Sanitizer should preserve body text.")
    assert_not_contains(clean.lower(), "script", "Sanitizer should remove script tags.")
    assert_not_contains(clean.lower(), "onclick", "Sanitizer should remove event attributes.")
    assert_not_contains(clean.lower(), "style=", "Sanitizer should remove inline styles.")



def test_final_page_notes_helper_is_self_contained_after_split():
    from ui.final_pages import get_important_travel_notes

    notes = get_important_travel_notes({"important_travel_notes_text": "First note\nSecond note"})
    assert_equal(
        notes,
        ["First note", "Second note"],
        "Final-page notes helper should import text conversion dependencies after module split.",
    )


def test_day_page_rendering_helpers_are_self_contained_after_split():
    from ui.day_pages import render_split_list_pages, render_text_paragraph_page, get_day_pack_stats

    list_html = render_split_list_pages("What’s included", ["Hotel", "Transfer"], items_per_page=10)
    assert_contains(list_html, "What’s included", "Split list pages should render after module split.")
    assert_contains(list_html, "Hotel", "Split list pages should include list items after module split.")

    notes_html = render_text_paragraph_page("Important travel notes", ["Schedules may change."])
    assert_contains(notes_html, "Important travel notes", "Text paragraph pages should render after module split.")
    assert_contains(notes_html, "Schedules may change.", "Text paragraph pages should include note text after module split.")

    stats = get_day_pack_stats("Day 1", [{"type": "Activity", "effective_type": "Activity", "title": "Walking Tour"}], {})
    assert_equal(stats["activity_count"], 1, "Day packing stats should import row-type helpers after module split.")


def test_activity_block_helpers_are_self_contained_after_split():
    from ui.day_blocks import build_activity_block

    row = {
        "type": "Activity",
        "effective_type": "Activity",
        "title": "Northern Lights Experience",
        "time": "8:00 PM",
        "duration": "2 hours",
        "includes": ["Local guide", "Northern lights search"],
    }
    block = build_activity_block(row)
    assert_contains(block["html"], "Northern Lights Experience", "Activity block should render after module split.")
    assert_contains(block["html"], "Local guide", "Activity inclusions should render after module split.")


def test_parser_split_public_imports_remain_stable():
    from itinerary_parser import (
        clean_space,
        normalize_time_text,
        extract_duration_from_description,
        parse_itinerary,
    )
    from parser_modules.parser_main import parse_itinerary as split_parse_itinerary

    assert_equal(clean_space("  Oslo   City  "), "Oslo City", "Parser wrapper should still expose clean_space.")
    assert_equal(normalize_time_text("20:00"), "8:00 PM", "Parser wrapper should still expose time normalization.")
    assert_equal(
        extract_duration_from_description("Tromsø: Fjord Tour | 9 AM | 5.5 Hrs | What's included?"),
        "5 hours 30 minutes",
        "Parser wrapper should still expose extraction helpers after split.",
    )

    raw = "Day 1\tActivity\t01.01.2027\t\tOslo: Guided Walk - Time: 10:00 am - 12:00 pm - Includes: Guide"
    assert_equal(
        parse_itinerary(raw),
        split_parse_itinerary(raw),
        "Compatibility wrapper should return the same parser output as the split parser implementation.",
    )

def run_all():
    tests = [
        test_time_expansion,
        test_full_pasted_row_decimal_duration,
        test_activity_includes_do_not_absorb_description_label,
        test_text_polish_regressions,
        test_whats_included_nights_wording,
        test_journey_arc_normal_hotel_not_experience,
        test_activity_intro_variation_not_templated,
        test_trip_glance_normal_hotels_are_arranged_accommodation,
        test_image_bank_matching_is_destination_specific,
        test_image_bank_missing_folder_is_safe,
        test_day_image_selection_does_not_reuse_images_and_prefers_available_season,
        test_root_default_fallback_is_used_when_destination_missing_and_is_relevant,
        test_destination_specific_image_wins_over_default_fallback,
        test_default_fallback_does_not_reuse_images_until_needed,
        test_multi_country_external_image_bank_paths_are_supported,
        test_swedish_itinerary_uses_root_default_when_no_sweden_images_exist,
        test_image_bank_diagnostics_counts_root_default_images,
        test_layout_policy_one_day_per_page,
        test_pdf_day_image_layout_rules,
        test_pdf_export_places_day_image_from_current_page_story,
        test_cover_crop_protects_upper_image_content,
        test_cover_crop_focus_options_change_vertical_crop,
        test_day_rendering_packing_helpers_are_self_contained_after_split,
        test_apply_output_edits_preserves_activity_time_range_after_split,
        test_visual_editor_html_sanitizer,
        test_final_page_notes_helper_is_self_contained_after_split,
        test_day_page_rendering_helpers_are_self_contained_after_split,
        test_activity_block_helpers_are_self_contained_after_split,
        test_parser_split_public_imports_remain_stable,
    ]

    for test in tests:
        test()

    print(f"All regression tests passed ({len(tests)} tests).")



if __name__ == "__main__":
    run_all()
