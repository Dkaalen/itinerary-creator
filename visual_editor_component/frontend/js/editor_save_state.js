/** Responsibility split from state.js. */
function humanTime(value) {
  if (!value) return '';
  try {
    const date = typeof value === 'number' ? new Date(value) : new Date(String(value));
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
  } catch (err) { return ''; }
}

function saveStatusLabel() {
  if (saveState.state === 'dirty') return 'Unsaved edits';
  if (saveState.state === 'saving') return 'Saving…';
  if (saveState.state === 'autosaving') return 'Autosaving…';
  if (saveState.state === 'recovered') return 'Recovered draft';
  if (saveState.state === 'local_draft') return 'Saved locally';
  if (saveState.state === 'failed') return 'Save needs attention';
  if (saveState.state === 'exporting') return 'Applying changes…';
  if (saveState.lastSavedAt) return `Saved ${humanTime(saveState.lastSavedAt)}`;
  if (saveState.serverSavedAt) return `Server saved ${humanTime(saveState.serverSavedAt)}`;
  return saveState.message || 'Ready';
}

function saveStatusDetail() {
  if (saveState.error) return saveState.error;
  if (saveState.state === 'dirty' && saveState.localRecoveryAvailable === false) {
    return saveState.message || 'Browser recovery is paused. Use Save changes to sync your work.';
  }
  if (saveState.state === 'dirty') return 'Browser recovery draft is saved locally. Use Save changes when you want to sync to the app.';
  if (saveState.state === 'saving' || saveState.state === 'autosaving') return 'Sending a compact editor delta to the app.';
  if (saveState.state === 'recovered') return 'A matching browser draft was restored and can be synced with Save changes.';
  if (saveState.state === 'local_draft') return 'The browser has a local recovery copy. Use Save changes before leaving this project.';
  if (saveState.state === 'failed') return 'Your local recovery draft is still kept in this browser.';
  if (saveState.serverOk === false) return saveState.serverReason || 'Last server autosave was rejected.';
  const savedAt = humanTime(saveState.lastSavedAt || saveState.serverSavedAt || saveState.localDraftAt);
  return savedAt ? `Last recovery snapshot: ${savedAt}` : 'Local recovery is ready.';
}

function noteEditorInteraction() {
  lastEditorInteractionAt = Date.now();
}

function editorIsActivelyInUse(now = Date.now()) {
  return now - lastEditorInteractionAt < AUTOSAVE_IDLE_GRACE_MS;
}

function updateSaveState(state, extras = {}) {
  saveState = Object.assign({}, saveState, extras, {state});
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = saveStatusLabel();
    note.className = `saved-note show ${state}`;
  }
  updateSaveStatusUi();
}

function updateSaveStatusUi() {
  const label = document.getElementById('saveStatusLabel');
  if (label) label.textContent = saveStatusLabel();
  const detail = document.getElementById('saveStatusDetail');
  if (detail) detail.textContent = saveStatusDetail();
  const card = document.getElementById('saveRecoveryCard');
  if (card) card.className = `save-recovery-card ${saveState.state}`;
  const server = document.getElementById('saveServerStatus');
  if (server) {
    const ok = saveState.serverOk;
    server.textContent = ok === false ? `Server issue: ${saveState.serverReason || 'check autosave'}` : (saveState.serverSavedAt ? `Server saved ${humanTime(saveState.serverSavedAt)}` : '');
  }
}


function normalizeSavedValue(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value.replace(/\s+/g, ' ').trim();
  try { return JSON.stringify(value); } catch (err) { return String(value); }
}

function serverPayloadContainsPendingSave(payload) {
  if (!pendingServerSaveKeys.size || !model || typeof getByPath !== 'function') return false;
  for (const key of pendingServerSaveKeys) {
    const serverValue = normalizeSavedValue(getByPath(payload, key));
    const localValue = normalizeSavedValue(getByPath(model, key));
    if (serverValue !== localValue) return false;
  }
  return true;
}

function acknowledgeServerSaveFromPayload(payload) {
  if (!serverPayloadContainsPendingSave(payload)) return false;
  pendingServerSaveKeys.forEach(key => touchedKeys.delete(key));
  pendingServerSaveKeys = new Set();
  pendingServerSavePayload = '';
  if (!touchedKeys.size) {
    updateSaveState('saved', {message: 'Saved', lastSavedAt: Date.now(), error: ''});
  }
  return true;
}

function hydrateSaveStateFromPayload(payload) {
  const status = payload?.autosave_status || {};
  if (!status || typeof status !== 'object') return;
  saveState.serverSavedAt = status.saved_at || saveState.serverSavedAt || '';
  saveState.serverOk = Object.prototype.hasOwnProperty.call(status, 'ok') ? !!status.ok : saveState.serverOk;
  saveState.serverReason = status.reason || '';
  if (status.recovered) {
    saveState.recovered = true;
    saveState.state = 'recovered';
    saveState.message = 'Recovered server draft';
  } else if (status.ok && status.saved_at) {
    saveState.state = 'saved';
    saveState.lastSavedAt = Date.now();
    saveState.message = 'Autosaved';
  } else if (status.ok === false) {
    saveState.state = 'failed';
    saveState.error = status.reason || 'Server autosave failed';
  }
}
