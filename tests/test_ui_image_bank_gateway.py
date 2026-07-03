from pathlib import Path

from app_modules.image_gateway import (
    connect_image_bank_for_picture_stage,
    destination_image_bank_is_ready_for_client_pictures,
    image_bank_is_ready_for_client_pictures,
    image_bank_should_attempt_destination_connection,
)
from images.replacement_options import (
    list_replacement_image_options,
    list_replacement_image_options_for_rows,
)


def _write_placeholder(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")


def test_image_bank_gateway_separates_destination_readiness_from_fallback_usability():
    real_status = {"full_bank_found": True, "missing_full_bank": False, "destination_image_count": 8}
    fallback_status = {"default_only": True, "missing_full_bank": True, "default_image_count": 3}
    missing_status = {"full_bank_found": False, "missing_full_bank": True, "default_image_count": 0, "total_image_count": 0}

    assert destination_image_bank_is_ready_for_client_pictures(real_status) is True
    assert image_bank_should_attempt_destination_connection(real_status) is False
    assert image_bank_is_ready_for_client_pictures(real_status) is True

    assert destination_image_bank_is_ready_for_client_pictures(fallback_status) is False
    assert image_bank_should_attempt_destination_connection(fallback_status) is True
    assert image_bank_is_ready_for_client_pictures(fallback_status) is True

    assert image_bank_is_ready_for_client_pictures(missing_status) is False


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


def test_stale_default_only_gateway_result_is_not_blocking():
    from app_modules.image_gateway_ui import _image_bank_gateway_is_blocking

    result = {
        "ready": False,
        "status": {"default_only": True, "missing_full_bank": True, "default_image_count": 2},
        "message": "Full destination image bank is missing.",
    }

    assert _image_bank_gateway_is_blocking(result) is False


def test_image_bank_gateway_attempts_destination_connection_before_default_only_fallback():
    calls = {"connect": 0}

    def status_func():
        return {
            "full_bank_found": False,
            "missing_full_bank": True,
            "default_only": True,
            "default_image_count": 2,
            "total_image_count": 2,
            "blocking_message": "Full destination image bank is missing.",
        }

    def connect_func():
        calls["connect"] += 1
        return {
            "full_bank_found": False,
            "missing_full_bank": True,
            "default_only": True,
            "default_image_count": 2,
            "total_image_count": 2,
            "blocking_message": "Full destination image bank is missing.",
            "setup_status": {"ok": False, "code": "bootstrap_disabled"},
        }

    result = connect_image_bank_for_picture_stage(status_func, connect_func)

    assert result.ready is True
    assert result.attempted_connection is True
    assert calls["connect"] == 1
    assert result.message == ""
    assert result.setup_status["code"] == "bootstrap_disabled"


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


def test_image_bank_gateway_keeps_existing_fallback_when_connection_returns_setup_only():
    def status_func():
        return {
            "full_bank_found": False,
            "missing_full_bank": True,
            "default_only": True,
            "default_image_count": 2,
            "total_image_count": 2,
        }

    def connect_func():
        return {"setup_status": {"ok": False, "code": "network_error", "message": "Could not fetch image bank."}}

    result = connect_image_bank_for_picture_stage(status_func, connect_func)

    assert result.ready is True
    assert result.attempted_connection is True
    assert result.status["default_image_count"] == 2
    assert result.setup_status["code"] == "network_error"


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
