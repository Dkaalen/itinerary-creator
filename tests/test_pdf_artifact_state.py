from app_modules.export_identity import export_signature_for_state
from app_modules.pdf_artifact_state import (
    clear_pdf_artifact_state,
    current_pdf_artifact,
    store_pdf_artifact,
)


def _state() -> dict:
    return {
        "preview_signature": "preview-1",
        "output_edits": {
            "pictures_added": True,
            "day_images": {"Day 1": {"mode": "manual", "path": "images/oslo.webp", "crop_focus": "center"}},
        },
    }


def test_pdf_artifact_uses_export_signature_not_preview_signature() -> None:
    state = _state()
    state.update({"pdf_bytes": b"%PDF", "pdf_signature": "preview-1"})

    assert current_pdf_artifact(state) is None


def test_pdf_artifact_resolves_current_export_signed_bytes() -> None:
    state = _state()
    signature = export_signature_for_state(state)
    store_pdf_artifact(state, content=b"%PDF", signature=signature, filename="norway.pdf")

    artifact = current_pdf_artifact(state)

    assert artifact is not None
    assert artifact.content == b"%PDF"
    assert artifact.signature == signature
    assert artifact.filename == "norway.pdf"


def test_clearing_pdf_artifact_also_clears_export_only_caches() -> None:
    state = _state()
    state.update(
        {
            "pdf_bytes": b"%PDF",
            "export_pdf_bytes": b"%PDF",
            "pdf_signature": "sig",
            "export_pdf_signature": "sig",
            "pdf_filename": "old.pdf",
            "export_last_error": "boom",
            "_pdf_image_contract_cache": {"signature": "old"},
        }
    )

    clear_pdf_artifact_state(state, status="Needs refresh")

    assert state["pdf_bytes"] is None
    assert state["export_pdf_bytes"] is None
    assert state["pdf_signature"] is None
    assert state["export_pdf_signature"] is None
    assert state["pdf_status"] == "Needs refresh"
    assert "pdf_filename" not in state
    assert "export_last_error" not in state
    assert "_pdf_image_contract_cache" not in state
