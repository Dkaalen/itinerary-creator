from __future__ import annotations

import inspect

from tests.support.streamlit_stub import SessionState, install_streamlit_stub

st = install_streamlit_stub(force=True)

from app_modules import input_generation_action, input_preview_table, project_workspace_revision
from app_modules.input_preview_table import render_supplier_rows_preview
from app_modules.project_persistence_state import mark_cloud_project_persisted
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.project_workspace_revision import mark_workspace_mutated
from app_modules.session_state_keys import OPEN_PROJECT_BROWSER_VISIBLE_KEY
from app_modules.workflow_result import WorkflowActionResult
from project_storage.repository import ProjectStorageRepository


def _saved_payload() -> dict:
    return {
        "metadata": {"itinerary_name": "Nordic Journey"},
        "current_snapshot": {
            "parsed_rows": [
                {
                    "day": 1,
                    "type": "Hotel",
                    "city": "Oslo",
                    "description": "Hotel stay",
                }
            ],
            "output_edits": {"days": {"1": {"title": "Arrival in Oslo"}}},
            "detail_level": "standard",
            "day_page_layout": "continuous",
        },
        "source": {"source_input": "Day 1\tHotel\tOslo\tHotel stay"},
    }


def _matching_state() -> SessionState:
    payload = _saved_payload()
    state = SessionState(
        {
            "itinerary_name": "Nordic Journey",
            "parsed_rows": [dict(payload["current_snapshot"]["parsed_rows"][0])],
            "output_edits": {"days": {"1": {"title": "Arrival in Oslo"}}},
            "detail_level": "standard",
            "day_page_layout": "continuous",
            "raw_text_input": "Day 1\tHotel\tOslo\tHotel stay",
        }
    )
    mark_workspace_mutated(state)
    mark_cloud_project_persisted(state, payload=payload, version_id="version-1")
    return state


def test_supplier_preview_reuses_exact_source_parse_and_cached_html(monkeypatch) -> None:
    st.session_state = SessionState()
    parse_calls: list[str] = []
    rendered: list[str] = []
    rows = [{"day": 1, "type": "Hotel", "city": "Oslo", "description": "Stay"}]

    monkeypatch.setattr(
        input_preview_table,
        "parse_and_normalize_itinerary",
        lambda text, state=None: parse_calls.append(text) or rows,
    )
    monkeypatch.setattr(st, "html", lambda html: rendered.append(html))

    first = render_supplier_rows_preview("Day 1\tHotel\tOslo\tStay")
    second = render_supplier_rows_preview("Day 1\tHotel\tOslo\tStay")

    assert list(first.rows) == rows
    assert list(second.rows) == rows
    assert parse_calls == ["Day 1\tHotel\tOslo\tStay"]
    assert len(rendered) == 2
    assert rendered[0] == rendered[1]


def test_supplier_preview_cache_uses_exact_raw_source_identity(monkeypatch) -> None:
    st.session_state = SessionState()
    parse_calls: list[str] = []
    monkeypatch.setattr(
        input_preview_table,
        "parse_and_normalize_itinerary",
        lambda text, state=None: parse_calls.append(text) or [{"day": 1}],
    )
    monkeypatch.setattr(st, "html", lambda *_args, **_kwargs: None)

    render_supplier_rows_preview("Day 1\tHotel")
    render_supplier_rows_preview("Day 1\tHotel ")

    assert parse_calls == ["Day 1\tHotel", "Day 1\tHotel"]


def test_supplier_preview_defers_uncached_parse_while_explorer_is_open(monkeypatch) -> None:
    st.session_state = SessionState({OPEN_PROJECT_BROWSER_VISIBLE_KEY: True})
    captions: list[str] = []
    monkeypatch.setattr(
        input_preview_table,
        "parse_and_normalize_itinerary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("parser must not run")),
    )
    monkeypatch.setattr(st, "caption", lambda value: captions.append(str(value)))

    result = render_supplier_rows_preview("Day 1\tHotel\tOslo")

    assert result is None
    assert captions == ["The parsed preview will update after Project Explorer is closed."]


def test_supplier_generation_forwards_prepared_preview_rows(monkeypatch) -> None:
    state = SessionState({"itinerary_name_input": "Nordic Journey"})
    prepared = [{"day": 1, "type": "Hotel"}]
    calls: list[tuple[str, object]] = []

    def fake_generate(
        target_state,
        raw_text,
        *,
        prepared_parsed_rows=None,
        prepared_parser_diagnostics=None,
    ):
        calls.append((raw_text, prepared_parsed_rows, prepared_parser_diagnostics))
        return WorkflowActionResult(ok=True, stage="edit", message="ok")

    monkeypatch.setattr(input_generation_action, "generate_itinerary", fake_generate)

    assert input_generation_action.generate_supplier_itinerary(
        state,
        "Day 1\tHotel",
        prepared_parsed_rows=prepared,
        prepared_parser_diagnostics=[{"category": "test"}],
    ) is True
    assert calls == [("Day 1\tHotel", prepared, [{"category": "test"}])]


def test_dirty_state_signatures_are_reused_until_mutation_revision_changes(monkeypatch) -> None:
    state = _matching_state()
    digest_calls = 0
    original_digest = project_workspace_revision._digest

    def counted_digest(value):
        nonlocal digest_calls
        digest_calls += 1
        return original_digest(value)

    monkeypatch.setattr(project_workspace_revision, "_digest", counted_digest)

    assert active_project_has_unsaved_changes(state) is False
    first_call_count = digest_calls
    assert first_call_count > 0

    assert active_project_has_unsaved_changes(state) is False
    assert digest_calls == first_call_count

    state["output_edits"]["days"]["1"]["title"] = "Changed title"
    mark_workspace_mutated(state)

    assert active_project_has_unsaved_changes(state) is True
    assert digest_calls > first_call_count


def test_direct_delete_model_has_no_retired_trash_mutation_api() -> None:
    for method_name in (
        "move_itineraries_to_trash",
        "restore_itineraries_from_trash",
    ):
        assert not hasattr(ProjectStorageRepository, method_name)

    assert "trash_only" not in inspect.signature(ProjectStorageRepository.list_project_page).parameters
    assert "include_trashed" not in inspect.signature(ProjectStorageRepository.list_project_folders).parameters


def test_failed_save_restores_workspace_revision_and_signature_caches() -> None:
    from app_modules.project_save_rollback import capture_project_save_baseline, restore_project_save_baseline
    from app_modules.project_workspace_revision import (
        PERSISTED_BASELINE_SIGNATURES_KEY,
        WORKSPACE_REVISION_KEY,
        WORKSPACE_SIGNATURE_CACHE_KEY,
    )

    state = SessionState(
        {
            WORKSPACE_REVISION_KEY: 7,
            WORKSPACE_SIGNATURE_CACHE_KEY: {"token": (7,), "signatures": {"parsed_rows": "old"}},
            PERSISTED_BASELINE_SIGNATURES_KEY: {"parsed_rows": "saved"},
            "itinerary_name": "Old name",
        }
    )
    baseline = capture_project_save_baseline(state)
    state[WORKSPACE_REVISION_KEY] = 9
    state[WORKSPACE_SIGNATURE_CACHE_KEY] = {"token": (9,), "signatures": {"parsed_rows": "new"}}
    state[PERSISTED_BASELINE_SIGNATURES_KEY] = {"parsed_rows": "new-saved"}

    restore_project_save_baseline(state, baseline)

    assert state[WORKSPACE_REVISION_KEY] == 7
    assert state[WORKSPACE_SIGNATURE_CACHE_KEY]["signatures"]["parsed_rows"] == "old"
    assert state[PERSISTED_BASELINE_SIGNATURES_KEY]["parsed_rows"] == "saved"


def test_failed_open_restores_workspace_revision_and_signature_caches() -> None:
    from app_modules.project_session_transitions import (
        capture_project_switch_baseline,
        restore_project_switch_baseline,
    )
    from app_modules.project_workspace_revision import (
        PERSISTED_BASELINE_SIGNATURES_KEY,
        WORKSPACE_REVISION_KEY,
        WORKSPACE_SIGNATURE_CACHE_KEY,
    )

    state = SessionState(
        {
            WORKSPACE_REVISION_KEY: 3,
            WORKSPACE_SIGNATURE_CACHE_KEY: {"token": (3,), "signatures": {"output_edits": "old"}},
            PERSISTED_BASELINE_SIGNATURES_KEY: {"output_edits": "saved"},
            "parsed_rows": [{"day": 1}],
        }
    )
    baseline = capture_project_switch_baseline(state)
    state.clear()
    state.update(
        {
            WORKSPACE_REVISION_KEY: 1,
            WORKSPACE_SIGNATURE_CACHE_KEY: {"token": (1,), "signatures": {"output_edits": "new"}},
            PERSISTED_BASELINE_SIGNATURES_KEY: {"output_edits": "new-saved"},
            "parsed_rows": [{"day": 99}],
        }
    )

    restore_project_switch_baseline(state, baseline)

    assert state[WORKSPACE_REVISION_KEY] == 3
    assert state[WORKSPACE_SIGNATURE_CACHE_KEY]["signatures"]["output_edits"] == "old"
    assert state[PERSISTED_BASELINE_SIGNATURES_KEY]["output_edits"] == "saved"
    assert state["parsed_rows"] == [{"day": 1}]


def test_empty_supplier_preview_result_is_cached_by_exact_source(monkeypatch) -> None:
    st.session_state = SessionState()
    parse_calls: list[str] = []
    captions: list[str] = []
    monkeypatch.setattr(
        input_preview_table,
        "parse_and_normalize_itinerary",
        lambda text, state=None: parse_calls.append(text) or [],
    )
    monkeypatch.setattr(st, "caption", lambda value: captions.append(str(value)))

    assert render_supplier_rows_preview("Not enough data").rows == ()
    assert render_supplier_rows_preview("Not enough data").rows == ()

    assert parse_calls == ["Not enough data"]
    assert captions == ["No itinerary rows detected yet.", "No itinerary rows detected yet."]


def test_preview_diagnostics_are_isolated_and_forwarded_to_generation(monkeypatch) -> None:
    import diagnostics
    from app_modules import generation_action

    st.session_state = SessionState()
    diagnostics.reset()
    diagnostics.warn("existing", "Keep active warning")

    def parse(text, state=None):
        diagnostics.warn("preview", "Preview-only warning", raw_value=text)
        return [{"day": 1, "type": "Hotel"}]

    monkeypatch.setattr(input_preview_table, "parse_and_normalize_itinerary", parse)
    monkeypatch.setattr(st, "html", lambda *_args, **_kwargs: None)
    preview = render_supplier_rows_preview("Day 1\tHotel")

    assert [item["category"] for item in diagnostics.get_warnings()] == ["existing"]
    assert [item["category"] for item in preview.parser_diagnostics] == ["preview"]

    state = SessionState()
    monkeypatch.setattr(generation_action, "validate_for_generation", lambda rows: type("Report", (), {"is_blocked": False})())
    monkeypatch.setattr(
        generation_action,
        "build_structured_input_review",
        lambda rows, parser_diagnostics: {"diagnostics": list(parser_diagnostics)},
    )
    rows, _report = generation_action._parse_and_review(
        state,
        "Day 1\tHotel",
        prepared_parsed_rows=list(preview.rows),
        prepared_parser_diagnostics=list(preview.parser_diagnostics),
    )

    assert rows == [{"day": 1, "type": "Hotel"}]
    assert state["parser_diagnostics"][0]["category"] == "preview"
    assert state["structured_input_review"]["diagnostics"][0]["category"] == "preview"


def test_hard_project_boundary_clears_supplier_preview_cache() -> None:
    from app_modules.supplier_preview_cache import (
        cached_supplier_rows_preview,
        remember_supplier_rows_preview,
    )
    from app_modules.workflow_transients import clear_project_boundary_transients

    state = SessionState()
    remember_supplier_rows_preview(
        state,
        "Day 1\tHotel",
        [{"day": 1, "type": "Hotel"}],
        parser_diagnostics=[{"category": "preview"}],
    )
    assert cached_supplier_rows_preview(state, "Day 1\tHotel") is not None

    clear_project_boundary_transients(state)

    assert cached_supplier_rows_preview(state, "Day 1\tHotel") is None
