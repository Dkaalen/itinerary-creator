"""Architecture contract for the Streamlit entry point and lazy route registry."""

from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import textwrap
import types

from app_modules.route_registry import (
    CALCULATOR_PAGE,
    DEFAULT_ROUTE_SPEC,
    DIRECT_PAGE_ROUTE_SPECS,
    EDIT_STAGE,
    EXPORT_STAGE,
    INPUT_STAGE,
    LOCAL_LIBRARY_PAGE,
    PICTURES_STAGE,
    REGISTERED_ROUTE_SPECS,
    STREAMLIT_ENTRY_POINT,
    SUPPORTED_APP_PAGES,
    SUPPORTED_WORKFLOW_STAGES,
    WORKFLOW_PAGE,
    WORKFLOW_ROUTE_SPECS,
    registered_route_ids,
    route_spec_for,
)


ROOT = Path(__file__).resolve().parents[1]
PAGE_MODULES = {route.module_name for route in REGISTERED_ROUTE_SPECS}
HEAVY_PREFIXES = (
    "app_modules.project_browser",
    "calculator.library_",
    "calculator_grid_component",
    "images",
    "parser_modules",
    "pdf_exporter_modules",
    "project_storage",
    "visual_editor_component",
)
EXTERNAL_HEAVY_MODULES = ("openpyxl", "reportlab")


def _run_clean_probe(body: str) -> dict[str, object]:
    prelude = textwrap.dedent(
        f"""
        import json
        import sys
        from pathlib import Path
        root = Path({str(ROOT)!r})
        sys.path.insert(0, str(root))
        """
    )
    script = prelude + "\n" + textwrap.dedent(body)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return json.loads(completed.stdout)


def test_single_entry_point_and_registry_are_complete_and_unique() -> None:
    assert STREAMLIT_ENTRY_POINT == "app.py"
    assert SUPPORTED_APP_PAGES == (WORKFLOW_PAGE, CALCULATOR_PAGE, LOCAL_LIBRARY_PAGE)
    assert SUPPORTED_WORKFLOW_STAGES == (INPUT_STAGE, EDIT_STAGE, PICTURES_STAGE, EXPORT_STAGE)
    assert tuple(WORKFLOW_ROUTE_SPECS) == SUPPORTED_WORKFLOW_STAGES
    assert tuple(DIRECT_PAGE_ROUTE_SPECS) == (CALCULATOR_PAGE, LOCAL_LIBRARY_PAGE)
    assert len(registered_route_ids()) == len(set(registered_route_ids())) == 6
    assert DEFAULT_ROUTE_SPEC is WORKFLOW_ROUTE_SPECS[INPUT_STAGE]

    for route in REGISTERED_ROUTE_SPECS:
        assert route.module_name.startswith("app_modules.")
        assert route.renderer_name.startswith("render_")


def test_route_resolution_preserves_default_invalid_and_direct_page_behavior() -> None:
    assert route_spec_for(None, None) is DEFAULT_ROUTE_SPEC
    assert route_spec_for("unknown-page", "unknown-stage") is DEFAULT_ROUTE_SPEC
    assert route_spec_for("unknown-page", EDIT_STAGE) is WORKFLOW_ROUTE_SPECS[EDIT_STAGE]
    assert route_spec_for(WORKFLOW_PAGE, EXPORT_STAGE) is WORKFLOW_ROUTE_SPECS[EXPORT_STAGE]
    assert route_spec_for(CALCULATOR_PAGE, EXPORT_STAGE) is DIRECT_PAGE_ROUTE_SPECS[CALCULATOR_PAGE]
    assert route_spec_for(LOCAL_LIBRARY_PAGE, INPUT_STAGE) is DIRECT_PAGE_ROUTE_SPECS[LOCAL_LIBRARY_PAGE]


def test_router_resolves_missing_invalid_and_picture_gated_session_state() -> None:
    from app_modules.main_view import resolve_active_route

    assert resolve_active_route({}).route_id == "workflow:input"
    assert resolve_active_route({"active_app_page": "invalid", "app_stage": "invalid"}).route_id == "workflow:input"
    assert resolve_active_route(
        {
            "active_app_page": "invalid",
            "app_stage": EDIT_STAGE,
            "parsed_rows": [{"day": "Day 1"}],
            "output_edits": {},
        }
    ).route_id == "workflow:edit"
    assert resolve_active_route(
        {
            "app_stage": PICTURES_STAGE,
            "parsed_rows": [{"day": "Day 1"}],
            "output_edits": {},
        }
    ).route_id == "workflow:edit"
    assert resolve_active_route(
        {
            "app_stage": PICTURES_STAGE,
            "parsed_rows": [{"day": "Day 1"}],
            "output_edits": {"pictures_added": True},
        }
    ).route_id == "workflow:pictures"




def test_root_entry_point_executes_only_the_supported_bootstrap(monkeypatch) -> None:
    calls: list[str] = []
    entry_module = types.ModuleType("app_modules.streamlit_entry")
    entry_module.run_streamlit_app = lambda: calls.append("run")
    monkeypatch.setitem(sys.modules, "app_modules.streamlit_entry", entry_module)

    runpy.run_path(str(ROOT / STREAMLIT_ENTRY_POINT), run_name="__main__")

    assert calls == ["run"]


def test_back_forward_navigation_and_session_restart_resolve_registered_routes() -> None:
    from app_modules.calculator_navigation import (
        close_calculator_page,
        open_calculator_page,
        open_local_library_page,
    )
    from app_modules.main_view import resolve_active_route
    from app_modules.workflow_navigation import transition_workflow_stage
    from app_modules.workflow_state import ensure_workflow_defaults

    state: dict[str, object] = {
        "parsed_rows": [{"day": "Day 1"}],
        "output_edits": {},
    }
    ensure_workflow_defaults(state)
    transition_workflow_stage(state, EDIT_STAGE)

    open_calculator_page(state)
    assert resolve_active_route(state).route_id == CALCULATOR_PAGE

    open_local_library_page(state)
    assert resolve_active_route(state).route_id == LOCAL_LIBRARY_PAGE

    close_calculator_page(state)
    assert resolve_active_route(state).route_id == "workflow:edit"

    restarted: dict[str, object] = {}
    ensure_workflow_defaults(restarted)
    assert resolve_active_route(restarted) is DEFAULT_ROUTE_SPEC


def test_route_loader_imports_only_the_registered_target(monkeypatch) -> None:
    import app_modules.main_view as main_view

    imported: list[str] = []
    rendered: list[str] = []

    def fake_import(module_name: str):
        imported.append(module_name)
        route = next(route for route in REGISTERED_ROUTE_SPECS if route.module_name == module_name)
        return types.SimpleNamespace(**{route.renderer_name: lambda version, route=route: rendered.append(f"{route.route_id}:{version}")})

    monkeypatch.setattr(main_view, "import_module", fake_import)
    for route in REGISTERED_ROUTE_SPECS:
        imported.clear()
        rendered.clear()
        renderer = main_view._load_route_renderer(route)
        renderer("v-test")
        assert imported == [route.module_name]
        assert rendered == [f"{route.route_id}:v-test"]


def test_entry_router_and_registry_imports_are_side_effect_free_in_clean_process() -> None:
    for module_name in (
        "app_modules.route_registry",
        "app_modules.streamlit_entry",
        "app_modules.main_view",
    ):
        result = _run_clean_probe(
            f"""
            import {module_name}
            loaded = sorted(sys.modules)
            heavy = [
                name for name in loaded
                if name.startswith({HEAVY_PREFIXES!r}) or name in {EXTERNAL_HEAVY_MODULES!r}
            ]
            pages = sorted(set(loaded).intersection({PAGE_MODULES!r}))
            print(json.dumps({{
                "streamlit_loaded": "streamlit" in sys.modules,
                "heavy": heavy,
                "pages": pages,
            }}))
            """
        )
        assert result == {"streamlit_loaded": False, "heavy": [], "pages": []}, module_name


def test_lightweight_package_initializers_do_not_initialize_application_surfaces() -> None:
    for package_name in (
        "app_modules",
        "calculator",
        "calculator_grid_component",
        "project_storage",
        "visual_editor_component",
    ):
        result = _run_clean_probe(
            f"""
            import {package_name}
            loaded = sorted(sys.modules)
            package_children = [name for name in loaded if name.startswith({package_name!r} + ".")]
            heavy = [
                name for name in loaded
                if name != {package_name!r}
                and (name.startswith({HEAVY_PREFIXES!r}) or name in {EXTERNAL_HEAVY_MODULES!r})
            ]
            print(json.dumps({{
                "streamlit_loaded": "streamlit" in sys.modules,
                "package_children": package_children,
                "heavy": heavy,
            }}))
            """
        )
        assert result["streamlit_loaded"] is False, package_name
        assert result["package_children"] == [], package_name
        assert result["heavy"] == [], package_name


def test_calculator_component_is_declared_only_on_first_render(monkeypatch) -> None:
    import calculator_grid_component as bridge

    declarations: list[tuple[str, str]] = []
    renders: list[dict[str, object]] = []

    def declare_component(name: str, *, path: str):
        declarations.append((name, path))

        def component(**kwargs):
            renders.append(kwargs)
            return "result"

        return component

    streamlit_module = types.ModuleType("streamlit")
    components_module = types.ModuleType("streamlit.components")
    components_v1_module = types.ModuleType("streamlit.components.v1")
    components_v1_module.declare_component = declare_component
    components_module.v1 = components_v1_module
    streamlit_module.components = components_module
    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "streamlit.components", components_module)
    monkeypatch.setitem(sys.modules, "streamlit.components.v1", components_v1_module)
    monkeypatch.setattr(bridge, "_calculator_grid", None)

    assert bridge.render_calculator_grid({"rows": []}, key="first") == "result"
    assert bridge.render_calculator_grid({"rows": [1]}, key="second") == "result"
    assert len(declarations) == 1
    assert declarations[0][0] == "calculator_grid"
    assert declarations[0][1].endswith("calculator_grid_component/frontend")
    assert [render["key"] for render in renders] == ["first", "second"]


def test_streamlit_bootstrap_orders_configuration_before_ui_and_routing(monkeypatch) -> None:
    from app_modules.streamlit_entry import run_streamlit_app

    events: list[object] = []
    state: dict[str, object] = {}

    streamlit_module = types.ModuleType("streamlit")
    streamlit_module.session_state = state
    streamlit_module.set_page_config = lambda **kwargs: events.append(("config", kwargs))

    styles_module = types.ModuleType("ui.styles")
    styles_module.apply_global_styles = lambda: events.append("styles")
    workflow_module = types.ModuleType("app_modules.workflow_state")
    workflow_module.ensure_workflow_defaults = lambda received: events.append(("defaults", received is state))
    main_view_module = types.ModuleType("app_modules.main_view")
    main_view_module.render_app = lambda version, *, state: events.append(("render", version, state is streamlit_module.session_state))
    version_module = types.ModuleType("app_modules.app_version")
    version_module.APP_VERSION = "v-entry"

    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    monkeypatch.setitem(sys.modules, "ui.styles", styles_module)
    monkeypatch.setitem(sys.modules, "app_modules.workflow_state", workflow_module)
    monkeypatch.setitem(sys.modules, "app_modules.main_view", main_view_module)
    monkeypatch.setitem(sys.modules, "app_modules.app_version", version_module)

    run_streamlit_app()

    assert events == [
        (
            "config",
            {"page_title": "Itinerary Creator", "page_icon": "🧭", "layout": "wide"},
        ),
        "styles",
        ("defaults", True),
        ("render", "v-entry", True),
    ]
