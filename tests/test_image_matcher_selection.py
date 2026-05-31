import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from image_test_helpers import assert_equal, assert_contains
from image_matcher import get_image_bank_diagnostics, scan_image_bank, select_day_image, select_day_images

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


def test_default_fallback_prefers_semantic_match_over_season_only_match():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Summer_City_Sunset_Skyline_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(default_dir / "Default_Winter_Northern_Lights_01.jpg", format="JPEG")

        match = select_day_image(
            "Day 1",
            [
                {
                    "day": "Day 1",
                    "date": "15.01.2027",
                    "city": "Helsinki",
                    "title": "Guided walking tour through the city centre",
                    "details": "Architecture, streets and skyline views.",
                }
            ],
            bank,
        )
        if not match:
            raise AssertionError("Default fallback should provide a city image for a city sightseeing day.")
        assert_contains(
            Path(match["path"]).name,
            "City_Sunset_Skyline",
            "A city sightseeing day should prefer a city Default image over an unrelated winter aurora image.",
        )


def test_default_fallback_prefers_road_image_for_coach_transfer():
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        bank = Path(tmp) / "image_bank"
        default_dir = bank / "Default"
        default_dir.mkdir(parents=True)
        Image.new("RGB", (40, 25), (40, 100, 140)).save(default_dir / "Default_Winter_Snowy_Winter_Road_01.jpg", format="JPEG")
        Image.new("RGB", (40, 25), (5, 20, 70)).save(default_dir / "Default_Winter_Northern_Lights_01.jpg", format="JPEG")

        match = select_day_image(
            "Day 5",
            [
                {
                    "day": "Day 5",
                    "date": "18.11.2026",
                    "city": "Saariselkä",
                    "title": "Coach transfer to Saariselkä",
                    "details": "Long distance comfortable panorama coach transfer by road.",
                }
            ],
            bank,
        )
        if not match:
            raise AssertionError("Coach transfer day should receive a relevant Default fallback image.")
        assert_contains(
            Path(match["path"]).name,
            "Road",
            "A coach transfer day should prefer a road/journey Default image.",
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


def test_strong_default_can_be_reused_in_app_preview_instead_of_showing_blank():
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
        matches = select_day_images_with_overrides(grouped, {}, app_root=Path(tmp), image_bank_scan_paths=[bank])
        if not matches.get("Day 1") or not matches.get("Day 2"):
            raise AssertionError("A strong contextual Default image may be reused rather than leaving later preview pages blank.")
        assert_equal(
            Path(matches["Day 1"]["path"]).name,
            Path(matches["Day 2"]["path"]).name,
            "The app preview wrapper should honor strong Default reuse selected by the matcher.",
        )
