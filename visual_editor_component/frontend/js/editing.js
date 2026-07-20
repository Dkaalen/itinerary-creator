function updateAutosaveNote(message) {
  const note = document.getElementById('savedNote');
  if (!note) return;
  note.textContent = message;
  note.classList.add('show');
}
function safeSendComponentValue(serialized, stateName = 'saving') {
  captureEditorScrollState(stateName);
  try {
    if (!Streamlit.setComponentValue(serialized)) throw new Error('Editor component session is not ready.');
    return true;
  } catch (err) {
    persistLocalDraft({fullSnapshot: true});
    updateSaveState('failed', {
      error: `Could not send save to app: ${err?.message || err || 'unknown error'}`,
      lastAttemptAt: Date.now()
    });
    return false;
  }
}

function sendServerAutosaveNow(force = false) {
  if (!model || serverAutosaveInFlight) return;
  if (!touchedKeys.size && !restoredLocalDraftPendingSave) return;
  const now = Date.now();
  if (!force && now - lastServerAutosaveAt < SERVER_AUTOSAVE_MIN_INTERVAL_MS) {
    scheduleServerAutosave(SERVER_AUTOSAVE_MIN_INTERVAL_MS);
    return;
  }
  if (!force && editorIsActivelyInUse(now)) {
    scheduleServerAutosave(AUTOSAVE_IDLE_GRACE_MS);
    return;
  }
  const serialized = buildServerAutosaveEnvelope();
  if (serialized === lastServerAutosavePayload) return;
  serverAutosaveInFlight = true;
  lastServerAutosaveAt = now;
  lastServerAutosavePayload = serialized;
  persistLocalDraft();
  updateSaveState('autosaving', {message: 'Autosaving…', lastAttemptAt: now, error: ''});
  safeSendComponentValue(serialized, 'autosaving');
  setTimeout(() => { serverAutosaveInFlight = false; }, 4000);
  setTimeout(() => {
    if (saveState.state === 'autosaving' && saveState.lastAttemptAt === now) {
      updateSaveState('local_draft', {message: 'Autosave sent; local recovery kept'});
    }
  }, SAVE_STATUS_STALE_MS);
}

function scheduleServerAutosave(delayMs = SERVER_AUTOSAVE_DELAY_MS, force = false) {
  if (serverAutosaveTimer) clearTimeout(serverAutosaveTimer);
  serverAutosaveTimer = setTimeout(() => {
    serverAutosaveTimer = null;
    sendServerAutosaveNow(force);
  }, delayMs);
}

function saveRestoredLocalDraftToServer() {
  if (!restoredLocalDraftPendingSave) return;
  restoredLocalDraftPendingSave = false;
  collect();
  const payload = compactFullPayloadForCommit(model);
  payload.draft_id = model.draft_id || '';
  payload.meta = model.meta || {};
  payload.workflow = model.workflow || {};
  payload.save_mode = 'recovered_full';
  const serialized = JSON.stringify({autosave: true, recovered: true, payload});
  if (serialized === lastSavedPayload) return;
  lastSavedPayload = serialized;
  lastServerAutosavePayload = serialized;
  lastServerAutosaveAt = Date.now();
  persistLocalDraft({fullSnapshot: true});
  if (safeSendComponentValue(serialized, 'recovered')) {
    updateSaveState('recovered', {message: 'Recovered browser draft synced', lastAttemptAt: Date.now(), recovered: true});
  }
  updateEditorStats();
}

function saveChanges(commitNonce = null) {
  if (serverAutosaveTimer) { clearTimeout(serverAutosaveTimer); serverAutosaveTimer = null; }
  if (restoredLocalDraftPendingSave && !commitNonce && !touchedKeys.size) {
    saveRestoredLocalDraftToServer();
    return true;
  }
  if (!touchedKeys.size && !commitNonce) return false;
  const serialized = buildSaveEnvelope(commitNonce);
  if (!commitNonce && serialized === lastSavedPayload) return false;
  lastSavedPayload = serialized;
  lastServerAutosavePayload = serialized;
  pendingServerSaveKeys = new Set(touchedKeys);
  pendingServerSavePayload = serialized;
  persistLocalDraft({fullSnapshot: true});
  updateSaveState(commitNonce ? 'exporting' : 'saving', {message: commitNonce ? 'Applying changes…' : 'Saving…', lastAttemptAt: Date.now(), error: ''});
  if (!safeSendComponentValue(serialized, commitNonce ? 'exporting' : 'saving')) return false;
  if (!pendingServerSaveKeys.size) {
    updateSaveState('saved', {message: commitNonce ? 'Changes applied' : 'Saved', lastSavedAt: Date.now(), error: ''});
  } else {
    updateSaveState(commitNonce ? 'exporting' : 'saving', {message: commitNonce ? 'Applying changes…' : 'Save sent', lastAttemptAt: Date.now(), error: ''});
  }
  updateEditorStats();
  return true;
}

function attachHandlers() {
  const stack = pageStackElement();
  stack?.addEventListener('scroll', noteEditorInteraction, {passive: true});
  document.querySelector('.editor-shell')?.addEventListener('pointerdown', noteEditorInteraction, {passive: true});
  document.querySelector('.editor-shell')?.addEventListener('keydown', noteEditorInteraction, {passive: true});
  document.querySelector('.editor-shell')?.addEventListener('input', noteEditorInteraction, {passive: true});
  document.getElementById('saveBtn').addEventListener('click', () => saveChanges());
  document.getElementById('undoBtn')?.addEventListener('click', undoLastEdit);
  document.getElementById('resetBlockBtn')?.addEventListener('click', resetSelectedBlock);
  document.getElementById('replaceBtn')?.addEventListener('click', replaceAllText);
  document.getElementById('flagIssueBtn')?.addEventListener('click', flagSelectedIssue);

  document.getElementById('resetBtn')?.addEventListener('click', () => {
    allowNextDrawToResetScroll();
    clearLocalDraft();
    model = JSON.parse(JSON.stringify(initialPayload));
    uploadedImages = {};
    touchedKeys = new Set();
    updateSaveState('ready', {message: 'Draft reset', error: '', recovered: false});
    draw();
  });
  attachPageEventHandlers();
  attachInspectorHandlers();
  document.querySelectorAll('[contenteditable="true"]').forEach(el => {
    const key = el.getAttribute('data-edit-key');
    el.dataset.lastValue = editableValue(el);
    el.addEventListener('focus', () => {
      activeEditKey = key;
      selectEditorBlockFromElement(el);
      el.dataset.lastValue = editableValue(el);
      rememberCanvasSelection();
    });
    el.addEventListener('mouseup', rememberCanvasSelection);
    el.addEventListener('keyup', rememberCanvasSelection);
    el.addEventListener('paste', insertCleanClipboardHtml);
    el.addEventListener('input', () => {
      const previous = el.dataset.lastValue || '';
      const current = editableValue(el);
      if (previous !== current) {
        pushUndo(el, previous);
        el.dataset.lastValue = current;
      }
      markTouched(key);
      activeFieldKey = key;
      rememberCanvasSelection();
      requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); updateEditorStats(); });
    });
  });
  updateEditorStats();
  updateSelectionUi();

  attachImageEventHandlers();
}
window.addEventListener('beforeunload', () => {
  if (touchedKeys.size) {
    collect();
    persistLocalDraft({fullSnapshot: true});
  }
});
