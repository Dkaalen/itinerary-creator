import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from image_test_helpers import assert_equal, assert_contains
from image_matcher import get_image_bank_diagnostics, scan_image_bank, select_day_image, select_day_images

def test_v36c72_app_image_bank_paths_prefer_full_then_fallback():
    import images.app_image_selection as app_images

    original_root = app_images.APP_ROOT
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full = root / "image_bank_full"
            fallback = root / "image_bank"
            full.mkdir()
            fallback.mkdir()
            app_images.APP_ROOT = root

            assert_equal(
                app_images.get_image_bank_paths(),
                [full, fallback],
                "App image helper should scan image_bank_full before image_bank when both exist.",
            )
            assert_equal(
                app_images.get_image_bank_path(),
                full,
                "App image helper should use image_bank_full as the primary writable bank when present.",
            )
    finally:
        app_images.APP_ROOT = original_root


def test_v36c72_app_image_bank_paths_fall_back_to_small_bank():
    import images.app_image_selection as app_images

    original_root = app_images.APP_ROOT
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fallback = root / "image_bank"
            fallback.mkdir()
            app_images.APP_ROOT = root

            assert_equal(
                app_images.get_image_bank_scan_paths(),
                [fallback],
                "App image helper should keep image_bank as fallback when image_bank_full is absent.",
            )
    finally:
        app_images.APP_ROOT = original_root



def test_app_image_bank_paths_prefer_submodule_full_bank_then_local_fallbacks():
    import images.app_image_selection as app_images

    original_root = app_images.APP_ROOT
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "itinerary-creator-git"
            submodule_full = root / "itinerary-image-bank" / "image_bank_full"
            local_full = root / "image_bank_full"
            fallback = root / "image_bank"
            submodule_full.mkdir(parents=True)
            local_full.mkdir(parents=True)
            fallback.mkdir(parents=True)
            app_images.APP_ROOT = root

            assert_equal(
                app_images.get_image_bank_scan_paths(),
                [submodule_full, local_full, fallback],
                "In-repo image-bank submodule should be scanned before in-repo fallback banks.",
            )
    finally:
        app_images.APP_ROOT = original_root


def test_app_image_bank_paths_prefer_submodule_before_sibling_full_bank():
    import images.app_image_selection as app_images

    original_root = app_images.APP_ROOT
    try:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root = parent / "itinerary-creator-git"
            submodule_full = root / "itinerary-image-bank" / "image_bank_full"
            sibling_full = parent / "itinerary-image-bank" / "image_bank_full"
            fallback = root / "image_bank"
            submodule_full.mkdir(parents=True)
            sibling_full.mkdir(parents=True)
            fallback.mkdir(parents=True)
            app_images.APP_ROOT = root

            assert_equal(
                app_images.get_image_bank_scan_paths(),
                [submodule_full, sibling_full, fallback],
                "GitHub/deployment submodule bank should be tried before local sibling bank.",
            )
    finally:
        app_images.APP_ROOT = original_root
