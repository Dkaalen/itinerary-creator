import json
import shutil
import subprocess
from pathlib import Path


FRONTEND = Path("visual_editor_component/frontend")


def _read_js(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_frequent_local_draft_uses_delta_not_full_commit_snapshot():
    local_draft = _read_js("js/editor_local_draft.js")
    dirty_state = _read_js("js/editor_dirty_state.js")
    editing = _read_js("js/editing.js")

    assert "const snapshot = buildLocalDraftPayload(options);" in local_draft
    assert "function buildLocalDraftDeltaPayload" in local_draft
    assert "const payload = stripUploadBinaryForLocalDraft(pruneForSave(model));" in local_draft
    assert "const payload = stripUploadBinaryForLocalDraft(compactFullPayloadForCommit(model));" in local_draft
    assert "scheduleLocalDraftPersist();" in dirty_state
    assert "persistLocalDraft({fullSnapshot: true});" in editing

    persist_body = local_draft.split("function persistLocalDraft", 1)[1].split("function scheduleLocalDraftPersist", 1)[0]
    assert "compactFullPayloadForCommit(model)" not in persist_body
    assert "!options?.fullSnapshot && (!touchedKeys || !touchedKeys.size)" in persist_body
    assert "stableStoragePayload === lastLocalDraftStoragePayload" in persist_body


def test_hard_boundaries_keep_full_browser_recovery_snapshots():
    editing = _read_js("js/editing.js")

    assert "persistLocalDraft({fullSnapshot: true});" in editing
    assert "safeSendComponentValue" in editing
    assert "saveRestoredLocalDraftToServer" in editing
    assert "window.addEventListener('beforeunload'" in editing
    assert "const serialized = buildSaveEnvelope(commitNonce);" in editing

    autosave_block = editing.split("function sendServerAutosaveNow", 1)[1].split("function scheduleServerAutosave", 1)[0]
    assert "persistLocalDraft();" in autosave_block
    assert "persistLocalDraft({fullSnapshot: true});" not in autosave_block


def test_pruned_delta_omits_document_pages_until_page_structure_changes():
    serialization = _read_js("js/serialization.js")

    assert "documentPagesTouched" in serialization
    assert "key === 'document_pages' || String(key || '').startsWith('document_pages.')" in serialization

    prune_body = serialization.split("function pruneForSave", 1)[1].split("function compactFullPayloadForCommit", 1)[0]
    assert "payload.document_pages" in prune_body
    assert "if (documentPagesTouched)" in prune_body


def test_delta_recovery_preserves_untouched_days_and_final_inclusions():
    if not shutil.which("node"):
        raise AssertionError("node is required for local draft frontend recovery contract validation")

    script = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const context = {
  console,
  document: {
    querySelectorAll: () => [],
    querySelector: () => null
  },
  CSS: {escape: value => String(value)},
  localStorage: {setItem(){}, getItem(){return null;}, removeItem(){}},
  saveState: {},
  uploadedImages: {},
  localDraftTimer: null,
  updateSaveState: () => {},
  clearTimeout,
  setTimeout,
  Date,
  JSON,
};
context.cssEscapeValue = value => String(value);
context.ItineraryVisualEditor = {define: () => {}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('visual_editor_component/frontend/js/serialization.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('visual_editor_component/frontend/js/editor_local_draft.js', 'utf8'), context);

const initial = {
  draft_id: 'draft-38',
  meta: {source_signature: 'sig-38', draft_schema_version: 3},
  workflow: {pictures_added: false},
  cover: {trip_title: 'Nordic Trip'},
  summary: {trip_glance_title: 'Glance'},
  days: [
    {day: 'Day 1', title: 'Oslo arrival', intro: 'Generated Oslo intro', blocks_html: '<p>Oslo leisure time</p>'},
    {day: 'Day 2', title: 'Bergen Railway', intro: 'Generated Bergen intro', blocks_html: '<p>Bergen rail details</p>'},
    {day: 'Day 3', title: 'Fjord cruise', intro: 'Generated fjord intro', blocks_html: '<p>Fjord details</p>'}
  ],
  final_pages: {
    whats_included_title: 'What’s included',
    whats_included_pages_html: [{html: '<div>Flights</div>'}, {html: '<div>Hotels</div>'}],
    whats_not_included_html: '<div>Meals</div>',
    important_travel_notes_text: 'Bring passport'
  },
  document_pages: []
};
context.initialPayload = JSON.parse(JSON.stringify(initial));
context.model = JSON.parse(JSON.stringify(initial));
context.touchedKeys = new Set(['days.1.title']);
context.model.days[1].title = 'Edited Bergen Railway';

const delta = context.buildLocalDraftPayload();
assert.equal(delta.save_mode, 'local_delta');
assert.deepEqual(delta.local_draft_touched_keys, ['days.1.title']);
assert.equal(delta.days.length, 1);
assert.equal(delta.days[0].day, 'Day 2');
assert.equal(delta.days[0].title, 'Edited Bergen Railway');
assert.equal(JSON.stringify(delta).includes('Generated Oslo intro'), false);
assert.equal(JSON.stringify(delta).includes('Generated fjord intro'), false);
assert.equal(Array.isArray(delta.document_pages), false);

const merged = context.mergeLocalDraftOntoServerPayload(delta);
assert.equal(merged.days.length, 3);
assert.equal(merged.days[0].intro, 'Generated Oslo intro');
assert.equal(merged.days[1].title, 'Edited Bergen Railway');
assert.equal(merged.days[2].blocks_html, '<p>Fjord details</p>');
assert.equal(merged.final_pages.whats_included_pages_html.length, 2);
assert.equal(merged.final_pages.whats_included_pages_html[1].html, '<div>Hotels</div>');
assert.equal(merged.final_pages.important_travel_notes_text, 'Bring passport');
assert.equal(merged.editor_draft.days.length, 3);
assert.equal(merged.editor_draft.final_sections.find(section => section.section_id === 'whats_included').pages.length, 2);
"""
    subprocess.run(["node", "-e", script], cwd=Path.cwd(), check=True)


def test_picture_stage_local_draft_cannot_restore_scattered_generated_day_order():
    if not shutil.which("node"):
        raise AssertionError("node is required for picture-stage draft order validation")

    script = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const days = Array.from({length: 10}, (_, index) => ({day: `Day ${index + 1}`, title: `Title ${index + 1}`}));
const scattered = ['day-day-1', 'day-day-2', 'day-day-4', 'day-day-5', 'day-day-3', 'day-day-6', 'day-day-7', 'day-day-9', 'day-day-8', 'day-day-10'];
const context = {
  console,
  document: {
    querySelectorAll: () => [],
    querySelector: () => null
  },
  CSS: {escape: value => String(value)},
  localStorage: {setItem(){}, getItem(){return null;}, removeItem(){}},
  saveState: {},
  uploadedImages: {},
  localDraftTimer: null,
  updateSaveState: () => {},
  clearTimeout,
  setTimeout,
  Date,
  JSON,
};
context.cssEscapeValue = value => String(value);
context.ItineraryVisualEditor = {define: () => {}};
vm.createContext(context);
[
  'visual_editor_component/frontend/js/editor_html_utils.js',
  'visual_editor_component/frontend/js/editor_pages_model.js',
  'visual_editor_component/frontend/js/serialization.js',
  'visual_editor_component/frontend/js/editor_local_draft.js',
].forEach(file => vm.runInContext(fs.readFileSync(file, 'utf8'), context, {filename: file}));

const initial = {
  draft_id: 'picture-order-draft',
  meta: {source_signature: 'picture-order-sig', draft_schema_version: 3},
  workflow: {pictures_added: true},
  cover: {trip_title: 'Nordic Trip'},
  summary: {trip_glance_title: 'Glance'},
  days,
  final_pages: {important_travel_notes_text: 'Bring passport'},
  document_pages: [
    {page_id: 'cover', page_type: 'cover', title: 'Cover', sort_order: 1, is_hidden: false},
    {page_id: 'summary', page_type: 'summary', title: 'Summary', sort_order: 2, is_hidden: false},
    ...days.map((day, index) => ({page_id: `day-day-${index + 1}`, page_type: 'generated_day', source_day_id: day.day, title: day.day, sort_order: index + 3, is_hidden: false, page_actions: {move: false}})),
    {page_id: 'final-important-travel-notes', page_type: 'final_section', title: 'Notes', sort_order: 13, is_hidden: false},
  ],
};
const localDraft = {
  save_mode: 'local_snapshot',
  workflow: {pictures_added: true},
  days,
  document_pages: [
    {page_id: 'cover', page_type: 'cover', title: 'Cover', sort_order: 1, is_hidden: false},
    {page_id: 'summary', page_type: 'summary', title: 'Summary', sort_order: 2, is_hidden: false},
    ...scattered.map((pageId, index) => ({page_id: pageId, page_type: 'generated_day', source_day_id: pageId.replace('day-day-', 'Day '), title: pageId, sort_order: index + 3, is_hidden: false, page_actions: {move: true}})),
    {page_id: 'final-important-travel-notes', page_type: 'final_section', title: 'Notes', sort_order: 13, is_hidden: false},
  ],
};
context.initialPayload = JSON.parse(JSON.stringify(initial));
context.model = JSON.parse(JSON.stringify(initial));
context.touchedKeys = new Set();

const merged = context.mergeLocalDraftOntoServerPayload(localDraft);
const generated = merged.document_pages.filter(page => page.page_type === 'generated_day');
assert.deepEqual(generated.map(page => page.page_id), Array.from({length: 10}, (_, index) => `day-day-${index + 1}`));
assert.deepEqual(generated.map(page => page.sort_order), Array.from({length: 10}, (_, index) => index + 3));
assert.equal(generated.find(page => page.page_id === 'day-day-3').page_actions.move, false);
assert.equal(merged.workflow.pictures_added, true);
"""
    subprocess.run(["node", "-e", script], cwd=Path.cwd(), check=True)
