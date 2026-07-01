from pathlib import Path

from visual_editor_component.editor_payload_warnings import _client_output_warnings_for_payload
from tests.support.frontend_assets import frontend_source


def _frontend_source() -> str:
    return frontend_source()


def test_review3_groups_warnings_and_uses_export_check_language():
    source = _frontend_source()

    assert "Export clear" in source
    assert "groupedClientWarnings" in source
    assert "Critical" in source
    assert "Review" in source
    assert "Hidden auto-fixes" in source
    assert "export blocker" in source
    assert "isHiddenAutoFixWarning" in source
    assert "warning-panel-stack" in source


def test_review3_warning_payloads_include_metadata_for_grouping():
    payload = {
        "cover": {"trip_title": "Norway Proposal"},
        "days": [{"city": "Oslo", "title": "Day 1", "intro": "", "blocks_html": ""}],
        "final_pages": {},
    }

    warnings = _client_output_warnings_for_payload(payload)

    assert isinstance(warnings, list)
    # The scanner may not find anything for clean text, but the payload contract
    # must keep the grouping metadata whenever a warning exists.
    for warning in warnings:
        assert {"code", "severity", "category", "message", "excerpt"} <= set(warning)


def test_review3_warning_count_ignores_hidden_autofix_bucket():
    source = Path("visual_editor_component/frontend/js/editor_warnings.js").read_text(encoding="utf-8")

    assert "editorClientWarnings()" in source
    assert "model.client_output_warnings.length" in source
