from __future__ import annotations

from app_modules.export_readiness_ui import export_readiness_panel_html
from app_modules.export_state import ExportReadiness


def test_export_readiness_panel_summarizes_ready_state() -> None:
    html = export_readiness_panel_html(
        ExportReadiness(
            has_document=True,
            pictures_added=True,
            image_bank_ready=True,
            pdf_ready=False,
            can_create_pdf=True,
            blocking_messages=(),
            status_label="Ready to create",
        )
    )

    assert "export-readiness-panel" in html
    assert "Ready to create the final PDF" in html
    assert "Pictures ready" in html
    assert "Image source ready" in html
    assert "Preflight · Clear" in html


def test_export_readiness_panel_escapes_blocker_copy() -> None:
    html = export_readiness_panel_html(
        ExportReadiness(
            has_document=True,
            pictures_added=False,
            image_bank_ready=False,
            pdf_ready=False,
            can_create_pdf=False,
            blocking_messages=("Add <pictures> before PDF.",),
            status_label="Not ready",
            critical_issue_count=1,
        )
    )

    assert "PDF export needs attention" in html
    assert "Add &lt;pictures&gt; before PDF." in html
    assert "Pictures missing" in html
    assert "Image source missing" in html
    assert "Preflight · 1 issue" in html
