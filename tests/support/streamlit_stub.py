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


def _noop(*args: Any, **kwargs: Any) -> None:
    return None


def _component_factory(*args: Any, **kwargs: Any):
    def _component(*component_args: Any, **component_kwargs: Any) -> None:
        return None

    return _component


def install_streamlit_stub(*, force: bool = False):
    """Install or complete a Streamlit stub and return it.

    ``force`` is rarely needed; the default completes any existing lightweight
    stub in place so tests that set a custom ``session_state`` keep their state.
    """

    streamlit = None if force else sys.modules.get("streamlit")
    if streamlit is None:
        streamlit = types.ModuleType("streamlit")

    if not hasattr(streamlit, "session_state") or streamlit.session_state is None:
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
        "write",
        "caption",
        "toast",
        "rerun",
        "experimental_rerun",
    ):
        if not hasattr(streamlit, name):
            setattr(streamlit, name, _noop)

    components = None if force else sys.modules.get("streamlit.components")
    if components is None:
        components = types.ModuleType("streamlit.components")

    components_v1 = None if force else sys.modules.get("streamlit.components.v1")
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
