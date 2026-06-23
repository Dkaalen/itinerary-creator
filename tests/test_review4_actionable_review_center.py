from pathlib import Path

from visual_editor_component.editor_payload_warnings import _compact_model_warnings
from itinerary_generation.structured_model import ModelWarning


def _read(relative: str) -> str:
    return Path(relative).read_text(encoding="utf-8")


class _StructuredDocument:
    warnings = (
        ModelWarning(
            code="source_signal_missing",
            message="Missing source detail",
            severity="review",
            source_row_ids=("r1",),
        ),
    )


def test_review4_uses_specific_page_action_labels_and_source_rows():
    render_js = _read("visual_editor_component/frontend/js/render.js")

    assert "function warningActionLabel" in render_js
    assert "Open day page" in render_js
    assert "Open final page" in render_js
    assert "Open cover" in render_js
    assert "Open summary" in render_js
    assert "warningSourceChipsHtml" in render_js
    assert "Source row:" in render_js
    assert "Review page</button>" not in render_js


def test_review4_model_warning_payload_gets_page_id_from_source_row():
    warnings = _compact_model_warnings(
        _StructuredDocument(),
        parsed_rows=[{"row_id": "r1", "day": "Day 2", "city": "Bergen", "title": "Rail to Oslo"}],
    )

    assert warnings[0]["page_id"] == "day-day-2"
    assert warnings[0]["page_label"] == "Day 2 · Bergen · Rail to Oslo"
    assert warnings[0]["source_row_ids"] == ["r1"]
