from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from importlib import import_module
from typing import Any

from app_modules.route_registry import RouteSpec, WORKFLOW_PAGE, route_spec_for
from app_modules.session_state_keys import ACTIVE_APP_PAGE_KEY
from app_modules.workflow_navigation import session_stage_from_state
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT


def _session_stage(state: Mapping[str, Any]) -> str:
    return session_stage_from_state(state)


def resolve_active_route(state: Mapping[str, Any]) -> RouteSpec:
    """Resolve the current state to one registered application surface."""

    return route_spec_for(
        state.get(ACTIVE_APP_PAGE_KEY, WORKFLOW_PAGE),
        _session_stage(state),
    )


def _load_route_renderer(route: RouteSpec) -> Callable[[str], None]:
    """Import only the selected page module and return its renderer."""

    module = import_module(route.module_name)
    renderer = getattr(module, route.renderer_name)
    if not callable(renderer):
        raise TypeError(
            f"Registered renderer is not callable: {route.module_name}.{route.renderer_name}"
        )
    return renderer


def render_debug_tools() -> None:
    from app_modules.debug_tools import render_debug_tools as renderer

    renderer()


def render_app(app_version: str, *, state: MutableMapping[str, Any] | None = None) -> None:
    """Route first, then import and render only the active app surface.

    Production callers use Streamlit session state. Tests and other adapters may
    provide a session-like mapping so routing does not depend on mutable global
    state left behind by another workflow.
    """

    if state is None:
        import streamlit as st

        session = st.session_state
    else:
        session = state

    session.setdefault("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
    route = resolve_active_route(session)
    renderer = _load_route_renderer(route)
    renderer(app_version)
    render_debug_tools()


__all__ = ["render_app", "resolve_active_route"]
