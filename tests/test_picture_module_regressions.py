from pathlib import Path

from tests.support.streamlit_stub import install_streamlit_stub

st = install_streamlit_stub()


def test_pdf_export_attempts_destination_bank_before_accepting_default_fallback(monkeypatch):
    from app_modules import export_image_validation

    st.session_state.clear()
    st.session_state.update(
        {
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
            "output_edits": {"pictures_added": True},
            "preview_signature": "sig-1",
            "itinerary_html": "",
        }
    )
    calls = {"connect": 0}

    def fake_grouped_days(state):
        return {"Day 1": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}]}

    def fake_status(required_destinations=None):
        return {
            "full_bank_found": False,
            "missing_full_bank": True,
            "default_only": True,
            "default_image_count": 2,
            "total_image_count": 2,
            "required_destinations": ["Norway/Oslo"],
            "required_destinations_ready": False,
        }

    def fake_connect(required_destinations=None):
        calls["connect"] += 1
        return {
            "full_bank_found": True,
            "missing_full_bank": False,
            "destination_image_count": 5,
            "required_destinations": ["Norway/Oslo"],
            "required_destinations_ready": True,
            "setup_status": {"ok": True, "code": "distribution_pack_installed"},
        }

    monkeypatch.setattr(export_image_validation, "image_grouped_days_from_state", fake_grouped_days)
    monkeypatch.setattr(export_image_validation, "image_bank_status", fake_status)
    monkeypatch.setattr(export_image_validation, "connect_remote_image_bank_if_missing", fake_connect)
    monkeypatch.setattr(export_image_validation, "destination_requests_from_rows", lambda grouped: ["Norway/Oslo"])
    monkeypatch.setattr(export_image_validation, "select_day_images_with_overrides", lambda grouped, edits: {"Day 1": {"path": "/bank/oslo.webp"}})
    monkeypatch.setattr(export_image_validation, "day_image_matches_from_preview_html", lambda html: {})

    ok, status, matches, grouped = export_image_validation.prepare_pdf_image_contract()

    assert ok is True
    assert calls["connect"] == 1
    assert status["required_destinations_ready"] is True
    assert matches["Day 1"]["path"] == "/bank/oslo.webp"
    assert grouped["Day 1"][0]["city"] == "Oslo"


def test_pdf_export_keeps_default_fallback_after_failed_destination_attempt(monkeypatch):
    from app_modules import export_image_validation

    st.session_state.clear()
    st.session_state.update(
        {
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
            "output_edits": {"pictures_added": True},
            "preview_signature": "sig-2",
            "itinerary_html": "",
        }
    )
    calls = {"connect": 0}

    fallback_status = {
        "full_bank_found": False,
        "missing_full_bank": True,
        "default_only": True,
        "default_image_count": 2,
        "total_image_count": 2,
        "required_destinations": ["Norway/Oslo"],
        "required_destinations_ready": False,
    }

    def fake_grouped_days(state):
        return {"Day 1": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}]}

    def fake_connect(required_destinations=None):
        calls["connect"] += 1
        return {**fallback_status, "setup_status": {"ok": False, "code": "network_error"}}

    monkeypatch.setattr(export_image_validation, "image_grouped_days_from_state", fake_grouped_days)
    monkeypatch.setattr(export_image_validation, "image_bank_status", lambda required_destinations=None: dict(fallback_status))
    monkeypatch.setattr(export_image_validation, "connect_remote_image_bank_if_missing", fake_connect)
    monkeypatch.setattr(export_image_validation, "destination_requests_from_rows", lambda grouped: ["Norway/Oslo"])
    monkeypatch.setattr(export_image_validation, "select_day_images_with_overrides", lambda grouped, edits: {"Day 1": {"path": "/bank/default.webp", "is_default": True}})
    monkeypatch.setattr(export_image_validation, "day_image_matches_from_preview_html", lambda html: {})

    ok, status, matches, _grouped = export_image_validation.prepare_pdf_image_contract()

    assert ok is True
    assert calls["connect"] == 1
    assert status["default_image_count"] == 2
    assert status["setup_status"]["code"] == "network_error"
    assert matches["Day 1"]["path"] == "/bank/default.webp"


def test_replacement_options_include_tiny_previews_for_visible_choices(monkeypatch):
    from visual_editor_component import editor_payload_images

    calls = []

    def fake_preview(path, option=False):
        calls.append((path, option))
        return f"preview:{Path(path).name}:{option}"

    monkeypatch.setattr(editor_payload_images, "get_image_preview_for_path", fake_preview)
    options = [{"path": f"/bank/image-{index}.jpg", "name": f"Image {index}"} for index in range(3)]

    enriched = editor_payload_images._with_option_previews(options, preview_limit=2)

    assert enriched[0]["preview_data_uri"] == "preview:image-0.jpg:True"
    assert enriched[1]["preview_data_uri"] == "preview:image-1.jpg:True"
    assert "preview_data_uri" not in enriched[2]
    assert all("data_uri" not in item for item in enriched)
    assert calls == [("/bank/image-0.jpg", True), ("/bank/image-1.jpg", True)]
