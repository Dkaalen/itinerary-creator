# Patch BZ1F deletion audit

This audit records the evidence used before removing obsolete compatibility files.

| Removed path | Production importers | Dynamic/string references | Replacement |
|---|---:|---:|---|
| `ui/transport_blocks.py` | 0 | 0 | `itinerary_generation.transport_render_blocks` and `ui.travel_sequence_blocks` |
| `visual_editor_component/app_modules/main_view.py` | 0 | 0 | `app_modules.main_view` |
| `visual_editor_component/app_modules/export_step.py` | 0 | 0 | `app_modules.export_step` |
| `visual_editor_component/app_modules/workflow_shell.py` | 0 | 0 | `app_modules.workflow_shell` |
| `visual_editor_component/ui/styles.py` | 0 | 0 | `ui.styles` |
| `_PATCH_DELETE_FILES.txt` | 0 | 0 | None; patch-process artifact only |

## Verification performed

- Repository-wide text search for dotted module names and file paths.
- AST import scan covering `import` and `from ... import ...` statements.
- Search for `importlib`, `__import__`, plugin registries and monkeypatch targets.
- Production import smoke test across all package modules.
- Fresh-extraction compilation and import smoke test of the clean archive.

Tests which previously asserted that the shims existed were changed to assert that
they remain absent and that no production source refers to them.
