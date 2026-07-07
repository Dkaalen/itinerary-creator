from __future__ import annotations

from pathlib import Path

from tests.support.streamlit_stub import install_streamlit_stub


def test_day_image_selection_treats_legacy_removed_choice_as_no_image(monkeypatch, tmp_path: Path) -> None:
    from images import day_image_selection

    monkeypatch.setattr(
        day_image_selection,
        "select_day_images",
        lambda grouped_days, image_bank_scan_paths, used_paths=None: {
            "Day 1": {"path": str(tmp_path / "auto-oslo.webp"), "reason": "auto fallback"}
        },
    )
    monkeypatch.setattr(day_image_selection, "image_bank_status_for_paths", lambda _paths: {"full_bank_found": True})

    matches = day_image_selection.select_day_images_with_overrides(
        {"Day 1": [{"city": "Oslo", "title": "Walk"}]},
        {"day_images": {"Day 1": {"mode": "removed", "removed": True, "path": "old-oslo.webp"}}},
        app_root=tmp_path,
        image_bank_scan_paths=[],
    )

    assert matches["Day 1"] is None


def test_cover_background_treats_legacy_removed_choice_as_no_image() -> None:
    from itinerary_generation.cover_assets import get_cover_image_choice

    choice = get_cover_image_choice(
        {"cover_image": {"mode": "removed", "removed": True, "path": "old-cover.webp", "crop_focus": "bottom"}},
        key="cover_image",
    )

    assert choice == {"mode": "none", "path": "", "crop_focus": "bottom"}


def test_pdf_image_contract_does_not_resurrect_removed_day_from_stale_preview(monkeypatch) -> None:
    st = install_streamlit_stub()
    from app_modules import export_image_validation

    monkeypatch.setattr(export_image_validation, "st", st)
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": "preview-removed",
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
            "output_edits": {
                "pictures_added": True,
                "day_images": {"Day 1": {"mode": "removed", "removed": True, "path": "old-oslo.webp"}},
            },
            "itinerary_html": (
                '<div class="a4-page day-page single-day-page" data-day="Day 1">'
                '<div class="day-image-slot" data-image-path="old-oslo.webp">'
                '<img class="day-image-preview-img" src="data:image/png;base64,AAAA" />'
                "</div></div>"
            ),
        }
    )

    monkeypatch.setattr(export_image_validation, "image_grouped_days_from_state", lambda _state: {"Day 1": [{"city": "Oslo"}]})
    monkeypatch.setattr(export_image_validation, "destination_requests_from_rows", lambda _grouped: ["Norway/Oslo"])
    monkeypatch.setattr(export_image_validation, "image_bank_storage_signature", lambda: "bank-v1")
    monkeypatch.setattr(
        export_image_validation,
        "image_bank_status",
        lambda _required=None: {"full_bank_found": True, "destination_image_count": 1, "total_image_count": 1},
    )
    monkeypatch.setattr(export_image_validation, "select_day_images_with_overrides", lambda _grouped, _edits: {"Day 1": None})

    ok, _status, matches, _grouped = export_image_validation.prepare_pdf_image_contract()

    assert ok is True
    assert matches["Day 1"] is None


def test_pdf_image_contract_cache_follows_image_bank_storage_signature(monkeypatch) -> None:
    st = install_streamlit_stub()
    from app_modules import export_image_validation

    monkeypatch.setattr(export_image_validation, "st", st)
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": "preview-current",
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
            "output_edits": {"pictures_added": True},
            "itinerary_html": "",
        }
    )
    bank = {"signature": "bank-v1", "path": "oslo-v1.webp"}

    monkeypatch.setattr(export_image_validation, "image_grouped_days_from_state", lambda _state: {"Day 1": [{"city": "Oslo"}]})
    monkeypatch.setattr(export_image_validation, "destination_requests_from_rows", lambda _grouped: ["Norway/Oslo"])
    monkeypatch.setattr(export_image_validation, "image_bank_storage_signature", lambda: bank["signature"])
    monkeypatch.setattr(
        export_image_validation,
        "image_bank_status",
        lambda _required=None: {
            "full_bank_found": True,
            "source_path": bank["signature"],
            "destination_image_count": 1,
            "total_image_count": 1,
        },
    )
    monkeypatch.setattr(
        export_image_validation,
        "select_day_images_with_overrides",
        lambda _grouped, _edits: {"Day 1": {"path": bank["path"]}},
    )

    ok, _status, matches, _grouped = export_image_validation.prepare_pdf_image_contract()
    assert ok is True
    assert matches["Day 1"]["path"] == "oslo-v1.webp"

    bank.update({"signature": "bank-v2", "path": "oslo-v2.webp"})
    ok, _status, matches, _grouped = export_image_validation.prepare_pdf_image_contract()

    assert ok is True
    assert matches["Day 1"]["path"] == "oslo-v2.webp"
