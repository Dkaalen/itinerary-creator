from __future__ import annotations

import ast
from pathlib import Path

from images.selection_contract import commit_selection_payload

ROOT = Path(__file__).resolve().parents[1]


def _imports(path: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_preview_editor_and_pdf_renderers_do_not_own_discovery_or_scoring():
    for path in (
        "app_modules/itinerary_html.py",
        "app_modules/render_context_document.py",
        "app_modules/render_context_final_sections.py",
        "pdf_exporter_modules/pdf_day_renderer.py",
        "visual_editor_component/editor_payload_images.py",
    ):
        imports = _imports(path)
        assert "images.matcher_scoring" not in imports
        assert "images.matcher_selection" not in imports
        if path != "visual_editor_component/editor_payload_images.py":
            assert "images.scanner" not in imports


def test_selection_debug_metadata_is_structured_internal_data():
    payload = commit_selection_payload(
        "Day 1",
        {"path": "/bank/Oslo.jpg", "filename": "Oslo.jpg", "score": 42, "reason": "city match"},
    )
    assert payload
    assert payload["selection_contract_version"] == 1
    assert payload["selection_debug"]["selected_candidate"] == "/bank/Oslo.jpg"
    assert payload["candidate_provenance"]["source_type"] == "image_bank"
    assert not isinstance(payload["selection_debug"], str)
