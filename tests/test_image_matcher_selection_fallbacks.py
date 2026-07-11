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


def test_default_bank_reuses_safe_summer_image_instead_of_forcing_winter_conflicts():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        summer_path = default_dir / "Default_Summer_Scenic_Fjord_View_01.webp"
        winter_path = default_dir / "Default_Winter_Northern_Lights_Mountains_01.webp"
        Image.new("RGB", (40, 25), (40, 100, 140)).save(summer_path, format="WEBP")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(winter_path, format="WEBP")

        matches = select_day_images(
            {
                "Day 1": [{"day": "Day 1", "date": "01.07.2027", "type": "Activity", "city": "Reykjavik", "title": "City walk"}],
                "Day 2": [{"day": "Day 2", "date": "02.07.2027", "type": "Activity", "city": "Reykjavik", "title": "Whale watching from the harbour"}],
                "Day 3": [{"day": "Day 3", "date": "03.07.2027", "type": "Activity", "city": "Reykjavik", "title": "Sky Lagoon spa ritual"}],
            },
            bank,
        )

        assert all(match for match in matches.values())
        assert {Path(match["path"]).name for match in matches.values()} == {summer_path.name}
        assert all("conflict:" not in str(match.get("reason", "")).lower() for match in matches.values())
        assert any("reused strong default" in str(match.get("reason", "")).lower() for match in matches.values())


def test_generic_winter_departure_avoids_specialty_reindeer_fallback():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        landscape_path = default_dir / "Default_Winter_Snowy_Forest_Landscape_01.webp"
        reindeer_path = default_dir / "Default_Winter_Reindeer_Sledding_01.webp"
        Image.new("RGB", (40, 25), (40, 100, 140)).save(landscape_path, format="WEBP")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(reindeer_path, format="WEBP")

        match = select_day_image(
            "Day 1",
            [{"day": "Day 1", "date": "15.12.2027", "type": "Departure", "city": "Tromso", "title": "Departure from Tromso Airport"}],
            bank,
        )

        assert match
        assert Path(match["path"]).name == landscape_path.name
        assert "conflict:" not in str(match.get("reason", "")).lower()


def test_matching_season_default_is_reused_before_wrong_season_image():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        winter_path = default_dir / "Default_Winter_Snowy_Forest_Landscape_01.webp"
        summer_path = default_dir / "Default_Summer_Golden_Hour_Lake_01.webp"
        Image.new("RGB", (40, 25), (40, 100, 140)).save(winter_path, format="WEBP")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(summer_path, format="WEBP")

        matches = select_day_images(
            {
                "Day 1": [{"day": "Day 1", "date": "14.12.2027", "type": "Hotel", "city": "Tromso", "title": "Winter stay"}],
                "Day 2": [{"day": "Day 2", "date": "15.12.2027", "type": "Departure", "city": "Tromso", "title": "Departure from Tromso Airport"}],
            },
            bank,
        )

        assert all(match for match in matches.values())
        assert {Path(match["path"]).name for match in matches.values()} == {winter_path.name}
        assert all("summer" not in Path(match["path"]).name.lower() for match in matches.values())


def test_golden_circle_does_not_infer_santa_theme():
    from images.metadata import infer_themes, tokenize

    themes = infer_themes(tokenize("Golden Circle route with Geysir and Gullfoss"))

    assert "santa" not in themes


def test_winter_city_day_does_not_use_reindeer_specialty_fallback():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        generic_path = default_dir / "Default_Winter_Snowy_Forest_Landscape_01.webp"
        reindeer_path = default_dir / "Default_Winter_Reindeer_Sledding_01.webp"
        Image.new("RGB", (40, 25), (40, 100, 140)).save(generic_path, format="WEBP")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(reindeer_path, format="WEBP")

        match = select_day_image(
            "Day 3",
            [{"day": "Day 3", "date": "15.12.2027", "type": "Activity", "city": "Bergen", "title": "Bergen walking tour and Fløibanen"}],
            bank,
        )

        assert match
        assert Path(match["path"]).name == generic_path.name


def test_non_rail_day_does_not_use_train_window_specialty_fallback():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        scenic_path = default_dir / "Default_Summer_Scenic_Fjord_View_01.webp"
        train_path = default_dir / "Default_Summer_Train_Window_Waterfall_01.webp"
        Image.new("RGB", (40, 25), (40, 100, 140)).save(scenic_path, format="WEBP")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(train_path, format="WEBP")

        match = select_day_image(
            "Day 4",
            [{"day": "Day 4", "date": "15.07.2027", "type": "Leisure", "city": "Vik", "title": "Day at leisure in Vík"}],
            bank,
        )

        assert match
        assert Path(match["path"]).name == scenic_path.name


def test_generic_view_and_express_words_do_not_create_specialty_themes():
    from images.metadata import infer_themes, tokenize

    themes = infer_themes(tokenize("ATV Quad Express with a scenic mountain view"))

    assert "train" not in themes
    assert "funicular" not in themes
