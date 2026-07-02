import json
import subprocess
from pathlib import Path


FRONTEND = Path("visual_editor_component/frontend/js")


def _run_node(script: str) -> None:
    subprocess.run(["node", "-e", script], cwd=Path.cwd(), check=True)


def test_pdf_commit_sends_tiny_noop_when_editor_has_no_changes():
    script = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const fields = [
  {key: 'cover.trip_title', value: 'Nordic Trip'},
  {key: 'days.0.title', value: 'Oslo arrival'},
  {key: 'days.0.intro', value: 'Welcome to Oslo'},
];
const context = {
  console,
  document: {
    querySelectorAll: selector => selector === '[data-edit-key]' ? fields.map(field => ({
      getAttribute: name => name === 'data-edit-key' ? field.key : '',
      innerHTML: field.value,
      textContent: field.value,
      value: field.value,
    })) : [],
    querySelector: () => null,
  },
  CSS: {escape: value => String(value)},
  uploadedImages: {},
  JSON,
};
context.cssEscapeValue = value => String(value);
context.editableValue = el => el.value;
vm.createContext(context);
vm.runInContext(fs.readFileSync('visual_editor_component/frontend/js/serialization.js', 'utf8'), context);
context.model = {
  meta: {source_signature: 'sig-fast'},
  workflow: {pictures_added: true},
  brand: {large: 'must not be sent'},
  cover: {trip_title: 'Nordic Trip'},
  summary: {},
  days: [{day: 'Day 1', title: 'Oslo arrival', intro: 'Welcome to Oslo', image: {data_uri: 'data:image/png;base64,heavy'}}],
  final_pages: {},
  document_pages: [{page_id: 'cover'}, {page_id: 'day-1'}],
};
context.touchedKeys = new Set();
const envelope = JSON.parse(context.buildSaveEnvelope('pdf-1'));
assert.equal(envelope.commit_nonce, 'pdf-1');
assert.equal(envelope.payload.save_mode, 'commit_noop');
assert.deepEqual(envelope.payload.days, []);
assert.equal(envelope.payload.editor_draft, undefined);
assert.equal(JSON.stringify(envelope).includes('data:image/png;base64,heavy'), false);
assert.equal(envelope.payload.document_pages, undefined);
"""
    _run_node(script)


def test_pdf_commit_scans_visible_dom_and_sends_only_changed_delta():
    script = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const fields = [
  {key: 'cover.trip_title', value: 'Nordic Trip'},
  {key: 'days.0.title', value: 'Edited Oslo arrival'},
  {key: 'days.0.intro', value: 'Welcome to Oslo'},
];
const context = {
  console,
  document: {
    querySelectorAll: selector => selector === '[data-edit-key]' ? fields.map(field => ({
      getAttribute: name => name === 'data-edit-key' ? field.key : '',
      innerHTML: field.value,
      textContent: field.value,
      value: field.value,
    })) : [],
    querySelector: () => null,
  },
  CSS: {escape: value => String(value)},
  uploadedImages: {},
  JSON,
};
context.cssEscapeValue = value => String(value);
context.editableValue = el => el.value;
vm.createContext(context);
vm.runInContext(fs.readFileSync('visual_editor_component/frontend/js/serialization.js', 'utf8'), context);
context.model = {
  meta: {source_signature: 'sig-fast'},
  workflow: {pictures_added: true},
  cover: {trip_title: 'Nordic Trip'},
  summary: {},
  days: [
    {day: 'Day 1', title: 'Oslo arrival', intro: 'Welcome to Oslo', image: {data_uri: 'data:image/png;base64,heavy'}},
    {day: 'Day 2', title: 'Bergen', intro: 'Untouched Bergen'}
  ],
  final_pages: {},
  document_pages: [{page_id: 'cover'}, {page_id: 'day-1'}, {page_id: 'day-2'}],
};
context.touchedKeys = new Set();
const envelope = JSON.parse(context.buildSaveEnvelope('pdf-2'));
assert.equal(envelope.payload.save_mode, 'commit_delta');
assert.equal(envelope.payload.days.length, 1);
assert.equal(envelope.payload.days[0].day, 'Day 1');
assert.equal(envelope.payload.days[0].title, 'Edited Oslo arrival');
assert.equal(envelope.payload.days[0].intro, undefined);
assert.equal(JSON.stringify(envelope).includes('Untouched Bergen'), false);
assert.equal(JSON.stringify(envelope).includes('data:image/png;base64,heavy'), false);
assert.equal(envelope.payload.document_pages, undefined);
"""
    _run_node(script)


def test_pdf_commit_keeps_pending_image_changes_as_delta():
    script = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const context = {
  console,
  document: {querySelectorAll: () => [], querySelector: () => null},
  CSS: {escape: value => String(value)},
  uploadedImages: {},
  JSON,
};
context.cssEscapeValue = value => String(value);
context.editableValue = el => el.value || '';
vm.createContext(context);
vm.runInContext(fs.readFileSync('visual_editor_component/frontend/js/serialization.js', 'utf8'), context);
context.model = {
  meta: {source_signature: 'sig-fast'},
  workflow: {pictures_added: true},
  cover: {},
  summary: {},
  days: [{day: 'Day 1', title: 'Oslo', image: {mode: 'auto', crop_focus: 'top', data_uri: 'data:image/png;base64,heavy'}}],
  final_pages: {},
  document_pages: [],
};
context.touchedKeys = new Set(['days.0.image']);
context.model.days[0].image.crop_focus = 'center';
const envelope = JSON.parse(context.buildSaveEnvelope('pdf-3'));
assert.equal(envelope.payload.save_mode, 'commit_delta');
assert.equal(envelope.payload.days.length, 1);
assert.equal(envelope.payload.days[0].image.crop_focus, 'center');
assert.equal(envelope.payload.days[0].image.data_uri, undefined);
assert.equal(JSON.stringify(envelope).includes('data:image/png;base64,heavy'), false);
"""
    _run_node(script)


def test_hard_commit_rerun_uses_tiny_frontend_signal_payload():
    from visual_editor_component.editor_commit_signal import build_editor_commit_signal_payload

    payload = build_editor_commit_signal_payload("sig-fast")

    assert payload["workflow"] == {"commit_signal_only": True}
    assert payload["meta"]["source_signature"] == "sig-fast"
    assert payload["days"] == []
    assert payload["document_pages"] == []
    assert "brand" not in payload

    workflow_source = Path("visual_editor_component/editor_workflow.py").read_text(encoding="utf-8")
    render_source = Path("visual_editor_component/frontend/js/render.js").read_text(encoding="utf-8")
    assert "build_editor_commit_signal_payload" in workflow_source
    assert "if (commitSignalOnly) return;" in render_source
