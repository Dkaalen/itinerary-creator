"""Declarative application route and workflow-stage registry.

This module owns supported route names and their lazy Streamlit renderer targets.
It deliberately contains no Streamlit, workbook, image, editor, PDF, or storage
imports so routing can be inspected without initializing an application surface.
Workflow eligibility decisions remain in :mod:`app_modules.workflow_navigation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


STREAMLIT_ENTRY_POINT = "app.py"

WORKFLOW_PAGE = "workflow"
CALCULATOR_PAGE = "calculator"
LOCAL_LIBRARY_PAGE = "local_library"
SUPPORTED_APP_PAGES = (WORKFLOW_PAGE, CALCULATOR_PAGE, LOCAL_LIBRARY_PAGE)

INPUT_STAGE = "input"
EDIT_STAGE = "edit"
PICTURES_STAGE = "pictures"
EXPORT_STAGE = "export"
SUPPORTED_WORKFLOW_STAGES = (INPUT_STAGE, EDIT_STAGE, PICTURES_STAGE, EXPORT_STAGE)


@dataclass(frozen=True, slots=True)
class RouteSpec:
    """One supported application surface and its lazy renderer target."""

    route_id: str
    app_page: str
    workflow_stage: str | None
    module_name: str
    renderer_name: str


_WORKFLOW_ROUTE_SPECS = {
    INPUT_STAGE: RouteSpec(
        route_id=f"{WORKFLOW_PAGE}:{INPUT_STAGE}",
        app_page=WORKFLOW_PAGE,
        workflow_stage=INPUT_STAGE,
        module_name="app_modules.input_step",
        renderer_name="render_input_page",
    ),
    EDIT_STAGE: RouteSpec(
        route_id=f"{WORKFLOW_PAGE}:{EDIT_STAGE}",
        app_page=WORKFLOW_PAGE,
        workflow_stage=EDIT_STAGE,
        module_name="app_modules.preview_step",
        renderer_name="render_edit_page",
    ),
    PICTURES_STAGE: RouteSpec(
        route_id=f"{WORKFLOW_PAGE}:{PICTURES_STAGE}",
        app_page=WORKFLOW_PAGE,
        workflow_stage=PICTURES_STAGE,
        module_name="app_modules.picture_step",
        renderer_name="render_picture_page",
    ),
    EXPORT_STAGE: RouteSpec(
        route_id=f"{WORKFLOW_PAGE}:{EXPORT_STAGE}",
        app_page=WORKFLOW_PAGE,
        workflow_stage=EXPORT_STAGE,
        module_name="app_modules.export_page",
        renderer_name="render_export_page",
    ),
}

_DIRECT_PAGE_ROUTE_SPECS = {
    CALCULATOR_PAGE: RouteSpec(
        route_id=CALCULATOR_PAGE,
        app_page=CALCULATOR_PAGE,
        workflow_stage=None,
        module_name="app_modules.calculator_page",
        renderer_name="render_calculator_page",
    ),
    LOCAL_LIBRARY_PAGE: RouteSpec(
        route_id=LOCAL_LIBRARY_PAGE,
        app_page=LOCAL_LIBRARY_PAGE,
        workflow_stage=None,
        module_name="app_modules.local_library_page",
        renderer_name="render_local_library_page",
    ),
}

WORKFLOW_ROUTE_SPECS: Mapping[str, RouteSpec] = MappingProxyType(_WORKFLOW_ROUTE_SPECS)
DIRECT_PAGE_ROUTE_SPECS: Mapping[str, RouteSpec] = MappingProxyType(_DIRECT_PAGE_ROUTE_SPECS)
REGISTERED_ROUTE_SPECS = tuple(WORKFLOW_ROUTE_SPECS.values()) + tuple(DIRECT_PAGE_ROUTE_SPECS.values())
DEFAULT_ROUTE_SPEC = WORKFLOW_ROUTE_SPECS[INPUT_STAGE]


def route_spec_for(app_page: object, workflow_stage: object) -> RouteSpec:
    """Resolve one registered route while preserving the established fallbacks.

    Direct Calculator and Local Library routes take precedence. Missing or
    invalid application-page state falls back to the workflow, where an invalid
    stage falls back to the input surface. Eligibility downgrades such as
    ``pictures -> edit`` remain the responsibility of ``workflow_navigation``.
    """

    page_value = str(app_page or WORKFLOW_PAGE)
    direct_route = DIRECT_PAGE_ROUTE_SPECS.get(page_value)
    if direct_route is not None:
        return direct_route

    stage_value = str(workflow_stage or INPUT_STAGE)
    return WORKFLOW_ROUTE_SPECS.get(stage_value, DEFAULT_ROUTE_SPEC)


def registered_route_ids() -> tuple[str, ...]:
    return tuple(route.route_id for route in REGISTERED_ROUTE_SPECS)


__all__ = [
    "CALCULATOR_PAGE",
    "DEFAULT_ROUTE_SPEC",
    "DIRECT_PAGE_ROUTE_SPECS",
    "EDIT_STAGE",
    "EXPORT_STAGE",
    "INPUT_STAGE",
    "LOCAL_LIBRARY_PAGE",
    "PICTURES_STAGE",
    "REGISTERED_ROUTE_SPECS",
    "RouteSpec",
    "STREAMLIT_ENTRY_POINT",
    "SUPPORTED_APP_PAGES",
    "SUPPORTED_WORKFLOW_STAGES",
    "WORKFLOW_PAGE",
    "WORKFLOW_ROUTE_SPECS",
    "registered_route_ids",
    "route_spec_for",
]
