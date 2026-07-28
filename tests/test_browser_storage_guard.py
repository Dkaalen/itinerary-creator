from __future__ import annotations

from app_modules import browser_storage_guard


def test_browser_storage_guard_is_bounded_and_preserves_unrelated_keys() -> None:
    script = browser_storage_guard._BROWSER_STORAGE_GUARD

    assert "MAX_AGE = 7 * DAY" in script
    assert "MAX_CALC_NAMESPACES = 3" in script
    assert "MAX_CALC_BYTES = 1.5 * 1024 * 1024" in script
    assert "MAX_EDITOR_DRAFTS = 3" in script
    assert "MAX_EDITOR_BYTES = 1.0 * 1024 * 1024" in script
    assert "itineraryCalculatorBrowserDraft.v1." in script
    assert "itineraryCalculatorBrowserDraft.v2." in script
    assert "itineraryCalculatorBrowserDraft.v3." in script
    assert "itineraryVisualEditorDraft." in script
    assert "localStorage.clear" not in script


def test_browser_storage_guard_mounts_once_per_streamlit_session(monkeypatch) -> None:
    import streamlit.components.v1 as components

    calls: list[tuple[str, int, int]] = []
    monkeypatch.setattr(
        components,
        "html",
        lambda body, *, height, width: calls.append((str(body), int(height), int(width))),
        raising=False,
    )
    state: dict[str, object] = {}

    browser_storage_guard.render_browser_storage_guard(state)
    browser_storage_guard.render_browser_storage_guard(state)

    assert len(calls) == 1
    assert calls[0][1:] == (0, 0)
    assert "MAX_CALC_BYTES" in calls[0][0]
    assert state["browser_storage_guard_rendered_v1"] is True
