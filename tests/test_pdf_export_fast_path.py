from pathlib import Path
from tests.support.static_contracts import read_contract_text

from app_modules import export_actions
from app_modules.export_identity import export_signature_for_state
from tests.support.streamlit_stub import install_streamlit_stub


def test_current_pdf_creation_is_a_noop_fast_path(monkeypatch):
    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": "current-preview",
            "pdf_status": "Ready",
            "parsed_rows": [{"day": "1", "type": "activity", "title": "Walk Oslo"}],
            "output_edits": {"pictures_added": True},
        }
    )
    current_signature = export_signature_for_state(st.session_state)
    st.session_state.update(
        {
            "pdf_signature": current_signature,
            "pdf_bytes": b"%PDF-current",
            "export_pdf_signature": current_signature,
            "export_pdf_bytes": b"%PDF-current",
        }
    )

    def _should_not_run(*_args, **_kwargs):  # pragma: no cover - failure path
        raise AssertionError("Current PDF should not rebuild, revalidate, reconnect images, or render again.")

    monkeypatch.setattr(export_actions, "validate_for_generation", _should_not_run)
    monkeypatch.setattr(export_actions, "rebuild_current_preview", _should_not_run)
    monkeypatch.setattr(export_actions, "save_pdf_file", _should_not_run)

    assert export_actions.create_pdf_from_current_preview() is True
    assert st.session_state["pdf_status"] == "Ready"


def test_export_screen_does_not_offer_recreate_when_pdf_is_current():
    source = read_contract_text("app_modules/export_step.py")
    picture_source = read_contract_text("app_modules/picture_step.py")
    cta_source = read_contract_text("app_modules/picture_pdf_cta.py")

    assert "if readiness.pdf_ready:" in source
    assert source.index("if readiness.pdf_ready:") < source.index('st.button("Create PDF"')
    assert "render_picture_pdf_cta" in picture_source
    assert "if current_pdf_bytes():" in cta_source
    assert cta_source.index("if current_pdf_bytes():") < cta_source.index('st.button("Create PDF"')


def test_export_screen_clears_stale_pdf_commit_state_without_waiting():
    source = (
        read_contract_text("app_modules/export_step.py")
        + read_contract_text("app_modules/pdf_creation_request.py")
    )

    assert "visual_editor_export_commit_ready" not in source
    assert "Applying pending editor changes" not in source
    assert "clear_stale_pdf_editor_state()" in source
    assert "request_editor_save_before_pdf(st.session_state)" not in source
    assert "create_pdf_from_current_preview()" in source


def test_current_pdf_bytes_requires_a_current_preview_signature():
    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": None,
            "pdf_signature": None,
            "pdf_bytes": b"%PDF-stale",
            "export_pdf_signature": None,
            "export_pdf_bytes": b"%PDF-stale-export",
        }
    )

    assert export_actions.current_pdf_bytes() is None


def test_current_pdf_bytes_ignores_stale_editor_pdf_commit_state():
    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": "sig-1",
            "output_edits": {"pictures_added": True},
            "_pdf_after_visual_edit_commit_nonce": "2",
            "_visual_editor_export_commit_ready": False,
        }
    )
    current_signature = export_signature_for_state(st.session_state)
    st.session_state.update(
        {
            "pdf_signature": current_signature,
            "pdf_bytes": b"%PDF-current",
            "export_pdf_signature": current_signature,
            "export_pdf_bytes": b"%PDF-current",
        }
    )

    assert export_actions.current_pdf_bytes() == b"%PDF-current"




def test_current_pdf_bytes_rejects_preview_signed_pdf_after_image_state_changes():
    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": "sig-1",
            "pdf_signature": "sig-1",
            "pdf_bytes": b"%PDF-preview-only",
            "output_edits": {
                "pictures_added": True,
                "day_images": {"Day 1": {"mode": "none", "path": "", "crop_focus": "center"}},
            },
        }
    )

    assert export_actions.current_pdf_bytes() is None

def test_export_readiness_does_not_reuse_unsigned_pdf_bytes():
    from app_modules.export_state import export_readiness_from_state

    readiness = export_readiness_from_state(
        {
            "itinerary_html": "<html></html>",
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
            "output_edits": {"pictures_added": True},
            "preview_signature": None,
            "pdf_bytes": b"%PDF-stale",
            "pdf_signature": None,
            "export_pdf_bytes": b"%PDF-stale-export",
            "export_pdf_signature": None,
        },
        {"full_bank_found": True, "missing_full_bank": False},
    )

    assert readiness.pdf_ready is False
    assert readiness.status_label == "Ready to create"


def test_pdf_creation_stops_when_preview_refresh_fails(monkeypatch):
    from types import SimpleNamespace

    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": None,
            "pdf_signature": None,
            "pdf_bytes": None,
            "export_pdf_bytes": None,
            "export_pdf_signature": None,
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
            "output_edits": {"pictures_added": True},
            "itinerary_html": "<html></html>",
            "html_path": "stale-preview.html",
            "pdf_status": "Not created",
        }
    )

    monkeypatch.setattr(export_actions, "validate_for_generation", lambda _rows: SimpleNamespace(is_blocked=False))
    monkeypatch.setattr(export_actions, "rebuild_current_preview", lambda **_kwargs: False)

    def _should_not_render(*_args, **_kwargs):  # pragma: no cover - failure path
        raise AssertionError("PDF should not render from a stale or unsigned preview.")

    monkeypatch.setattr(export_actions, "save_pdf_file", _should_not_render)

    assert export_actions.create_pdf_from_current_preview() is False
    assert st.session_state["pdf_status"] == "Preview refresh failed"
    assert st.session_state["pdf_bytes"] is None


def test_pdf_creation_stops_when_preview_signature_is_missing(monkeypatch):
    from types import SimpleNamespace

    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": None,
            "pdf_signature": None,
            "pdf_bytes": None,
            "export_pdf_bytes": None,
            "export_pdf_signature": None,
            "parsed_rows": [{"day": "Day 1", "city": "Oslo", "title": "Walk"}],
            "output_edits": {"pictures_added": True},
            "itinerary_html": "<html></html>",
            "html_path": "stale-preview.html",
            "pdf_status": "Not created",
        }
    )

    monkeypatch.setattr(export_actions, "validate_for_generation", lambda _rows: SimpleNamespace(is_blocked=False))
    monkeypatch.setattr(export_actions, "rebuild_current_preview", lambda **_kwargs: True)

    def _should_not_render(*_args, **_kwargs):  # pragma: no cover - failure path
        raise AssertionError("PDF should not render without a preview signature.")

    monkeypatch.setattr(export_actions, "save_pdf_file", _should_not_render)

    assert export_actions.create_pdf_from_current_preview() is False
    assert st.session_state["pdf_status"] == "Preview refresh failed"
    assert st.session_state["pdf_bytes"] is None


def test_pdf_image_contract_ignores_stale_stage_matches_when_user_removed_image(monkeypatch):
    st = install_streamlit_stub(force=True)
    st.session_state.clear()
    st.session_state.update(
        {
            "day_image_matches": {"Day 1": {"path": "stale-auto-image.jpg"}},
            "output_edits": {"day_images": {"Day 1": {"mode": "none", "path": "", "crop_focus": "center"}}},
        }
    )

    from app_modules import export_image_validation

    monkeypatch.setattr(
        export_image_validation,
        "select_day_images_with_overrides",
        lambda grouped, output_edits: {"Day 1": None},
    )

    assert export_image_validation._select_image_matches_for_export({"Day 1": [{"city": "Oslo"}]}) == {"Day 1": None}


def test_pdf_renderer_prewarms_day_image_crops_before_reportlab_build():
    source = read_contract_text("pdf_exporter_modules/typed_exporter.py")
    prewarm_source = read_contract_text("pdf_exporter_modules/pdf_image_prewarm.py")

    assert "prewarm_pdf_day_images(" in source
    assert "render_document.days or []" in source
    assert "make_cover_cropped_image(" in prewarm_source
    assert "Pre-warming is an optimization only" in prewarm_source
