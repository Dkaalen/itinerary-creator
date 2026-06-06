from pathlib import Path

from app_modules.image_gateway import (
    connect_image_bank_for_picture_stage,
    image_bank_is_ready_for_client_pictures,
)
from images.replacement_options import (
    list_replacement_image_options,
    list_replacement_image_options_for_rows,
)


def _write_placeholder(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")


def test_image_bank_gateway_accepts_only_real_destination_bank():
    assert image_bank_is_ready_for_client_pictures({"full_bank_found": True, "missing_full_bank": False})
    assert not image_bank_is_ready_for_client_pictures({"full_bank_found": False, "missing_full_bank": True})
    assert not image_bank_is_ready_for_client_pictures({"default_only": True, "missing_full_bank": True})


def test_image_bank_gateway_does_not_connect_when_bank_is_ready():
    calls = {"connect": 0}

    def status_func():
        return {"full_bank_found": True, "missing_full_bank": False, "destination_image_count": 8}

    def connect_func():  # pragma: no cover - should not run
        calls["connect"] += 1
        return {"full_bank_found": False, "missing_full_bank": True}

    result = connect_image_bank_for_picture_stage(status_func, connect_func)

    assert result.ready is True
    assert result.attempted_connection is False
    assert calls["connect"] == 0


def test_image_bank_gateway_blocks_default_only_after_failed_connection():
    def status_func():
        return {
            "full_bank_found": False,
            "missing_full_bank": True,
            "default_only": True,
            "blocking_message": "Full destination image bank is missing.",
        }

    def connect_func():
        return {
            "full_bank_found": False,
            "missing_full_bank": True,
            "default_only": True,
            "blocking_message": "Full destination image bank is missing.",
            "setup_status": {"ok": False, "code": "bootstrap_disabled"},
        }

    result = connect_image_bank_for_picture_stage(status_func, connect_func)

    assert result.ready is False
    assert result.attempted_connection is True
    assert result.setup_status["code"] == "bootstrap_disabled"
    assert "Full destination image bank is missing" in result.message


def test_image_bank_gateway_allows_picture_stage_after_connection_succeeds():
    def status_func():
        return {"full_bank_found": False, "missing_full_bank": True}

    def connect_func():
        return {
            "full_bank_found": True,
            "missing_full_bank": False,
            "destination_image_count": 12,
            "setup_status": {"ok": True, "code": "fetched_zip"},
        }

    result = connect_image_bank_for_picture_stage(status_func, connect_func)

    assert result.ready is True
    assert result.attempted_connection is True
    assert result.status["destination_image_count"] == 12


def test_normal_replacement_lists_hide_default_images_even_when_full_bank_exists(tmp_path):
    bank = tmp_path / "image_bank_full"
    oslo = bank / "Norway" / "Oslo" / "Oslo_Summer_City_Waterfront_01.webp"
    default = bank / "Default" / "Default_Summer_City_Sunset_Skyline_01.webp"
    _write_placeholder(oslo)
    _write_placeholder(default)

    city_options = list_replacement_image_options("Oslo", image_bank_scan_paths=[bank])
    assert [path.name for path in city_options] == [oslo.name]

    day_options = list_replacement_image_options_for_rows(
        "Day 1",
        [{"day": "Day 1", "city": "Oslo", "type": "Activity", "title": "Oslo Walking Tour", "details": "Waterfront city landmarks."}],
        image_bank_scan_paths=[bank],
    )
    assert day_options
    assert all(option["city"] != "Default" for option in day_options)


def test_explicit_replacement_fallback_can_still_show_default_options(tmp_path):
    bank = tmp_path / "image_bank_full"
    default = bank / "Default" / "Default_Summer_City_Sunset_Skyline_01.webp"
    _write_placeholder(bank / "Norway" / "Bergen" / "Bergen_Summer_City_01.webp")
    _write_placeholder(default)

    options = list_replacement_image_options(
        "Oslo",
        image_bank_scan_paths=[bank],
        allow_default_options=True,
    )

    assert [path.name for path in options] == [default.name]
