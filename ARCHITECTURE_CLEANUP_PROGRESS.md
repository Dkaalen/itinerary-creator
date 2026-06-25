# Itinerary App Architecture Cleanup Progress

This file is the handover checkpoint for the long-running architecture cleanup. It exists so a new chat can continue the work without losing the plan.

## Product rule

The app exists to create client-ready PDF itineraries from messy Excel/supplier input as fast and cleanly as possible.

Normal workflow:

```text
messy Excel/supplier input
-> Generate itinerary
-> clean editable preview
-> quick text/image edits if needed
-> Create PDF
-> Download client-ready PDF
```

Anything that does not make this faster, easier, more reliable, or more presentable is bloat.

## Non-negotiable workflow for future chats

- Use the latest uploaded full repo ZIP only as source of truth.
- Do not rely on previous patch claims unless verified in the current ZIP.
- Do not start coding unless the user has uploaded the latest ZIP.
- Patch one batch at a time.
- Validate each patch.
- Report briefly.
- Stop and wait for the user's `ok` before continuing.
- Do not send a ZIP after every patch unless it is the final patch in the agreed batch.
- After a final batch patch, send one ZIP containing only changed/added files.
- Do not send a full repo ZIP unless explicitly requested.
- Do not use `git add .`.
- Keep reports concise.

Preferred final push format:

```powershell
cd "C:\Users\DennisKålen\Desktop\itinerary_app\itinerary-creator-git"

git status

git add <changed-file-1>
git add <changed-file-2>

git commit -m "<clear commit message>"
git push -u origin HEAD
```

## Architecture principle

Do not use `one file = one function`.

Use:

```text
one file = one clear responsibility
one function = one clear job
normal workflow = only PDF-producing value
```

Before adding code, ask:

```text
Does this belong to an existing responsibility?
```

If yes, add it to the correct module.

If no, create a new module.

If the existing module is already overloaded, split first, then patch.

## Progress overview

Update this section after every completed patch batch.

```text
Overall architecture cleanup:        [####################] 100%
Critical editor/workflow cleanup:    [####################] 100%
Editor structure cleanup:            [####################] 100%
Streamlit workflow cleanup:          [####################] 100%
CSS responsibility cleanup:          [####################] 100%
Parser cleanup:                      [####################] 100%
Generation cleanup:                  [####################] 100%
PDF/images cleanup:                  [####################] 100%
Architecture guards:                 [####################] 100%
Healthcheck follow-up:                [####################] 100%
Fixture hygiene cleanup:              [####################] 100%
Cleanup leftovers and guard gaps:      [####################] 100%
Shared helper + duplicate cleanup:     [####################] 100%
Large generation core cleanup:          [####################] 100%
Remaining generation core cleanup:       [####################] 100%
```

Status legend:

```text
[ ] Not started
[~] In progress
[x] Completed
[!] Needs re-check / regression found
```

## Current known issue to verify first

[x] Right sidebar image tools have been removed from the inspector/sidebar path.

Observed unwanted sidebar block:

```text
IMAGE TOOLS
Mode
Crop
Name
CROP POSITION
REPLACEMENT IMAGE
Automatic
Use selected
Remove image
Upload
WHY THIS IMAGE
```

Required behavior:

```text
Image tools appear only on the image/canvas itself.
Right sidebar must not render image editing, replacement, crop, upload, remove, or why-this-image controls.
```

Likely source:

```text
visual_editor_component/frontend/js/editor_inspector.js
```

Look for:

```text
renderInspectorImageTools
IMAGE TOOLS
CROP POSITION
REPLACEMENT IMAGE
WHY THIS IMAGE
```

## Normal workflow bloat forbidden list

These must not appear in the normal user workflow unless behind an explicit debug/developer gate or only shown as true fatal errors:

```text
Structured input review
Parser confidence
Rows to review
Safe parser fixes
Correction queue
Review summary
Document checks
Export checks
Needs review
Ready for Client
Client QA
Warnings dashboard
0 warnings
Items need review
Export blockers panel when there are no fatal blockers
Autosave ready
Server autosave ready
Save recovery card in normal flow
Advanced tools
Right-sidebar image editing
Why this image
Image quality explanations in normal sidebar
Project downloads expander in normal export
Proposal profile selector in normal export
```

Allowed in normal workflow:

```text
Generate itinerary
Clean preview/editor
Direct text editing
Font tools
Font size tools
Color tools
DM Sans as an optional editor font, not default
Image controls on the images themselves
Save if needed
Create PDF
Download PDF
True fatal error if PDF cannot be created
```

## Recommended implementation sequence

Do not refactor the whole app at once. Use staged batches.

Recommended sequence:

```text
Batch 1: Critical editor/workflow cleanup
Batch 2: Editor structure cleanup
Batch 3: Streamlit workflow cleanup
Batch 4: CSS responsibility cleanup
Batch 5: Parser cleanup
Batch 6: Generation cleanup
Batch 7: PDF/images cleanup
Batch 8: Architecture guard system
```

The first three batches are the highest value because they protect the actual user workflow.

---

# Batch 1: Critical editor/workflow cleanup

Progress: `[####################] 100%`

Goal:

```text
Fix the visible editor/sidebar bloat and make it hard for it to return.
```

Completed in Batch 1:

```text
[x] editor_inspector.js split into responsibility modules
[x] sidebar image tools removed
[x] image editing kept on canvas/image modules only
[x] guard tests added for sidebar image bloat and normal shell bloat
[x] normal editor shell debug/review/status clutter moved behind editor_debug_shell.js
```

## Patch 1.1: Split `editor_inspector.js`

Status: [x]

Current problem:

```text
visual_editor_component/frontend/js/editor_inspector.js
```

Observed responsibility overload:

```text
selection metadata
field discovery
field editing
text formatting
source-row display
layout tools
image tools
image replacement
image crop controls
why-this-image explanations
right-sidebar rendering
event binding
```

Target structure:

```text
visual_editor_component/frontend/js/editor_inspector.js
visual_editor_component/frontend/js/editor_inspector_selection.js
visual_editor_component/frontend/js/editor_inspector_fields.js
visual_editor_component/frontend/js/editor_inspector_text_panel.js
visual_editor_component/frontend/js/editor_inspector_layout_panel.js
```

`editor_inspector.js` should only orchestrate the right inspector.

`editor_inspector_selection.js` owns:

```text
selected inspector metadata
selection card
source rows
target reveal
```

`editor_inspector_fields.js` owns:

```text
field entries
field labels
field values
field editor
reset selected/generated fields
```

`editor_inspector_text_panel.js` owns:

```text
font family
font size
color
spacing
clear formatting
```

`editor_inspector_layout_panel.js` owns:

```text
page layout controls
block layout controls
reset layout
```

Validation focus:

```text
node --check visual_editor_component/frontend/js/*.js
python scripts/import_smoke.py
focused editor inspector tests
```

## Patch 1.2: Remove sidebar image tools permanently

Status: [x]

Remove image-editing responsibilities from the right inspector entirely.

Forbidden in `editor_inspector*.js` normal render path:

```text
IMAGE TOOLS
CROP POSITION
REPLACEMENT IMAGE
Automatic
Use selected
Remove image
Upload
WHY THIS IMAGE
Why this image
image quality
```

Image editing must live only in:

```text
visual_editor_component/frontend/js/editor_image_tools.js
visual_editor_component/frontend/js/editor_image_event_handlers.js
```

Validation focus:

```text
right sidebar does not render image tools
canvas image toolbar still works
no image editing controls are lost from the image/canvas path
```

## Patch 1.3: Add guard tests against editor/sidebar bloat

Status: [x]

Add tests that fail if normal editor/sidebar source contains forbidden image-sidebar strings.

Guard terms:

```text
IMAGE TOOLS
CROP POSITION
REPLACEMENT IMAGE
WHY THIS IMAGE
Use selected
Remove image
Upload
```

Allowlist files:

```text
editor_image_tools.js
editor_image_event_handlers.js
```

Do not allow those terms in:

```text
editor_inspector.js
editor_inspector_selection.js
editor_inspector_fields.js
editor_inspector_text_panel.js
editor_inspector_layout_panel.js
render.js
```

## Patch 1.4: Clean remaining editor shell bloat regressions

Status: [x]

Remove or debug-gate normal editor shell references to:

```text
manual edits pending
warning count
PDF readiness badge
Autosave ready
Server autosave ready
Advanced tools
review center
Document checks
Export checks
```

Keep only useful normal controls:

```text
Save
Create PDF
text tools
canvas image tools
right inspector text/layout controls
```

---

# Batch 2: Editor structure cleanup

Progress: `[####################] 100%`

Completed in Batch 2:

```text
[x] state.js split into save/scroll/draft/html/editable/image-label modules
[x] render.js split into summary/final/manual/outline/shell modules
[x] document model, text tools, style presets, and readiness split by responsibility
[x] normal readiness/review rendering kept behind debug modules
```

Goal:

```text
Make the visual editor maintainable so bloat does not keep being added to catch-all files.
```

## Patch 2.1: Split `state.js`

Status: [x]

Current file:

```text
visual_editor_component/frontend/js/state.js
```

Responsibilities currently mixed:

```text
global state
save state
scroll preservation
local draft storage
HTML escaping
image focus labels
editable HTML builders
route rendering
warning patterns
```

Target structure:

```text
state.js
editor_save_state.js
editor_scroll_state.js
editor_local_draft.js
editor_html_utils.js
editor_editable_markup.js
editor_image_labels.js
```

`state.js` keeps global model/save constants and bootstrapping only.

`editor_save_state.js` owns:

```text
saveStatusLabel
saveStatusDetail
updateSaveState
updateSaveStatusUi
hydrateSaveStateFromPayload
```

`editor_scroll_state.js` owns:

```text
captureEditorScrollState
restoreEditorScrollState
allowNextDrawToResetScroll
```

`editor_local_draft.js` owns:

```text
draftStorageKey
persistLocalDraft
mergeLocalDraftOntoServerPayload
restoreLocalDraftIfAvailable
clearLocalDraft
```

`editor_html_utils.js` owns:

```text
esc
escAttr
```

`editor_editable_markup.js` owns:

```text
editableText
editableSpan
editableHtml
editableRoute
routeHtml
splitRouteParts
```

`editor_image_labels.js` owns:

```text
focusPos
imageFocusLabel
picturesAdded
```

## Patch 2.2: Split `render.js`

Status: [x]

Current file:

```text
visual_editor_component/frontend/js/render.js
```

Responsibilities currently mixed:

```text
summary rendering
final page rendering
manual page rendering
document outline
page menu
editor shell
status panels
draw loop
```

Target structure:

```text
render.js
editor_render_summary.js
editor_render_final_pages.js
editor_render_manual_pages.js
editor_document_outline.js
editor_shell.js
```

`render.js` keeps:

```text
render(payload)
draw()
mount editor shell
```

`editor_render_summary.js` owns summary page rendering.

`editor_render_final_pages.js` owns final text/html page rendering and list text to HTML.

`editor_render_manual_pages.js` owns manual page rendering.

`editor_document_outline.js` owns:

```text
pageTypeLabel
renderDocumentOutline
pagesMenuHtml
```

`editor_shell.js` owns:

```text
clean top editor shell
save button
create PDF button area
right inspector mount
```

Normal shell must not own:

```text
status dashboards
autosave cards
review center
readiness panels
advanced tools
warning pills
```

## Patch 2.3: Split `editor_document_model.js`

Status: [x]

Current file:

```text
visual_editor_component/frontend/js/editor_document_model.js
```

Responsibilities currently mixed:

```text
page model
block model
page ordering
field-key inference
selection state
manual page templates
manual block templates
layout overrides
manual page/block CRUD
```

Target structure:

```text
editor_document_model.js
editor_pages_model.js
editor_blocks_model.js
editor_selection_model.js
editor_manual_pages.js
editor_layout_overrides.js
```

`editor_document_model.js` keeps shared exports and compatibility wrappers only.

`editor_pages_model.js` owns:

```text
documentPages
sortedDocumentPages
pageObjectAt
documentPageById
pageIndexById
pageIsHidden
ensureDocumentPage
renumberDocumentPageOrders
```

`editor_blocks_model.js` owns:

```text
contractBlock
manualBlockContextFromSelection
ensureBlockStyleOverrides
blockLayoutClasses
```

`editor_selection_model.js` owns:

```text
selectEditorPage
selectEditorFieldByKey
selectEditorBlockFromElement
selectedEditorElement
selectedPageContract
selectedBlockContract
updateSelectionUi
```

`editor_manual_pages.js` owns:

```text
manualPageTemplateCatalog
manualPageTemplateOptionsHtml
manualBlockTemplateOptionsHtml
manualBlockTemplate
manualPageFromTemplate
createManualBlock
addManualBlockToSelectedPage
duplicateSelectedManualBlock
deleteSelectedManualBlock
moveManualBlockToIndex
```

`editor_layout_overrides.js` owns:

```text
pageLayoutClasses
blockLayoutClasses
setSelectedPageOverride
resetSelectedPageLayout
setSelectedBlockOverride
```

## Patch 2.4: Split `editor_text_tools.js`

Status: [x]

Current file:

```text
visual_editor_component/frontend/js/editor_text_tools.js
```

Responsibilities currently mixed:

```text
editable DOM lookup
undo
reset
selection memory
range styling
font/color/size presets
spacing presets
controlled blocks
paste sanitizing
```

Target structure:

```text
editor_text_tools.js
editor_text_dom.js
editor_text_selection.js
editor_text_formatting.js
editor_text_history.js
editor_insert_blocks.js
editor_paste_sanitizer.js
```

`editor_text_tools.js` becomes orchestration only.

`editor_text_dom.js` owns:

```text
isHtmlEditKey
editableValue
writeEditableValue
findEditableByKey
selectedEditable
editableFromSelectionNode
closestEditableBlock
isRichEditable
```

`editor_text_selection.js` owns:

```text
rememberCanvasSelection
restoreCanvasSelection
selectionRangeInside
selectedNodeInside
selectedStyleTarget
selectedTextToolEditable
selectedTextToolTarget
```

`editor_text_formatting.js` owns:

```text
applyClassPreset
applyTextStylePreset
applyFontFamilyPreset
applyFontSizePreset
applyColorPreset
applySpacingPreset
clearSelectedFormatting
removeClassGroup
removeClassGroupDeep
styleSelectedRange
```

`editor_text_history.js` owns:

```text
pushUndo
undoLastEdit
resetSelectedBlock
restoreValueForKey
fieldDiffState
```

`editor_insert_blocks.js` owns:

```text
insertControlledBlock
insertHtmlAtSelectionOrEnd
addNoteBlock
addDividerBlock
```

`editor_paste_sanitizer.js` owns:

```text
plainTextToCleanPasteHtml
sanitizeClipboardHtml
insertCleanClipboardHtml
```

## Patch 2.5: Split style preset behavior

Status: [x]

Current file:

```text
visual_editor_component/frontend/js/style_presets.js
```

Target structure:

```text
style_presets.js
style_preset_data.js
style_preset_lookup.js
editor_block_templates.js
```

`style_presets.js` keeps compatibility exports.

`style_preset_data.js` owns static/generated preset data.

`style_preset_lookup.js` owns:

```text
controlledPresetGroup
controlledPresetClassMap
controlledPresetClassNames
controlledEditorAllowedClasses
controlledPresetOptionsHtml
```

`editor_block_templates.js` owns:

```text
controlledBlockTemplate
```

Requirement:

```text
Current default font stays default.
DM Sans remains optional only in editor font options.
```

## Patch 2.6: Move readiness/review UI to debug-only module

Status: [x]

Current file:

```text
visual_editor_component/frontend/js/editor_readiness.js
```

Target structure:

```text
editor_readiness.js
editor_debug_readiness.js
editor_warning_model.js
```

Normal editor rendering must not include:

```text
Document checks
Export checks
PDF readiness badge
warning panel
review center
```

`editor_warning_model.js` may keep non-rendering warning extraction if internally needed.

`editor_debug_readiness.js` owns debug-only review panels.

---

# Batch 3: Streamlit workflow cleanup

Progress: `[####################] 100%`

Completed in Batch 3:

```text
[x] main_view.py reduced to stage routing
[x] workflow actions split by generation/project/image/export responsibility
[x] parser/review/diagnostic UI placed behind one debug boundary
[x] workflow guard tests added for normal-flow cleanliness
```

Goal:

```text
Make the Python app flow match the simple product flow and keep debug panels out of normal usage.
```

## Patch 3.1: Split `app_modules/main_view.py`

Status: [x]

Current file:

```text
app_modules/main_view.py
```

Responsibilities currently mixed:

```text
stage routing
top navigation
hero/header
input page
generation messages
editor page
image-bank gateway UI
picture stage
export stage
debug tools
```

Target structure:

```text
app_modules/main_view.py
app_modules/workflow_config.py
app_modules/app_header.py
app_modules/input_step.py
app_modules/preview_step.py
app_modules/image_gateway_ui.py
app_modules/picture_step.py
app_modules/export_page.py
app_modules/debug_tools.py
```

`main_view.py` keeps only:

```text
render_app(app_version)
stage routing
```

`workflow_config.py` owns:

```text
FLOW_STAGES
STAGE_LABELS
normal workflow copy
```

`app_header.py` owns:

```text
_render_app_header
_render_top_nav
_stage_panel
```

`input_step.py` owns:

```text
render_input_page
paste text box
generate button
load project
```

`preview_step.py` owns:

```text
render_edit_page
_render_document_editor
normal clean preview flow
```

`image_gateway_ui.py` owns:

```text
_current_image_bank_requests
_current_image_bank_status
_connect_current_image_bank
_image_status_notice
_image_bank_gateway_is_blocking
_render_image_bank_gateway_repair
```

`picture_step.py` owns picture-stage behavior if the separate stage remains.

`export_page.py` owns:

```text
render_export_page
```

`debug_tools.py` owns:

```text
render_debug_tools
parser diagnostics
health report
structured input review if kept
```

## Patch 3.2: Split `workflow_actions.py`

Status: [x]

Current file:

```text
app_modules/workflow_actions.py
```

Responsibilities currently mixed:

```text
generate itinerary
load project
retry image bank
enter picture stage
enter export stage
```

Target structure:

```text
app_modules/workflow_actions.py
app_modules/generation_action.py
app_modules/project_load_action.py
app_modules/image_stage_action.py
app_modules/export_stage_action.py
```

`workflow_actions.py` keeps compatibility imports only.

`generation_action.py` owns:

```text
generate_itinerary
```

`project_load_action.py` owns:

```text
load_project
```

`image_stage_action.py` owns:

```text
retry_image_bank_connection
enter_picture_stage
```

`export_stage_action.py` owns:

```text
enter_export_stage
```

## Patch 3.3: Create a real debug boundary

Status: [x]

Add or consolidate one clear debug gate, for example:

```text
app_modules/debug_mode.py
```

Owns:

```text
is_debug_mode()
```

Everything diagnostic must be behind this boundary:

```text
structured input review
parser confidence
safe parser fixes
correction queue
review summary
advisory warnings
export checks dashboard
project diagnostics
QA reports
```

Normal flow must not render these.

## Patch 3.4: Add workflow guard tests

Status: [x]

Guard tests should assert:

```text
Generate itinerary normal path goes to preview/editor.
Structured input review is not rendered in normal flow.
Export page normal path shows Create PDF / Download PDF only.
Fatal errors are still visible when PDF creation is blocked.
```

---

# Batch 4: CSS responsibility cleanup

Progress: `[####################] 100%`

Goal:

```text
Remove patch-history CSS layering and organize styles by responsibility.
```

Completed in Batch 4:

```text
[x] editor.css rebuilt as responsibility-based imports
[x] patch-history workspace/review/image-inspector CSS files removed
[x] Streamlit global CSS split into UI style modules
[x] itinerary preview/PDF CSS builder split into focused modules
[x] CSS asset tests updated to guard against patch-history file regressions
```

Current CSS smell:

```text
editor_workspace_late.css
editor_workspace_corrections.css
editor_workspace_final.css
editor_review_final.css
```

These names reflect patch history, not product responsibility.

## Patch 4.1: Rebuild editor CSS import structure

Status: [x]

Target import set:

```text
editor_tokens.css
editor_base.css
editor_pages.css
editor_shell.css
editor_toolbar.css
editor_text_tools.css
editor_image_tools.css
editor_inspector.css
editor_layout_tools.css
editor_manual_pages.css
editor_final_pages.css
editor_debug.css
editor_responsive.css
```

## Patch 4.2: Merge workspace patch-history files

Status: [x]

Merge/remove:

```text
editor_workspace_late.css
editor_workspace_corrections.css
editor_workspace_final.css
```

Move rules into responsibility files.

## Patch 4.3: Remove or debug-gate review/image-inspector CSS

Status: [x]

Remove or isolate:

```text
editor_review.css
editor_review_final.css
editor_image_inspector.css
```

Normal workflow should not need review panel CSS or sidebar image inspector CSS.

## Patch 4.4: Split Streamlit/global CSS blobs

Status: [x]

Current file:

```text
ui/styles.py
```

Target structure:

```text
ui/styles.py
ui/style_tokens.py
ui/style_app_shell.py
ui/style_workflow.py
ui/style_forms.py
ui/style_export.py
ui/style_image_bank.py
ui/style_debug.py
ui/style_responsive.py
```

`ui/styles.py` keeps `apply_global_styles()` only as an aggregator.

## Patch 4.5: Split itinerary preview CSS builder

Status: [x]

Current file:

```text
app_modules/itinerary_html_styles.py
```

Target structure:

```text
app_modules/itinerary_html_styles.py
app_modules/preview_css_tokens.py
app_modules/preview_css_cover.py
app_modules/preview_css_summary.py
app_modules/preview_css_day_pages.py
app_modules/preview_css_final_pages.py
app_modules/preview_css_images.py
app_modules/preview_css_responsive.py
```

`itinerary_html_styles.py` keeps `build_preview_style(...)` as an aggregator.

---

# Batch 5: Parser cleanup

Progress: `[--------------------] 0%`

Goal:

```text
Make messy Excel/supplier parsing easier to maintain without changing output.
```

## Patch 5.1: Split `parser_modules/details.py`

Status: [x]

Current responsibilities mixed:

```text
text cleanup
detail extraction
title cleanup
title/prose splitting
comma-list parsing
effective type detection
```

Target structure:

```text
parser_modules/details.py
parser_modules/row_text_standardization.py
parser_modules/detail_extractors.py
parser_modules/title_cleanup.py
parser_modules/list_parsing.py
parser_modules/effective_type_detection.py
```

`details.py` keeps compatibility exports only.

## Patch 5.2: Split `parser_modules/parser_main.py`

Status: [x]

Target structure:

```text
parser_modules/parser_main.py
parser_modules/date_fields.py
parser_modules/raw_row_context.py
parser_modules/city_inference.py
parser_modules/row_builder.py
parser_modules/row_enrichment.py
```

`parse_itinerary(raw_text)` should become:

```text
read rows -> build context -> build row -> enrich row -> append row
```

## Patch 5.3: Parser regression protection

Status: [x]

Before and after parser split, run parser tests and focused transport tests.

Focus areas:

```text
self transfers always excluded
night train classified as rail
Norway in a Nutshell segment fidelity
coastal cruise stays specialized
South Coast title parsing
flight luggage wording
hotel nights/destination parsing
```

---

# Batch 6: Generation cleanup

Progress: `[####################] 100%`

Goal:

```text
Make generated itinerary copy/render logic easier to improve without regressions.
```

Completed in Batch 6:

```text
[x] generation facades now isolate day intro, summaries, activity titles, structured document, editable draft, quality gate, QA report, nutshell, exclusions, and day render responsibilities
[x] existing public imports remain compatibility-safe
[x] normal workflow behavior unchanged
[x] focused generation/quality/structured tests pass
```

## Patch 6.1: Split `day_intro_engine.py`

Status: [x]

Target structure:

```text
itinerary_generation/day_intro_engine.py
itinerary_generation/day_intro_classification.py
itinerary_generation/day_intro_route.py
itinerary_generation/day_intro_activity.py
itinerary_generation/day_intro_arrival.py
```

`create_day_intro()` should become a short decision tree.

## Patch 6.2: Split `summaries.py`

Status: [x]

Target structure:

```text
itinerary_generation/summaries.py
itinerary_generation/trip_glance_builder.py
itinerary_generation/journey_arc_builder.py
itinerary_generation/city_experience_classifier.py
itinerary_generation/journey_arc_text_safety.py
```

## Patch 6.3: Split `activity_titles.py`

Status: [x]

Target structure:

```text
itinerary_generation/activity_titles.py
itinerary_generation/activity_title_normalization.py
itinerary_generation/activity_title_rules.py
itinerary_generation/activity_title_patterns.py
```

`create_client_activity_title(row)` should become:

```text
normalize source -> classify activity -> apply rule -> clean result
```

## Patch 6.4: Split `structured_builder.py`

Status: [x]

Target structure:

```text
itinerary_generation/structured_builder.py
itinerary_generation/structured_items_builder.py
itinerary_generation/structured_warning_builder.py
itinerary_generation/structured_days_builder.py
itinerary_generation/structured_travel_sequences.py
itinerary_generation/structured_final_sections.py
```

## Patch 6.5: Split `editable_draft.py`

Status: [x]

Target structure:

```text
itinerary_generation/editable_draft.py
itinerary_generation/editable_draft_model.py
itinerary_generation/editable_draft_normalize.py
itinerary_generation/editable_draft_merge.py
itinerary_generation/editable_draft_lookup.py
itinerary_generation/legacy_output_edits_bridge.py
```

The legacy bridge should be isolated so it can eventually be removed.

## Patch 6.6: Split `quality_gate.py`

Status: [x]

Target structure:

```text
itinerary_generation/quality_gate.py
itinerary_generation/generation_quality_gate.py
itinerary_generation/client_output_quality_gate.py
itinerary_generation/render_document_text_scan.py
itinerary_generation/image_quality_gate.py
```

Important:

```text
Quality checks should not create normal UI bloat.
They should return fatal messages only when needed.
```

## Patch 6.7: Move QA report to debug/reporting area

Status: [x]

Current file:

```text
itinerary_generation/qa_report.py
```

Target debug structure:

```text
itinerary_generation/debug/qa_report_model.py
itinerary_generation/debug/qa_edit_events.py
itinerary_generation/debug/qa_warning_events.py
itinerary_generation/debug/qa_report_render.py
itinerary_generation/debug/qa_report_persist.py
```

Normal app flow should not import QA report rendering.

## Patch 6.8: Split specialist generation/render helpers

Status: [x]

Targets:

```text
itinerary_generation/nutshell_domain.py
itinerary_generation/exclusion_sections.py
itinerary_generation/day_render_blocks.py
```

Potential structures:

```text
nutshell_model.py
nutshell_detection.py
nutshell_source.py
nutshell_route_parser.py
nutshell_journey_builder.py
```

```text
exclusion_self_transfers.py
exclusion_flights.py
exclusion_commercial_items.py
exclusion_formatting.py
```

```text
day_render_activity_blocks.py
day_render_transport_blocks.py
day_render_hotel_blocks.py
day_render_group_tour_blocks.py
day_render_leisure_blocks.py
day_render_block_ordering.py
```

---

# Batch 7: PDF/images cleanup

Progress: `[####################] 100%`

Goal:

```text
Make PDF export and image-bank reliability easier to maintain.
```

## Patch 7.1: Split `pdf_exporter_modules/typed_exporter.py`

Status: [x]

Target structure:

```text
pdf_exporter_modules/typed_exporter.py
pdf_exporter_modules/pdf_html_fallback.py
pdf_exporter_modules/pdf_cover_renderer.py
pdf_exporter_modules/pdf_summary_renderer.py
pdf_exporter_modules/pdf_day_renderer.py
pdf_exporter_modules/pdf_image_renderer.py
pdf_exporter_modules/pdf_final_section_renderer.py
pdf_exporter_modules/pdf_internal_review_appendix.py
```

`typed_exporter.py` keeps:

```text
export_render_document_to_pdf
```

Internal review appendix should be debug-only or removed from normal output if not needed.

## Patch 7.2: Split `pdf_exporter_modules/styles.py`

Status: [x]

Target structure:

```text
pdf_exporter_modules/styles.py
pdf_exporter_modules/pdf_style_tokens.py
pdf_exporter_modules/pdf_style_base.py
pdf_exporter_modules/pdf_style_cover.py
pdf_exporter_modules/pdf_style_summary.py
pdf_exporter_modules/pdf_style_day.py
pdf_exporter_modules/pdf_style_final_pages.py
pdf_exporter_modules/pdf_style_tables.py
```

`styles.py` keeps:

```text
make_styles
```

## Patch 7.3: Split `images/remote_distribution.py`

Status: [x]

Target structure:

```text
images/remote_distribution.py
images/remote_distribution_models.py
images/remote_distribution_config.py
images/remote_distribution_requests.py
images/remote_manifest.py
images/remote_pack_resolver.py
images/remote_archive_install.py
images/remote_distribution_locking.py
images/remote_distribution_prefetch.py
```

`remote_distribution.py` keeps compatibility façade exports only.

Completed in Batch 7:

```text
[x] typed_exporter.py reduced to typed PDF orchestration and compatibility exports
[x] cover, summary, day, image, final-section, fallback, and internal-review PDF responsibilities split
[x] styles.py reduced to style orchestration, palette/footer wrappers, and compatibility exports
[x] PDF style tokens/base/cover/day/summary/table/final modules added
[x] remote_distribution.py reduced to compatibility façade exports
[x] remote image-bank models, config, requests, pack resolver, archive install, locking, manifest orchestration, and prefetch modules added
```

---

# Batch 8: Architecture guard system

Progress: `[####################] 100%`

Goal:

```text
Stop future chats from adding bloat to the wrong files.
```


Completed in Batch 8:

```text
[x] source-level normal-workflow bloat guard helpers added
[x] file-size and function-size guard helpers added
[x] patch-history/vague-name guard helpers added
[x] lazy import boundaries added for debug review panels
[x] PDF internal review appendix lazy-loaded only when enabled
[x] architecture guard tests added to the architecture test group
```

## Batch 9: Healthcheck follow-up

Progress: `[####################] 100%`

Completed in Batch 9:

```text
[x] refreshed stale frontend source-contract tests after the editor split
[x] restored premium Norway in a Nutshell timeline mode labels
[x] verified baseline compile/import/frontend syntax gates
```

## Patch 8.1: Add source-level bloat guards

Status: [x]

Fail tests if normal workflow files contain forbidden visible bloat strings.

Forbidden normal UI strings:

```text
Document checks
Export checks
Autosave ready
Server autosave ready
Advanced tools
Structured input review
Rows to review
Parser confidence
Safe parser fixes
Correction queue
Review summary
Client QA
Ready for Client
Needs Review
WHY THIS IMAGE
IMAGE TOOLS
REPLACEMENT IMAGE
```

Allow only in debug modules or explicitly allowlisted test fixtures.

## Patch 8.2: Add file-size / responsibility guards

Status: [x]

Suggested thresholds:

```text
Frontend JS > 350 lines -> warning
Frontend JS > 500 lines -> fail unless allowlisted
Python workflow file > 350 lines -> warning
Function > 120 lines -> warning
Function > 200 lines -> fail unless allowlisted
CSS file named late/final/corrections -> fail after CSS cleanup
```

Allowlist exceptions:

```text
data registries
test fixtures
static preset data
compatibility facades
```

## Patch 8.3: Add naming guards

Status: [x]

Discourage vague or patch-history names:

```text
utils
helpers
final
late
corrections
new
old
misc
```

Exception only when already existing and intentionally retained for compatibility.

## Patch 8.4: Add import-boundary guards

Status: [x]

Suggested boundaries:

```text
normal app flow must not import debug report renderers
normal editor shell must not import debug readiness renderer
right inspector must not import image replacement/upload tools
PDF normal export must not import internal review appendix rendering unless explicitly enabled
```

---

# Files not recommended for immediate split

These are acceptable or lower priority right now:

```text
visual_editor_component/frontend/js/editor_image_tools.js
visual_editor_component/frontend/js/editor_image_event_handlers.js
visual_editor_component/frontend/js/editor_page_event_handlers.js
visual_editor_component/frontend/js/commands.js
visual_editor_component/frontend/js/streamlit_bridge.js
app_modules/export_step.py
app_modules/export_state.py
app_modules/pdf_preflight.py
app_modules/editor_commit.py
app_modules/workflow_state.py
images/image_uploads.py
images/image_overrides.py
images/replacement_options.py
pdf_exporter_modules/day_page_guard.py
pdf_exporter_modules/image_layout.py
parser_modules/time_finders.py
parser_modules/time_duration.py
parser_modules/time_tokens.py
shared/*
```

Compatibility façade files are acceptable when they intentionally keep older imports alive:

```text
ui/activity_inclusions.py
ui/render_text_helpers.py
pdf_exporter_modules/images.py
parser_modules/time_parsing.py
parser_modules/extractors.py
```

# Large data/registry files

Large data-like registry files are not the same problem as catch-all behavior files.

Example:

```text
itinerary_generation/data/nordic_destination_registry.py
```

This may be split later by country, but it is lower priority than workflow/editor files.

Potential future structure:

```text
itinerary_generation/data/destination_models.py
itinerary_generation/data/destination_alias_index.py
itinerary_generation/data/destinations_norway.py
itinerary_generation/data/destinations_sweden.py
itinerary_generation/data/destinations_denmark.py
itinerary_generation/data/destinations_finland.py
itinerary_generation/data/destinations_iceland.py
itinerary_generation/data/destinations_baltics.py
```

# Required validation pattern

For each patch batch, use focused tests first.

Recommended baseline:

```bash
python -m compileall -q .
node --check visual_editor_component/frontend/js/*.js
python scripts/import_smoke.py
```

Then run focused tests for touched area:

```bash
python scripts/run_test_group.py parser
python scripts/run_test_group.py ui
python scripts/run_test_group.py editor
python scripts/run_test_group.py pdf
python scripts/run_test_group.py images
python scripts/run_test_group.py architecture
```

If a grouped runner times out, report exactly where it timed out and whether any failures appeared before timeout.

Do not claim full pass if it timed out.

Known dirty fixture files may still affect `git diff --check`:

```text
tests/fixtures/activity_training/cleaned_activity_master.tsv
tests/fixtures/activity_training/raw_messy_activity_source.txt
```

Do not modify them unless intentionally cleaning fixture whitespace.

# Suggested next chat starting instruction

Use this prompt when opening a new chat:

```text
Read ARCHITECTURE_CLEANUP_PROGRESS.md first. Treat the latest uploaded ZIP as source of truth. Do not code until the ZIP is inspected. Continue from the first unchecked item in the progress file. Keep the staged patch workflow: patch one batch, validate, report briefly, stop for ok. The product rule is: anything that does not help create a client-ready PDF faster, easier, more reliably, or more presentably is bloat.
```

# How to update this file

After each completed patch:

1. Change the relevant item from `[ ]` to `[x]`.
2. Update the progress bars.
3. Add a short note under the completed item if something important was learned.
4. Add any new known regression under `Current known issue to verify first`.
5. Do not mark work complete unless it was validated.
---

# Batch 10: Fixture hygiene cleanup

Progress: `[####################] 100%`

Goal:

```text
Remove accidental dirty fixture state caused only by CRLF line endings and guard the activity-training fixtures against drifting dirty again.
```

Completed:

```text
[x] Normalized activity-training fixture line endings to LF
[x] Verified fixture content is unchanged after line-ending normalization
[x] Added fixture hygiene guard tests
```


---

# Batch 11: Cleanup leftovers and guard gaps

Progress: `[####################] 100%`

Completed in Batch 11:

```text
[x] Removed root patch artifact manifests from the repo tree
[x] Removed stale duplicate workflow-shell test under visual_editor_component/tests
[x] Removed dead review-step workflow-card code from app_modules/workflow_shell.py
[x] Split oversized editor_shell.css into shell, workspace, outline, and page-action responsibilities
[x] Added guards for root patch artifacts, duplicate tests, CSS size, and oversized *_core.py files
```
---

# Batch 12: Shared helper + duplicate logic cleanup

Progress: `[####################] 100%`

Goal:

```text
Remove low-value helper duplication and make shared helpers the single source of truth.
```

Completed in Batch 12:

```text
[x] Replaced local clean_space implementations with shared.text.clean_space
[x] Removed stale ChatGPT patch metadata folder from the repo working tree
[x] Added architecture guard coverage for duplicated clean_space helpers
[x] Extended patch-artifact hygiene guard to catch _patch_metadata
```


## Batch 13: Large generation core cleanup

Progress: `[####################] 100%`

Completed:

- Inverted editable-draft modules so `editable_draft_model.py`, `editable_draft_normalize.py`, `editable_draft_lookup.py`, `editable_draft_merge.py`, and `editable_draft_legacy_bridge.py` own their logic.
- Inverted quality-gate modules so generation-input checks, client-output checks, and shared patterns are separate responsibilities.
- Inverted structured-builder modules so row helpers, item building, warning building, day building, travel sequencing, and final sections are split by responsibility.
- Kept `*_core.py` files as compatibility facades for older imports.
- Added architecture guards so cleaned facades do not grow back into implementation catch-alls and named modules do not import back from cleaned core files.

Validation notes:

- `quality` group stages 1-6 passed. The full grouped command timed out during stage 7, so stages 7-9 were rerun directly and passed.
- `architecture` group stages 1-6 passed. The full grouped command timed out during stage 7, so stages 7-11 were rerun directly and passed.

---

# Batch 14: Remaining generation core cleanup

Progress: `[####################] 100%`

Goal:

```text
Finish the remaining generation `_core.py` cleanup so `*_core` files stay thin compatibility facades instead of becoming new catch-all implementation files.
```

Completed in Batch 14:

```text
[x] Moved Nutshell domain implementation from `nutshell_domain_core.py` into `nutshell_domain.py`
[x] Moved exclusion-section implementation from `exclusion_sections_core.py` into `exclusion_sections.py`
[x] Moved day-intro implementation from `day_intro_engine_core.py` into `day_intro_engine.py`
[x] Moved summary/journey-arc implementation from `summaries_core.py` into `summaries.py`
[x] Moved QA-report implementation from `qa_report_core.py` into `qa_report.py`
[x] Moved day-render-block implementation from `day_render_blocks_core.py` into `day_render_blocks.py`
[x] Updated responsibility modules to import named implementation modules instead of legacy core modules
[x] Extended architecture guards so cleaned generation core facades cannot grow back into implementations
[x] Normalized group-tour overnight breakfast wording found during validation
```
