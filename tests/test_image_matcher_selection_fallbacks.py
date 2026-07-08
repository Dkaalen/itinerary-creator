import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from image_test_helpers import assert_equal, assert_contains
from image_matcher import get_image_bank_diagnostics, scan_image_bank, score_image_for_day, select_day_image, select_day_images

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



def test_self_drive_arrival_day_prefers_activity_destination_image_over_origin_city():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank_full"
        (bank / "Norway" / "Voss").mkdir(parents=True)
        (bank / "Default").mkdir(parents=True)
        Image.new("RGB", (40, 25), (20, 40, 60)).save(
            bank / "Norway" / "Voss" / "Voss_Summer_River_Valley_01.webp", format="WEBP"
        )
        Image.new("RGB", (40, 25), (40, 100, 140)).save(
            bank / "Default" / "Default_Summer_Scenic_Fjord_View_01.webp", format="WEBP"
        )

        rows = [
            {"day": "Day 1", "date": "09.06.2026", "type": "Arrival", "city": "Oslo", "title": "Welcome to Norway"},
            {"day": "Day 1", "date": "09.06.2026", "type": "Car", "city": "Oslo", "title": "Pick up your rental car"},
            {"day": "Day 1", "date": "09.06.2026", "type": "Drive", "city": "Oslo", "title": "Drive to Voss"},
            {"day": "Day 1", "date": "09.06.2026", "type": "Hotel", "city": "Voss", "title": "Scandic Voss"},
            {"day": "Day 1", "date": "09.06.2026", "type": "Activity", "city": "Voss", "title": "E-Mountain Bike Rental", "details": "Outdoor activity in Voss"},
        ]
        match = select_day_image("Day 1", rows, bank)
        if not match:
            raise AssertionError("Self-drive arrival day should receive a destination image.")
        assert_contains(
            str(match.get("path", "")).replace("\\", "/"),
            "Norway/Voss",
            "Image matching should use the day's main destination, not only the first origin city row.",
        )


def test_autumn_dates_do_not_force_summer_default_images():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Summer_Train_Window_Waterfall_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Summer_City_Sunset_Skyline_01.jpg", format="JPEG")

        match = select_day_image(
            "Day 1",
            [
                {
                    "day": "Day 1",
                    "date": "27.10.2026",
                    "type": "Hotel",
                    "city": "Helsinki",
                    "title": "Hotel Arthur",
                    "details": "Arrival day and accommodation in the city centre.",
                }
            ],
            bank,
        )
        if not match:
            raise AssertionError("Arrival/hotel day should still get a safe Default fallback when destination bank is missing.")
        assert_contains(
            Path(match["path"]).name,
            "City_Sunset_Skyline",
            "October should not be treated as summer and a hotel/arrival day should avoid train imagery.",
        )


def test_day_trip_to_known_destination_can_drive_image_city():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank_full"
        (bank / "Finland" / "Helsinki").mkdir(parents=True)
        (bank / "Estonia" / "Tallinn").mkdir(parents=True)
        Image.new("RGB", (40, 25), (40, 100, 140)).save(bank / "Finland" / "Helsinki" / "Helsinki_Summer_Harbour_01.webp", format="WEBP")
        Image.new("RGB", (40, 25), (40, 100, 140)).save(bank / "Estonia" / "Tallinn" / "Tallinn_Old_Town_01.webp", format="WEBP")

        match = select_day_image(
            "Day 2",
            [
                {
                    "day": "Day 2",
                    "date": "28.10.2026",
                    "type": "Activity",
                    "effective_type": "Activity",
                    "city": "Helsinki",
                    "title": "Excursion to Tallinn",
                    "details": "Self guided tour of Old Town Tallinn and Helsinki port transfers.",
                }
            ],
            bank,
        )
        if not match:
            raise AssertionError("Tallinn day trip should receive an image.")
        assert_contains(
            str(match.get("path", "")).replace("\\", "/"),
            "Estonia/Tallinn",
            "Day-trip image matching should prefer the explicit destination over the base city.",
        )


def test_arctic_resort_fallback_beats_generic_city_default():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Summer_Colorful_Nordic_Buildings_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(default_dir / "Default_Winter_Northern_Lights_Landscape_01.jpg", format="JPEG")

        match = select_day_image(
            "Day 5",
            [
                {
                    "day": "Day 5",
                    "date": "31.10.2026",
                    "type": "Hotel",
                    "city": "Kakslauttanen",
                    "title": "Kakslauttanen Arctic Resort",
                    "details": "Small Glass Igloo, breakfast and dinner included.",
                }
            ],
            bank,
        )
        if not match:
            raise AssertionError("Arctic resort day should receive a contextual fallback image.")
        assert_contains(
            Path(match["path"]).name,
            "Northern_Lights",
            "Glass igloo/arctic resort days should avoid generic city-building Default imagery.",
        )


def test_app_preview_uses_default_only_bank_as_shared_fallback():
    from PIL import Image
    from images.day_image_selection import select_day_images_with_overrides

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Summer_City_Sunset_Skyline_01.jpg", format="JPEG")

        grouped = {
            "Day 1": [{"day": "Day 1", "date": "01.10.2027", "type": "Activity", "city": "Oslo", "title": "Oslo Walking Tour", "details": "City landmarks and skyline."}],
            "Day 2": [{"day": "Day 2", "date": "02.10.2027", "type": "Transfer", "city": "Oslo", "title": "Private Hotel to Airport", "details": "Private transfer from hotel to airport."}],
        }

        fallback_matches = select_day_images_with_overrides(grouped, {}, app_root=Path(tmp), image_bank_scan_paths=[bank])
        if not fallback_matches.get("Day 1") or not fallback_matches.get("Day 2"):
            raise AssertionError("Default-only image banks should remain usable fallback sources for normal picture review.")
        assert_equal(
            Path(fallback_matches["Day 1"]["path"]).name,
            Path(fallback_matches["Day 2"]["path"]).name,
            "Default fallback mode should preserve strong Default reuse selected by the matcher.",
        )

        blocked_matches = select_day_images_with_overrides(
            grouped,
            {"block_default_final_images": True},
            app_root=Path(tmp),
            image_bank_scan_paths=[bank],
        )
        assert_equal(
            blocked_matches,
            {"Day 1": None, "Day 2": None},
            "An explicit internal block flag should still disable bundled Default images for specialized checks.",
        )
