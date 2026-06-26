from pathlib import Path

from app_modules import export_actions
from tests.support.streamlit_stub import install_streamlit_stub


def test_current_pdf_creation_is_a_noop_fast_path(monkeypatch):
    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state.update(
        {
            "preview_signature": "current-preview",
            "pdf_signature": "current-preview",
            "pdf_bytes": b"%PDF-current",
            "pdf_status": "Ready",
            "parsed_rows": [{"day": "1", "type": "activity", "title": "Walk Oslo"}],
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
    source = Path("app_modules/export_step.py").read_text(encoding="utf-8")
    picture_source = Path("app_modules/picture_step.py").read_text(encoding="utf-8")

    assert "if not readiness.pdf_ready:" in source
    assert source.index("if not readiness.pdf_ready:") < source.index('st.button("Create PDF"')
    assert "if not current_pdf_bytes():" in picture_source
    assert picture_source.index("if not current_pdf_bytes():") < picture_source.index('st.button("Create PDF"')


def test_export_screen_clears_stale_pdf_commit_state_without_waiting():
    source = Path("app_modules/export_step.py").read_text(encoding="utf-8")

    assert "visual_editor_export_commit_ready" not in source
    assert "Applying pending editor changes" not in source
    assert "clear_pdf_editor_commit_request(st.session_state)" in source
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
            "pdf_signature": "sig-1",
            "pdf_bytes": b"%PDF-current",
            "_pdf_after_visual_edit_commit_nonce": "2",
            "_visual_editor_export_commit_ready": False,
        }
    )

    assert export_actions.current_pdf_bytes() == b"%PDF-current"


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
