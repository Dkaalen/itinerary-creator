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
Final healthcheck + artifact hygiene:      [####################] 100%
```

Status legend:

```text
[ ] Not started
[~] In progress
[x] Completed
[!] Needs re-check / regression found
```


## Post-cleanup product quality sprint

Architecture cleanup is complete. The next phase is end-to-end itinerary quality using real supplier inputs.

```text
Golden input inventory:           [####################] 100%
Golden input runner/reporting:    [####################] 100%
Client output quality fixes:      [####################] 100%
Preview/PDF parity hardening:     [####################] 100%
Editor product polish:            [####################] 100%
```

Current real corpus checkpoint:

```text
Vipin Nordic calculator rows:     5,557
Source workbooks represented:     2
Sheets represented:               307
Latest parser exceptions:         0
Latest generation smoke:          passed
Latest average parser confidence: 99.4%
```

Use `docs/reports/golden_input_quality_sprint.md` as the entry point for the product-quality sprint.


---

# Batch 17: Golden input title/prose quality fixes

Progress: `[####################] 100%`

Goal:

```text
Use the real Vipin Nordic calculator corpus to reduce overlong titles, supplier prose leaking into titles, and row-type/title mistakes that hurt client-ready itinerary output.
```

Completed in Batch 17:

```text
[x] Kept Day Overview rows as Day Overview even when long supplier prose mentions flights/trains/buses
[x] Added compact title extraction for sentence-style supplier prose and day activity text
[x] Converted long-distance bus/coach calculator rows into compact transport titles
[x] Stripped address/procurement notes from generic private point-to-point transfer titles
[x] Improved leading known-place city inference for titles such as Helsinki Hop on Hop off
[x] Improved malformed hotel title parsing where check-in text followed the property name
[x] Added regression tests for the new real-corpus title and city cases
[x] Re-ran the full 5,557-row Vipin corpus report
```

Full-corpus result after Batch 17:

```text
Rows checked:                  5,557
Parsed rows:                   5,438
Parser exceptions:             0
Generation smoke:              passed
Average parser confidence:     97.4%
Rows under 80 confidence:      196
Overlong title flags:          173 -> 86
Supplier prose title flags:    82 -> 63
Missing parsed city flags:     9 -> 8
```

---

# Batch 18: Golden title/prose boundary cleanup

Progress: `[####################] 100%`

Goal:

```text
Continue the real Vipin corpus quality sprint while preserving one clear responsibility per file.
```

Completed in Batch 18:

```text
[x] Split supplier title/prose boundary heuristics into parser_modules/title_prose_boundaries.py
[x] Kept parser_modules/title_cleanup.py as the title-cleanup orchestrator
[x] Fixed earliest-boundary selection so early prose markers beat later markers
[x] Compacted repeated-subject activity descriptions such as Seljalandsfoss Waterfall Seljalandsfoss...
[x] Compacted rental-car, coach, cable-car, hotel-note, and itinerary-note title shapes from the real corpus
[x] Added regression tests for the new real-corpus title shapes
[x] Re-ran the full 5,557-row Vipin corpus report
```

Full-corpus result after Batch 18:

```text
Rows checked:                  5,557
Parsed rows:                   5,438
Parser exceptions:             0
Generation smoke:              passed
Average parser confidence:     97.5%
Rows under 80 confidence:      192
Overlong title flags:          86 -> 0
Supplier prose title flags:    63 -> 0
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


---

# Batch 15: Final healthcheck + artifact hygiene cleanup

Progress: `[####################] 100%`

Goal:

```text
Run a final architecture healthcheck after the cleanup series and remove remaining patch/package artifacts from the project tree.
```

Completed in Batch 15:

```text
[x] Removed stray root `CHANGED_FILES_MANIFEST.md` from the uploaded project tree
[x] Extended `.gitignore` to block patch manifests and `_patch_metadata/`
[x] Extended clean ZIP artifact hygiene to exclude patch manifests and patch metadata
[x] Extended runtime cleanup to remove patch manifests and patch metadata
[x] Added test coverage for the strengthened artifact hygiene rules
```

---

# Batch 19: Real corpus output quality, parity, and editor polish

Progress: `[####################] 100%`

Goal:

```text
Finish the post-cleanup product-quality sprint by clearing deterministic real-corpus parsed-output defects, broadening preview/PDF parity smoke coverage, and refreshing editor no-bloat polish guards.
```

Completed in Batch 19:

```text
[x] Added contextual city inference for sparse itinerary rows without letting numeric night/count cells become cities
[x] Cleared missing parsed city, missing hotel name, missing route origin/destination, missing room category, weak title, missing hotel nights, and unexpected skip output buckets
[x] Hardened hotel extraction for Excel serial dates, malformed star-hotel rows, room quantities, igloos, suites, chalets, studios, and meal-text leakage
[x] Hardened route extraction for Norway in a Nutshell, timed multileg transfers, airport flights, trains, buses, coaches, and local transfer summaries
[x] Reclassified report-only calculator/header rows as source-data/reporting cases instead of parser output failures
[x] Extended representative golden-input preview/PDF parity smoke coverage across multiple real fixture itineraries
[x] Refreshed editor design-polish and no-bloat guards against the split frontend source files
[x] Preserved the clean normal workflow with no new normal-user dashboards, QA panels, readiness gates, or sidebar image-tool bloat
```

Full-corpus result after Batch 19:

```text
Rows checked:                       5,557
Parsed output rows:                 5,439
Generated editable titles checked:  4,194
Parser exceptions:                  0
Rows skipped by parser:             118
Average parser confidence:          99.4%
Rows under 80 confidence:           0
Whole-corpus generation smoke:      passed
Parser review flags remaining:      very_long_supplier_text: 324
```

Remaining bad-output log categories are source-data/reporting categories rather than deterministic parsed-output defects:

```text
missing_source_city: 381
missing_source_date: 87
missing_source_day: 85
non_itinerary_type: 65
missing_source_type: 21
```

---

# Batch 20: Responsibility cleanup hardening

Progress: `[####################] 100%`

Goal:

```text
Future-proof the remaining broad responsibility files so each file has one clear responsibility or acts only as a thin compatibility facade.
```

Completed in Batch 20:

```text
[x] Converted `itinerary_generation/day_intro_engine.py` into a thin public facade and moved intro orchestration into responsibility modules
[x] Converted `itinerary_generation/nutshell_domain.py` into a compatibility facade backed by Nutshell model, constants, cleaning, source, route parsing, detection, and journey-builder modules
[x] Converted `itinerary_generation/day_render_blocks.py` into a UI-neutral facade backed by activity, transport, ordering, and document-adapter render modules
[x] Reduced `app_modules/itinerary_render_context.py` to a render-context coordinator backed by document, cover-data, summary-data, and final-section-data modules
[x] Reduced `app_modules/export_actions.py` to a PDF export coordinator backed by PDF artifact, editor-commit, issue-display, image-validation, and render-context modules
[x] Converted `itinerary_generation/qa_report.py` into a facade backed by QA model, helper, edit, warning, builder, rendering, and persistence modules
[x] Converted `itinerary_generation/input_review.py` into a facade backed by review models, helpers, rows, corrections, builder, and formatting modules
[x] Converted `itinerary_generation/exclusion_sections.py` into a facade backed by exclusion constants, row rules, source items, specific sections, and final builder modules
[x] Converted `itinerary_generation/summaries.py` into a facade backed by summary text, trip-glance, experience, and journey-arc modules
[x] Converted `scripts/vipin_excel_corpus.py` into a CLI/facade backed by a small `scripts/vipin_corpus/` package
[x] Re-split oversized helper functions discovered by the architecture guard in `day_intro_orchestrator.py` and `summaries_experience.py`
[x] Preserved compatibility imports for existing callers while keeping implementation ownership in the new responsibility modules
```

Validation snapshot:

```text
python -m compileall -q .
node --check visual_editor_component/frontend/js/*.js
python scripts/import_smoke.py
Focused architecture/export/parity/corpus tests: 98 passed
Architecture group stages 1-5 passed through the grouped runner
Architecture stage 6 timed out with no failure shown; stage 6 rerun directly and passed
Architecture stages 7-11 rerun directly in chunks and passed
```

---

# Batch 21: Second-layer responsibility cleanup

Progress: `[####################] 100%`

Goal:

```text
Finish the second-layer "one file = one clear responsibility" cleanup without changing the user-facing workflow.
```

Completed in Batch 21:

```text
[x] Split destination profile model/data/build/copy responsibilities
[x] Split editor page contract model/ID/build/query responsibilities
[x] Split PDF controlled content, inclusion, block, day, and general-page rendering
[x] Split hotel normalization into dates/meals/rooms/names/row orchestration
[x] Split hotel parsing into meal, room, and detail parsing
[x] Split transport sequence, special-route, and arrangement rendering
[x] Split group-tour source enrichment, presentation, and inclusion responsibilities
[x] Split image-bank paths, recursive scanning, index construction, and cache API
[x] Split client-output text, content/time checks, image checks, and report model
[x] Split itinerary health models, row/route facts, destination checks, and orchestration
[x] Split reference-corpus models/loaders and offline TSV/XLSX/manifest/CLI builders
[x] Split activity-training text/model/loading/matching/validation responsibilities
[x] Split product-rule models/context/evidence/descriptions/matching responsibilities
[x] Split structured-document source coverage from ID/cross-reference integrity
[x] Split image matcher destination context from service/theme inference
[x] Split single-row normalization from itinerary-level normalization orchestration
[x] Re-checked destination_content.py and summaries_experience.py as cohesive copy generators
[x] Re-checked scripts/test_groups.py as a focused test registry/stage builder
[x] Preserved compatibility facades and legacy private hooks still used by callers/tests
```

Validation snapshot:

```text
Full Python compilation: passed
git diff --check: passed
Architecture/facade/boundary checks: 42 passed
Additional targeted domain regressions: 52 passed
Architecture guard findings: 0 across every guard category

The local runtime did not provide pytest, BeautifulSoup, Streamlit, or
ReportLab, so the normal grouped runners must be rerun in the full project
environment after applying the patch.

Four failures in tests/test_accommodation_stress_fixtures.py were reproduced
unchanged against the uploaded Git baseline and are not Batch 21 regressions.
```


---

# Batch 22: Scandinavian winter output fidelity

Progress: `[####################] 100%`

Completed in Batch 22:

```text
[x] Made cover date ranges follow itinerary day order and show years for cross-year trips
[x] Repaired destination-only flight routes by using the row city as the origin
[x] Added client-ready flight ticket and checked/carry-on baggage wording
[x] Preserved complete hotel bed configurations without duplicated room descriptors
[x] Suppressed placeholder activity meeting points and repaired common source typos
[x] Prevented unsupported Trollfjord and generic boat-title cruise claims
[x] Replaced unsuitable generic Arctic waterfront copy
[x] Removed sales-oriented optional-addition notes from the default client document
[x] Added focused Scandinavian winter output regressions
```

## Batch 23 — Maintainable Booknordics customer theme

- [x] Added explicit agent and Booknordics customer generation actions.
- [x] Kept one canonical itinerary/rendering pipeline; branding is selected through output state.
- [x] Added the Booknordics palette, DM Sans font contract, and supplied logo asset.
- [x] Applied customer branding consistently to preview and typed PDF output.
- [x] Added page-header logos from page 3 onward while leaving cover and summary pages clear.
- [x] Included output branding in render/cache state and customer PDF filenames.
- [x] Added focused brand-theme regressions and an official-source DM Sans installer.

---

# Batch 24 — Booknordics customer theme repair

Progress: `[####################] 100%`

Completed in Batch 24:

```text
[x] Made generated customer previews fully consume the Booknordics theme tokens, logo, DM Sans font faces, and red accent rules
[x] Made the visual editor receive a brand payload instead of relying on agent defaults
[x] Added Booknordics visual-editor CSS and local component font assets so the editable preview renders independently
[x] Prevented visual-editor brand metadata from being saved into editable drafts or PDF commit payloads
[x] Delayed Streamlit component height messages until after the first render event to avoid unsafe SessionInfo access during PDF creation
[x] Restored useful operational travel notes while keeping sales-oriented notes out of the default document
[x] Preserved the agent day-image divider color while using the Booknordics accent only for customer PDFs
[x] Replaced unsupported customer-PDF day-label star separators with PDF-safe hyphens
[x] Added focused regressions for Booknordics preview, visual-editor theming, safe component bridge behavior, notes, and PDF-safe labels
```

Validation snapshot:

```text
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Focused Booknordics/export/parity regressions: 46 passed
Architecture/facade/boundary guards: 44 passed
Import smoke: optional skips=25, failures=0
Rendered Booknordics sample PDF inspected after export: passed
git diff --check: passed
```

---

# Batch 25 — Booknordics preview/PDF parity and inclusion polish

Progress: `[####################] 100%`

Completed in Batch 25:

```text
[x] Fixed Booknordics cover and overview image fitting in generated preview and visual editor paths so selected images do not tile
[x] Reworked customer preview CSS so red remains a structural accent instead of over-colouring day-page sublabels
[x] Made the typed Booknordics PDF cover and overview consume the same customer palette, DM Sans styling, image-fit treatment, and logo rules as the preview
[x] Ensured the fallback HTML-to-PDF route configures the active output brand before rendering customer PDFs
[x] Added generated-inclusion-page ownership checks so stale saved final pages can refresh after renderer upgrades
[x] Rebalanced categorized inclusion pagination to avoid orphan transport pages and blank overflow pages in the Scandinavian winter itinerary
[x] Added explicit continued titles for multi-page final sections in preview and PDF contracts
[x] Added the independent-transfers travel note while preserving useful operational notes and excluding sales-oriented notes
[x] Normalized flight baggage wording consistently across day travel arrangements and final inclusions
[x] Preserved baggage “per person” wording in the client sanitizer while continuing to remove price-per-person language
[x] Normalized standalone hyphenated hour durations such as `3-hour` to `3 hours`
[x] Cached repeated cover/summary image crops during a PDF export to reduce duplicate image work
[x] Preserved the thin Nutshell compatibility hook expected by the architecture facade tests
[x] Added focused regressions for Booknordics image fitting, red-accent scope, inclusion pagination, travel notes, baggage wording, continuation headings, and duration display
```

Validation snapshot:

```text
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Focused Booknordics/output-brand/Scandinavian regressions: 22 passed
Adjacent PDF/editor/final-page/cache regressions: 21 passed
Architecture group stages 1-6 passed before runner timeout at stage 7
Architecture stages 7-11 rerun directly after the timeout: 139 passed
Architecture guards: passed
Import smoke: optional skips=25, failures=0
Rendered Booknordics Scandinavian sample PDF: 24 pages, 2 What’s included pages, no blank text pages
git diff --check: passed
```

---

# Batch 26 — Client-output baggage allowance gate hotfix

Progress: `[####################] 100%`

Completed in Batch 26:

```text
[x] Fixed the late client-output quality gate so legitimate flight baggage allowance wording with `per person` is not mistaken for leaked supplier pricing
[x] Kept price-like `per person` wording blocked, including currency amounts, standalone per-person prices, and baggage-fee wording
[x] Added focused regressions for the Booknordics baggage allowance wording that previously blocked generation
```

Validation snapshot:

```text
Focused baggage/client-sanitizer regressions: passed
Scandinavian Booknordics generation smoke: passed
```

---

# Batch 27 — Booknordics cover contrast and export speed polish

Progress: `[####################] 100%`

Completed in Batch 27:

```text
[x] Removed the Booknordics cover card from preview, visual editor, and typed PDF output
[x] Reused image-aware cover contrast so customer covers can use light text on dark image areas and navy/dark text on light image areas
[x] Aligned the Booknordics PDF cover rule and route stack with a single centered divider instead of the previous offset line treatment
[x] Kept the agent cover behavior unchanged while applying Booknordics cover-specific palette adjustments through a focused brand helper
[x] Reduced Add Pictures payload cost by limiting eager option-preview thumbnails and avoiding unnecessary thumbnail optimization work
[x] Added persistent PDF image-variant caching so repeated exports can reuse resized/cropped image files across export temp directories
[x] Added focused regressions for Booknordics cover contrast, no-card rendering, cover alignment source ownership, editor payload preview caps, and PDF image cache reuse
```

Validation snapshot:

```text
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Focused Booknordics cover/contrast/theme regressions: 21 passed
Adjacent editor/PDF/cache/parity regressions: 27 passed
Combined focused and adjacent regression set: 55 passed
Architecture guards: passed
Import smoke: optional skips=25, failures=0
Rendered Booknordics cover sample PDF inspected: no cover card, light text on dark image, centered accent divider
```

---

# Batch 28 — Shared image-bank fallback logic hotfix

Progress: `[####################] 100%`

Completed in Batch 28:

```text
[x] Restored one shared image-readiness path for agent and Booknordics customer itineraries
[x] Allowed Add Pictures and PDF export to proceed with bundled fallback images when no destination bank is available
[x] Kept missing full-bank and missing destination-pack states as warnings instead of brand-specific blockers
[x] Prevented stale blocking image-bank gateway state from stopping the workflow when fallback images are available
[x] Stopped Norway in a Nutshell route stops such as Myrdal and Gudvangen from becoming mandatory image-pack requests
[x] Preserved hard blocking only for the true no-image-source case
[x] Updated client-output image checks so fallback-image usage is reviewable rather than generation-blocking
[x] Added regressions for shared fallback readiness, stale gateway cleanup, route-stop request filtering, default fallback selection, and export readiness
```

Validation snapshot:

```text
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Focused image-bank/workflow/export regressions: 90 passed
Architecture guards: passed
Import smoke: optional skips=25, failures=0
git diff --check: passed
```

---

# Batch 29 — Single-pipeline export stability hotfix

Progress: `[####################] 100%`

Completed in Batch 29:

```text
[x] Removed the unbounded PDF export wait for a browser-side visual-editor commit acknowledgement
[x] Made Create PDF use the latest server-saved editor state directly so export cannot get stuck on “Applying pending editor changes…”
[x] Cleared stale legacy PDF commit requests when entering or rendering the export stage
[x] Kept Add Pictures/editor/save behavior shared across output brands while preventing PDF export from starting a brand-specific workflow
[x] Kept the two generation buttons on one shared generation pipeline; the selected output brand remains only presentation/theme state
[x] Updated export readiness, PDF preflight, and current-PDF reuse so stale commit state does not hide downloads or block creation
[x] Added regressions proving PDF export has no unbounded pending-editor wait and that agent/customer generation share one pipeline
```

Validation snapshot:

```text
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Focused export/readiness/document-flow regressions: 40 passed
Adjacent Booknordics/theme/image-fallback/workflow regressions: 37 passed
Visual editor/render-cache adjacent regressions: 53 passed
Booknordics cover/parity and Scandinavian quality regressions: 21 passed
Generation smoke for agent and Booknordics customer brands: passed
Architecture guards: passed
Import smoke: optional skips=25, failures=0
git diff --check: passed
```

---

# Batch 30 — Itinerary stability and fidelity repair

Progress: `[####################] 100%`

Completed in Batch 30:

```text
[x] Restored a bounded editor-save handshake for PDF export so the app saves current edits before export without an endless wait
[x] Added recoverable fallback actions for PDF export and Add Pictures when the browser editor acknowledgement does not arrive
[x] Forced generated day pages into canonical day-number order for preview/PDF contracts so Day 2 cannot be exported after later days
[x] Kept agent and Booknordics customer generation on the same pipeline; output brand remains presentation/theme state only
[x] Treated self-arranged accommodation as self-arranged/excluded instead of included accommodation, while preserving the source-stated night count and mismatch warning
[x] Removed stale generated exclusion artifacts such as bare accommodation headings and `self-arranged - date` activity-specific exclusions
[x] Prevented non-explicit scenic Flåm/Voss/Gudvangen/Myrdal routing from being rebranded as Norway in a Nutshell
[x] Repaired coastal-cruise transfer wording so self-arranged port transfers are not described as private transfers
[x] Added render-only overnight cruise arrival context on the following day so Bergen arrival is visible before the accommodation transfer
[x] Improved western Norway transport-day titles and Nærøyfjord route labels, including `Journey to Flåm via Gudvangen` and `Nærøyfjord Cruise from Gudvangen to Flåm`
[x] Preserved Borgund Stave Church in the Flåm activity title and restored day/final inclusion parity for Bergen boat-tour inclusions
[x] Restored PDF-safe Booknordics day-header separators using bullet separators instead of plain hyphens
[x] Made important travel notes context-aware so September western Norway itineraries do not show Northern Lights or winter-travel notes unless supported by the itinerary
[x] Reduced autosave churn in the editor to lower workflow disruption while preserving draft persistence
[x] Added regressions for canonical day order, self-arranged accommodation, route-branding restraint, cruise fidelity, activity inclusion parity, contextual notes, and bounded export commits
```

Validation snapshot:

```text
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Focused stability/fidelity/export/theme/workflow regressions: 64 passed
Adjacent PDF/editor/cache/transport/model regressions: 94 passed
Architecture guards: passed
Import smoke: optional skips=25, failures=0
Rendered Kristiansand Booknordics PDF sample: 16 pages, Day 1-10 in correct order, no Norway in a Nutshell leakage, no self-arranged exclusion artifact, contextual travel notes, cruise arrival present
git diff --check: passed
```

---

# Batch 31 — PDF export reliability and performance state-machine cleanup

Progress: `[####################] 100%`

Completed in Batch 31:

```text
[x] Added a small PDF export job state model so Create PDF has explicit idle, saving, exporting, ready, and failed states instead of implicit button/session side effects
[x] Split PDF editor-save coordination into a focused module with a bounded save request and recoverable fallback to the last saved itinerary
[x] Kept agent and Booknordics customer export on the same shared pipeline; the output brand remains presentation/theme state only
[x] Made the picture-stage Create PDF button hand off to the export page with a one-shot shared PDF job request instead of only changing stages
[x] Preserved existing PDF downloads while new saves or retries are pending so the user is not forced to restart the itinerary
[x] Added internal PDF export stage timing around validation, preview refresh, image preparation, render-context reuse, client-safety checks, PDF rendering, and byte storage
[x] Removed repeated image-bank storage-signature scans from the normal picture/export screen paths; cached image-bank status is now reused by request signature unless an explicit repair stores a new status
[x] Changed the visual editor save flow so dirty keys are not cleared merely because a browser message was sent; they clear only after the server-rendered payload acknowledges the saved values
[x] Added regressions for the export job lifecycle, bounded editor-save recovery, one-shot Create PDF handoff, image-bank scan avoidance, internal timing capture, and save acknowledgement behavior
```

Validation snapshot:

```text
Focused PDF export job/state-machine regressions: passed
Focused Canva-like export flow regressions: passed
Existing export readiness/download/fast-path regressions: passed
Visual editor autosave/save-contract regressions: passed
Adjacent workflow, Booknordics/theme, image fallback, and itinerary fidelity regressions: passed
Frontend JavaScript syntax validation: passed
```

---

# Batch 32 — Messy Finland input fidelity repair

Progress: `[####################] 100%`

Completed in Batch 32:

```text
[x] Treated supplier rows titled `Leisure Day` as leisure/free-time rows even when pasted under the Activity type
[x] Prevented Santa Claus Village optional husky/reindeer recommendations from becoming included product titles or day-intro copy
[x] Added explicit Santa Claus Village visit copy that stays focused on Santa’s Post Office, Arctic Circle crossing, and self-guided village time
[x] Stopped generic photo/fjord/coastal activity prose from applying to Rovaniemi Northern Lights BBQ products without source evidence
[x] Added Northern Lights BBQ description copy based on campfire/barbecue/light-pollution source evidence
[x] Improved route-transfer detection for explicit place-to-airport shuttle transfers such as Kakslauttanen to Ivalo Airport
[x] Titled final route-transfer days as transfer days and generated onward-journey intro copy from the actual origin and destination
[x] Preserved final shuttle transfers as included arranged transport while keeping local self transfers excluded
[x] Preserved messy hotel bed counts such as `2 Twin Beds and 1 Twin Sofa Bed` and `2x Single Bed, 1x Single Sofa Bed`
[x] Extracted explicit hotel amenities such as hotel-sauna access into accommodation day blocks and final inclusions
[x] Kept hotel date/night-count mismatch metadata available for review instead of silently dropping the conflict
[x] Added fallback-image scoring so overnight Lapland rail context can prefer winter/Lapland imagery over generic summer rail-track images
[x] Added focused regressions for messy Finland input fidelity, including leisure handling, Santa Village title restraint, Northern Lights BBQ copy, final transfer endpoint/title, hotel fidelity, and winter rail image selection
```

Validation snapshot:

```text
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Focused messy-input fidelity regressions: 6 passed
Focused and adjacent itinerary/image/accommodation/export/theme regressions: 66 passed
Architecture guards: passed
Import smoke: optional skips=25, failures=0
git diff --check: passed
```

---

# Batch 33: Image-edit and PDF-export stability cleanup

Progress: `[####################] 100%`

Goal:

```text
Make picture changes and PDF creation feel stable by removing full-editor image redraws, avoiding heavy browser-local image payloads, and eliminating the legacy PDF browser-commit wait path.
```

Completed in Batch 33:

```text
[x] Reworked visual-editor image changes to refresh only the affected image surface instead of redrawing the full document
[x] Removed full document collect/draw calls from day and cover image replacement actions
[x] Added small in-place image upload compression before storing visual-editor uploads in the browser model
[x] Kept uploaded binary data out of browser-local recovery drafts while preserving it for server autosave/save payloads
[x] Forced short debounced server autosave for image-only changes so PDF export has a fresher server-owned state
[x] Increased replacement-option previews so all shown day-image choices can preview immediately
[x] Removed active PDF export dependency on the visual-editor browser commit handshake
[x] Converted the old PDF editor-save module into no-wait compatibility helpers
[x] Reused cached picture-stage image matches during PDF image-contract preparation when valid
[x] Added regression tests for no-wait export and image-edit hot-path stability
```
---

# Batch 34: Editor image/save workflow recovery

Progress: `[####################] 100%`

Goal:

```text
Recover from the Batch 33 image-edit regression by keeping normal editor edits local and non-blocking, making manual Save a compact sync, and deferring heavy preview/PDF refresh work to explicit workflow boundaries.
```

Completed in Batch 34:

```text
[x] Stopped normal image replacement/crop/upload actions from scheduling forced server autosave or Streamlit component commits
[x] Changed normal edit dirty-state handling to save browser recovery drafts locally without triggering automatic Streamlit reruns
[x] Debounced browser-local draft persistence so typing/image changes do not rewrite the full recovery snapshot on every single interaction
[x] Changed recovered browser drafts to wait for explicit Save instead of immediately sending a server payload on component render
[x] Added a touched-field collection path so normal Save only reads changed editor fields instead of collecting the whole document
[x] Kept full visible-model collection for hard commit boundaries such as Apply Changes / legacy commit nonce flows
[x] Removed synchronous preview/render-context rebuild from normal editor Save; Add Pictures and PDF export remain the explicit refresh boundaries
[x] Updated editor messaging and regression tests so picture edits and normal saves stay local/non-blocking until the user chooses to sync
```

---

# Batch 35: PDF image sync, export speed and legacy cleanup

Progress: `[####################] 100%`

Goal:

```text
Make PDF creation a reliable hard sync boundary for picture edits, speed up the first typed PDF export, clean up inclusion pagination/title policy, and remove obsolete PDF editor-save compatibility code.
```

Completed in Batch 35:

```text
[x] Changed Create PDF from picture review to first request one full visible-editor commit, so image removals, replacements, uploads and crop focus are saved before PDF creation
[x] Kept normal image editing local/non-blocking while making PDF export the explicit server-sync boundary
[x] Prevented stale picture-stage `day_image_matches` from overriding committed manual/none image choices during PDF image-contract preparation
[x] Added typed-PDF day-image pre-warming so deterministic crop/resize variants are built before ReportLab `doc.build`
[x] Kept repeated inclusion/final-page titles clean without client-visible `continued` wording
[x] Relaxed compact inclusion pagination only for plain single-line entries and short transport clusters
[x] Moved image-bank setup JSON/details behind explicit debug mode
[x] Deleted obsolete no-wait legacy PDF editor-save/commit compatibility modules
[x] Updated export/image/inclusion regressions for the new sync boundary and clean final-page title policy
```

---

# Batch 36: Transport route facts repair

Progress: `[####################] 100%`

Goal:

```text
Fix route-origin pollution and establish one canonical route-facts path for transport titles, day travel lines and final inclusions.
```

Completed in Batch 36:

```text
[x] Added TransportRouteFacts as the canonical route-facts wrapper for transport rows
[x] Routed transport phrase generation and transport summaries through the shared route-facts path
[x] Stripped supplier product/mode wording from route origins such as Domestic flight from Bergen, Overnight coastal cruise from Bergen, Eurostar train London and Night train Stockholm
[x] Preserved via points, route destinations and transport mode facts for titles/rendering/inclusions
[x] Fixed checked-bag detail wording so included flight baggage renders as checked luggage
[x] Added regression coverage for polluted transport origins and explicit route facts
```

Validation snapshot:

```text
Focused transport route/inclusion regressions: passed
Adjacent transport, cruise, rail, Finland and messy-input regressions: passed
Fast validation targets excluding documented pre-existing expectation failures: passed
Architecture validation targets excluding documented pre-existing source-contract failure: passed
Full Python compilation: passed
Frontend JavaScript syntax validation: passed
Architecture guards: passed
Import smoke: optional skips=24, failures=0
git diff --check: passed
```

Pre-existing failures observed in the uploaded baseline and still unresolved:

```text
[x] tests/test_patch_k_transport_preview_quality.py::test_nutshell_timetable_route_uses_premium_no_arrow_format
[x] tests/test_transport_render_split.py::test_nutshell_domain_and_parsing_do_not_import_transport_facade_or_each_other
[x] tests/test_nordic_quality_sample.py::test_nordic_quality_sample_matches_key_quality_target_markers
```
