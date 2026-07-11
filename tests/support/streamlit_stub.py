"""Central Streamlit test stub.

Several tests import modules that expect Streamlit and Streamlit Components to
exist, while the unit-test environment intentionally does not start a real
Streamlit runtime.  Installing one complete stub in a single place avoids
order-dependent test failures where one module registers ``streamlit`` without
``streamlit.components.v1`` and a later import then fails.
"""

from __future__ import annotations

import sys
import types
from typing import Any


class SessionState(dict):
    """Small dict/object hybrid matching the parts of st.session_state we use."""

    def __getattr__(self, name: str) -> Any:
        return self.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value



class _ContextManagerStub:
    """Context manager returned by Streamlit layout/form helpers in tests."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def form_submit_button(self, *args: Any, **kwargs: Any) -> bool:
        return False

    def button(self, *args: Any, **kwargs: Any) -> bool:
        return False


def _context(*args: Any, **kwargs: Any) -> _ContextManagerStub:
    return _ContextManagerStub()


def _columns(spec: Any, *args: Any, **kwargs: Any) -> tuple[_ContextManagerStub, ...]:
    count = spec if isinstance(spec, int) else len(spec) if hasattr(spec, "__len__") else 1
    return tuple(_ContextManagerStub() for _ in range(max(0, int(count))))


def _button(*args: Any, **kwargs: Any) -> bool:
    return False


def _file_uploader(*args: Any, **kwargs: Any) -> None:
    return None


def _selectbox(label: str, options: Any, *args: Any, **kwargs: Any) -> Any:
    values = tuple(options or ())
    if not values:
        return None
    index = int(kwargs.get("index", 0) or 0)
    return values[max(0, min(len(values) - 1, index))]


def _value_kwarg(*args: Any, **kwargs: Any) -> Any:
    return kwargs.get("value", "")


def _checkbox(*args: Any, **kwargs: Any) -> bool:
    return bool(kwargs.get("value", False))


def _noop(*args: Any, **kwargs: Any) -> None:
    return None


def _dialog(*args: Any, **kwargs: Any):
    def _decorator(func):
        return func

    return _decorator


def _component_factory(*args: Any, **kwargs: Any):
    def _component(*component_args: Any, **component_kwargs: Any) -> None:
        return None

    return _component


def install_streamlit_stub(*, force: bool = False):
    """Install or complete a Streamlit stub and return it.

    ``force`` is rarely needed; the default completes any existing lightweight
    stub in place so tests that set a custom ``session_state`` keep their state.
    """

    # Preserve module identity even for a forced reset. Production modules
    # retain their imported ``streamlit`` reference, so replacing the object in
    # ``sys.modules`` creates order-dependent split session-state ownership.
    streamlit = sys.modules.get("streamlit")
    if streamlit is None:
        streamlit = types.ModuleType("streamlit")

    if force:
        streamlit.session_state = SessionState()
    elif not hasattr(streamlit, "session_state") or streamlit.session_state is None:
        streamlit.session_state = SessionState()
    elif isinstance(streamlit.session_state, dict) and not isinstance(streamlit.session_state, SessionState):
        streamlit.session_state = SessionState(streamlit.session_state)

    for name in (
        "error",
        "exception",
        "warning",
        "success",
        "info",
        "markdown",
        "html",
        "write",
        "caption",
        "toast",
        "rerun",
        "experimental_rerun",
        "subheader",
        "download_button",
    ):
        if not hasattr(streamlit, name):
            setattr(streamlit, name, _noop)

    for name in ("container", "expander", "form"):
        if not hasattr(streamlit, name):
            setattr(streamlit, name, _context)
    if not hasattr(streamlit, "columns"):
        streamlit.columns = _columns
    for name in ("button", "form_submit_button"):
        if not hasattr(streamlit, name):
            setattr(streamlit, name, _button)
    if not hasattr(streamlit, "file_uploader"):
        streamlit.file_uploader = _file_uploader
    if not hasattr(streamlit, "selectbox"):
        streamlit.selectbox = _selectbox
    for name in ("text_input", "text_area", "number_input"):
        if not hasattr(streamlit, name):
            setattr(streamlit, name, _value_kwarg)
    if not hasattr(streamlit, "checkbox"):
        streamlit.checkbox = _checkbox
    if not hasattr(streamlit, "dialog"):
        streamlit.dialog = _dialog

    components = sys.modules.get("streamlit.components")
    if components is None:
        components = types.ModuleType("streamlit.components")

    components_v1 = sys.modules.get("streamlit.components.v1")
    if components_v1 is None:
        components_v1 = types.ModuleType("streamlit.components.v1")
    if not hasattr(components_v1, "declare_component"):
        components_v1.declare_component = _component_factory

    streamlit.components = components
    components.v1 = components_v1

    sys.modules["streamlit"] = streamlit
    sys.modules["streamlit.components"] = components
    sys.modules["streamlit.components.v1"] = components_v1
    return streamlit
