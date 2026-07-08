from __future__ import annotations

import ast
from pathlib import Path


def _text(relative_path: str) -> str:
    return Path(relative_path).read_text(encoding="utf-8")


def _contains(relative_path: str, token: str) -> bool:
    return token in _text(relative_path)


def _omits(relative_path: str, token: str) -> bool:
    return token not in _text(relative_path)


def _combined_contains(paths: tuple[str, ...], token: str) -> bool:
    return any(_contains(path, token) for path in paths)


def _combined_omits(paths: tuple[str, ...], token: str) -> bool:
    return all(_omits(path, token) for path in paths)


def _python_calls(relative_path: str) -> set[str]:
    tree = ast.parse(_text(relative_path))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    return calls


def _python_imported_names(relative_path: str) -> set[str]:
    tree = ast.parse(_text(relative_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)
    return names


def test_export_step_uses_shared_recoverable_pdf_job_flow():
    pdf_flow_paths = (
        "app_modules/export_step.py",
        "app_modules/pdf_creation_request.py",
        "app_modules/pdf_editor_commit_gate.py",
    )

    assert _combined_omits(pdf_flow_paths, "request_editor_save_before_pdf(st.session_state)")
    assert _combined_contains(pdf_flow_paths, "workflow_transaction_state")
    assert _combined_contains(pdf_flow_paths, "transaction_timeout_copy")
    assert _combined_contains(pdf_flow_paths, "Create PDF from last saved version")
    assert _combined_omits(pdf_flow_paths, "Saving the latest editor changes before creating the PDF")
    assert _combined_contains(pdf_flow_paths, "clear_stale_pdf_editor_state()")
    assert _combined_omits(pdf_flow_paths, "Applying pending editor changes")
    assert _combined_omits(pdf_flow_paths, "visual_editor_export_commit_ready")
    assert _combined_contains(pdf_flow_paths, "current_export_job")
    assert _combined_contains(pdf_flow_paths, "auto_pdf_create_requested")
    assert _combined_contains(pdf_flow_paths, "PDF creation was stopped because the document is not ready")
    assert _combined_contains(pdf_flow_paths, "start_pdf_editor_commit(st.session_state, auto_create_pdf=True)")
    assert _combined_contains(pdf_flow_paths, "mark_exporting")
    assert _contains(
        "app_modules/workflow_transactions.py",
        "Syncing the latest editor changes before PDF export",
    )


def test_pdf_export_configures_reportlab_for_fast_image_streams():
    config_calls = _python_calls("pdf_exporter_modules/pdf_reportlab_config.py")
    typed_calls = _python_calls("pdf_exporter_modules/typed_exporter.py")
    fallback_calls = _python_calls("pdf_exporter_modules/exporter.py")

    assert "configure_reportlab_for_fast_pdf" in typed_calls
    assert "configure_reportlab_for_fast_pdf" in fallback_calls
    assert _contains("pdf_exporter_modules/pdf_reportlab_config.py", "rl_config.useA85 = 0")
    assert "rl_config" in _python_imported_names("pdf_exporter_modules/pdf_reportlab_config.py")


def test_picture_page_create_pdf_enters_export_with_one_shot_auto_request():
    assert "render_picture_pdf_cta" in _python_imported_names("app_modules/picture_step.py")
    assert "start_pdf_editor_commit" in _python_calls("app_modules/picture_pdf_cta.py")
    assert "enter_export_stage" in _python_calls("app_modules/picture_pdf_cta.py")
    assert "start_workflow_transaction" in _python_calls("app_modules/pdf_editor_commit_gate.py")
    assert "request_auto_pdf_create" in _python_calls("app_modules/export_stage_action.py")
    assert _contains("app_modules/export_stage_action.py", "auto_create_pdf: bool = False")
    assert _omits("app_modules/export_stage_action.py", "request_pdf_commit_func")


def test_pdf_export_avoids_repeated_image_bank_storage_scans_on_normal_path():
    normal_path_modules = ("app_modules/export_step.py",)

    assert _combined_omits(normal_path_modules, "image_bank_storage_signature")
    assert "get_cached_image_bank_status" in _python_imported_names("app_modules/export_step.py")
    assert "get_cached_image_bank_status" in _python_imported_names("app_modules/export_image_validation.py")


def test_pdf_export_timing_is_internal_and_stage_based():
    export_calls = _python_calls("app_modules/export_actions.py")

    assert {"reset_pdf_export_timings", "record_pdf_export_stage", "has_pdf_export_timings"}.issubset(export_calls)
    assert _contains("app_modules/export_actions.py", "prepare_images")
    assert _contains("app_modules/export_actions.py", "render_pdf")
    assert _contains("app_modules/export_timing.py", "PDF_EXPORT_TIMINGS_KEY")
    assert _contains("app_modules/export_timing.py", "record_pdf_export_marker")
    assert _omits("app_modules/export_timing.py", "st.")


def test_editor_save_keeps_dirty_keys_until_server_payload_acknowledges_them():
    assert _contains("visual_editor_component/frontend/js/state.js", "pendingServerSaveKeys")
    assert _contains("visual_editor_component/frontend/js/editor_save_state.js", "acknowledgeServerSaveFromPayload")
    assert _contains("visual_editor_component/frontend/js/editor_save_state.js", "serverPayloadContainsPendingSave")
    assert _contains("visual_editor_component/frontend/js/editing.js", "pendingServerSaveKeys = new Set(touchedKeys)")
    assert _contains("visual_editor_component/frontend/js/render.js", "acknowledgeServerSaveFromPayload(initialPayload)")
    assert _omits(
        "visual_editor_component/frontend/js/editing.js",
        "if (!safeSendComponentValue(serialized, commitNonce ? 'exporting' : 'saving')) return;\n  touchedKeys = new Set();",
    )
