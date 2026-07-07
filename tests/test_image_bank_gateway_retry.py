from __future__ import annotations

from tests.support.streamlit_stub import install_streamlit_stub


def test_image_bank_retry_clears_cached_status_and_scanner(monkeypatch) -> None:
    import app_modules.image_gateway_ui as gateway_ui

    st = install_streamlit_stub()
    st.session_state.clear()
    st.session_state["_image_bank_status_cache"] = {
        "request_signature": "stale",
        "bank_signature": "stale",
        "status": {"default_image_count": 1},
    }

    cleared = []
    invalidated = []

    monkeypatch.setattr(gateway_ui, "_current_image_bank_requests", lambda: [{"country": "NO", "destination": "Oslo"}])
    monkeypatch.setattr(gateway_ui, "clear_image_bank_status_cache", lambda state: (cleared.append(dict(state)), state.pop("_image_bank_status_cache", None)))
    monkeypatch.setattr(gateway_ui, "invalidate_image_bank_cache", lambda: invalidated.append(True))
    monkeypatch.setattr(
        gateway_ui,
        "connect_remote_image_bank_if_missing",
        lambda requests: {
            "required_destinations_ready": True,
            "destination_image_count": 3,
            "required_destinations": requests,
        },
    )

    status = gateway_ui._connect_current_image_bank()

    assert status["required_destinations_ready"] is True
    assert len(cleared) == 2
    assert invalidated == [True, True]
    assert st.session_state["_image_bank_status_cache"]["status"]["destination_image_count"] == 3
