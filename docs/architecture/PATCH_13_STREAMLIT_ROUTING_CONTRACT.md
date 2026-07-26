# Patch 13 — Streamlit Entry-Point and Routing Contract

## Supported application entry point

The only supported hosted application command is:

```text
streamlit run app.py
```

`app.py` is deliberately a minimal executable shim. It imports and calls
`app_modules.streamlit_entry.run_streamlit_app()` and owns no workflow,
project, workbook, image, editor, or PDF decisions.

Importing `app_modules.streamlit_entry` is side-effect free. Calling
`run_streamlit_app()` performs startup in this order:

1. Import Streamlit.
2. Apply `st.set_page_config()`.
3. Import the application version, global styles, workflow defaults, and router.
4. Apply global styles.
5. Populate missing session defaults without replacing active project state.
6. Route and render one application surface.

## Official route registry

`app_modules.route_registry` is the dependency-free owner of supported route
names and lazy renderer targets.

| Route ID | `active_app_page` | Workflow stage | Renderer target |
|---|---|---|---|
| `workflow:input` | `workflow` or missing/invalid | `input` | `app_modules.input_step.render_input_page` |
| `workflow:edit` | `workflow` or missing/invalid | `edit` | `app_modules.preview_step.render_edit_page` |
| `workflow:pictures` | `workflow` or missing/invalid | `pictures` | `app_modules.picture_step.render_picture_page` |
| `workflow:export` | `workflow` or missing/invalid | `export` | `app_modules.export_page.render_export_page` |
| `calculator` | `calculator` | ignored | `app_modules.calculator_page.render_calculator_page` |
| `local_library` | `local_library` | ignored | `app_modules.local_library_page.render_local_library_page` |

The registry owns only names and renderer locations. It does not import page
modules or decide whether a workflow stage is currently eligible.

## Navigation and fallback ownership

`app_modules.workflow_navigation` remains the owner of visible navigation state
and workflow-stage eligibility:

- Missing rows force the input stage.
- Pictures and export fall back to edit until pictures are committed.
- Invalid workflow stages normalize to input.
- Calculator, Local Library, and workflow route transitions mutate only the
  canonical route keys.

`app_modules.main_view` asks `workflow_navigation` for the eligible stage, asks
the registry for the matching route, then imports only that route's renderer.

Fallback behavior is intentionally unchanged:

- Missing route state enters the workflow.
- Invalid application-page state enters the workflow and preserves any valid,
  eligible workflow stage.
- Invalid page plus invalid stage enters `workflow:input`.
- Direct Calculator and Local Library routes take precedence over workflow stage.

## Lazy import and initialization contract

Importing any of the following must not initialize a page, workbook data, image
engine, visual editor, PDF engine, Calculator component, or project browser UI:

- `app_modules`
- `app_modules.route_registry`
- `app_modules.streamlit_entry`
- `app_modules.main_view`
- `calculator`
- `calculator_grid_component`
- `project_storage`
- `visual_editor_component`

The image and PDF package initializers retain their existing lazy public APIs.

The Calculator bridge no longer declares its Streamlit component at package
import. `calculator_grid_component.render_calculator_grid()` declares the
component once, on the first Calculator render, and reuses that declaration.

Workbook files are not opened by the entry package or router. The Local Library
read remains owned by the Calculator and Local Library page workflows after the
corresponding surface is entered.

## Preserved boundaries

Patch 13 does not move workflow logic into `app.py`, the entry bootstrap, or the
route registry. It does not change project reconstruction, Calculator state,
workbook authority, image matching, editor state, PDF generation, or storage
ownership.

Project reopening still commits the workflow route through
`project_session_transitions` and restores edit/picture stage through the
existing saved-project restoration authority.

## Enforced regression coverage

The routing contract tests cover:

- Single supported entry point.
- Complete and unique route registry.
- Default, missing, and invalid route state.
- Every registered route.
- Picture/export eligibility fallback.
- Route-specific lazy module import.
- Side-effect-free entry and package imports.
- Calculator component declaration on first render only.
- Streamlit bootstrap ordering.
- Calculator and Local Library navigation.
- Project reopening into the correct stage.
- Session reset and project-switch route behavior.
