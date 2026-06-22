function updateAutosaveNote(message) {
  const note = document.getElementById('savedNote');
  if (!note) return;
  note.textContent = message;
  note.classList.add('show');
}

function sendServerAutosaveNow() {
  if (!model || serverAutosaveInFlight) return;
  if (!touchedKeys.size && !restoredLocalDraftPendingSave) return;
  const now = Date.now();
  if (now - lastServerAutosaveAt < SERVER_AUTOSAVE_MIN_INTERVAL_MS) {
    scheduleServerAutosave(SERVER_AUTOSAVE_MIN_INTERVAL_MS);
    return;
  }
  const serialized = buildServerAutosaveEnvelope();
  if (serialized === lastServerAutosavePayload) return;
  serverAutosaveInFlight = true;
  lastServerAutosaveAt = now;
  lastServerAutosavePayload = serialized;
  persistLocalDraft();
  updateAutosaveNote('Autosaving…');
  Streamlit.setComponentValue(serialized);
  setTimeout(() => { serverAutosaveInFlight = false; }, 4000);
}

function scheduleServerAutosave(delayMs = SERVER_AUTOSAVE_DELAY_MS) {
  if (serverAutosaveTimer) clearTimeout(serverAutosaveTimer);
  serverAutosaveTimer = setTimeout(() => {
    serverAutosaveTimer = null;
    sendServerAutosaveNow();
  }, delayMs);
}

function saveRestoredLocalDraftToServer() {
  if (!restoredLocalDraftPendingSave) return;
  restoredLocalDraftPendingSave = false;
  collect();
  const serialized = buildServerAutosaveEnvelope();
  if (serialized === lastSavedPayload) return;
  lastSavedPayload = serialized;
  lastServerAutosavePayload = serialized;
  lastServerAutosaveAt = Date.now();
  persistLocalDraft();
  Streamlit.setComponentValue(serialized);
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = 'Recovered browser draft and saved it';
    note.classList.add('show');
    setTimeout(() => note.classList.remove('show'), 2200);
  }
  updateEditorStats();
}

function saveChanges(commitNonce = null) {
  if (serverAutosaveTimer) { clearTimeout(serverAutosaveTimer); serverAutosaveTimer = null; }
  if (!touchedKeys.size && !commitNonce) return;
  const serialized = buildSaveEnvelope(commitNonce);
  if (!commitNonce && serialized === lastSavedPayload) return;
  lastSavedPayload = serialized;
  lastServerAutosavePayload = serialized;
  persistLocalDraft();
  Streamlit.setComponentValue(serialized);
  touchedKeys = new Set();
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = commitNonce ? 'Applying changes…' : 'Saved';
    note.classList.add('show');
    if (!commitNonce) setTimeout(() => note.classList.remove('show'), 1500);
  }
  updateEditorStats();
}

function attachHandlers() {
  document.getElementById('saveBtn').addEventListener('click', () => saveChanges());
  document.getElementById('undoBtn')?.addEventListener('click', undoLastEdit);
  document.getElementById('resetBlockBtn')?.addEventListener('click', resetSelectedBlock);
  document.getElementById('replaceBtn')?.addEventListener('click', replaceAllText);
  document.getElementById('flagIssueBtn')?.addEventListener('click', flagSelectedIssue);

  document.getElementById('textStylePreset')?.addEventListener('change', event => {
    if (event.target.value) applyTextStylePreset(event.target.value);
    event.target.value = '';
  });
  document.getElementById('colorPreset')?.addEventListener('change', event => {
    if (event.target.value) applyColorPreset(event.target.value);
    event.target.value = '';
  });
  document.getElementById('compactSpacingBtn')?.addEventListener('click', () => applySpacingPreset('compact'));
  document.getElementById('normalSpacingBtn')?.addEventListener('click', () => applySpacingPreset('normal'));
  document.getElementById('addNoteBlockBtn')?.addEventListener('click', addNoteBlock);
  document.getElementById('addDividerBtn')?.addEventListener('click', addDividerBlock);
  document.getElementById('resetBtn')?.addEventListener('click', () => {
    clearLocalDraft();
    model = JSON.parse(JSON.stringify(initialPayload));
    uploadedImages = {};
    touchedKeys = new Set();
    draw();
  });
  document.getElementById('addManualPageBtn')?.addEventListener('click', addManualPage);
  document.querySelectorAll('[data-outline-page-id]').forEach(btn => {
    btn.addEventListener('click', event => {
      const pageId = btn.getAttribute('data-outline-page-id');
      if (event.target?.closest?.('[data-doc-page-action]')) return;
      if (pageId) scrollToPage(pageId);
    });
  });
  document.querySelectorAll('[data-doc-page-action]').forEach(btn => {
    btn.addEventListener('click', event => {
      event.stopPropagation();
      const pageId = btn.getAttribute('data-page-id-ref');
      const action = btn.getAttribute('data-doc-page-action');
      if (!pageId) return;
      if (action === 'hide') hideDocumentPage(pageId);
      if (action === 'restore') restoreDocumentPage(pageId);
      if (action === 'duplicate') duplicateManualPage(pageId);
      if (action === 'move-up') moveManualPage(pageId, -1);
      if (action === 'move-down') moveManualPage(pageId, 1);
    });
  });
  document.querySelectorAll('[data-page-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.getAttribute('data-page-index'));
      const action = btn.getAttribute('data-page-action');
      if (action === 'merge-up') mergeInclusionPageUp(idx);
      if (action === 'delete') deleteInclusionPage(idx);
    });
  });
  document.querySelectorAll('[data-page-id]').forEach(pageEl => {
    pageEl.addEventListener('click', event => {
      if (event.target?.closest?.('button,select,input,label,[data-editor-block-id],[data-edit-key]')) return;
      selectEditorPage(pageEl.getAttribute('data-page-id'));
    });
  });
  document.querySelectorAll('[data-editor-block-id]').forEach(el => {
    el.addEventListener('click', event => {
      if (event.target?.closest?.('button,select,input,label')) return;
      selectEditorBlockFromElement(el);
    });
  });
  attachInspectorHandlers();
  document.querySelectorAll('[contenteditable="true"]').forEach(el => {
    const key = el.getAttribute('data-edit-key');
    el.dataset.lastValue = editableValue(el);
    el.addEventListener('focus', () => {
      activeEditKey = key;
      selectEditorBlockFromElement(el);
      el.dataset.lastValue = editableValue(el);
    });
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
      requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); updateRightInspector(); });
    });
  });
  updateEditorStats();
  updateSelectionUi();

  document.querySelectorAll('[data-cover-img-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      collect();
      const key = btn.getAttribute('data-cover-img-key');
      const action = btn.getAttribute('data-cover-img-action');
      if (!model.cover) model.cover = {};
      const image = model.cover[key] || (model.cover[key] = {mode: 'auto', path: '', crop_focus: 'top', options: []});
      markTouched(`cover.${key}`);
      if (action === 'auto') {
        image.mode = 'auto';
        image.path = '';
        image.data_uri = image.auto_data_uri || image.data_uri || '';
        image.name = image.auto_name || image.name || '';
      }
      if (action === 'none') {
        image.mode = 'none';
        image.path = '';
        image.data_uri = '';
        image.name = '';
      }
      if (action === 'manual') {
        const sel = document.querySelector(`[data-cover-img-bank="${CSS.escape(key)}"]`);
        if (sel && sel.value) {
          const selected = (image.options || []).find(opt => opt.path === sel.value) || {};
          image.mode = 'manual';
          image.path = sel.value;
          image.data_uri = '';
          image.name = selected.name || sel.options[sel.selectedIndex]?.text || '';
          image.pending_preview = true;
        }
      }
      draw();
    });
  });
  document.querySelectorAll('[data-cover-img-focus]').forEach(sel => {
    sel.addEventListener('change', () => {
      const key = sel.getAttribute('data-cover-img-focus');
      if (!model.cover) model.cover = {};
      const image = model.cover[key] || (model.cover[key] = {mode: 'auto', path: '', crop_focus: 'top', options: []});
      image.crop_focus = sel.value;
      markTouched(`cover.${key}`);
      const page = sel.closest('.a4-page');
      if (page) page.style.backgroundPosition = focusPos(sel.value);
    });
  });
  document.querySelectorAll('[data-img-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      collect();
      const idx = Number(btn.getAttribute('data-day-index'));
      const action = btn.getAttribute('data-img-action');
      const day = model.days[idx];
      if (!day || !day.image) return;
      markTouched(`days.${idx}.image`);
      if (action === 'auto') {
        day.image.mode = 'auto';
        day.image.path = '';
        day.image.data_uri = day.image.auto_data_uri || day.image.data_uri || '';
        day.image.name = day.image.auto_name || day.image.name || '';
      }
      if (action === 'none') {
        day.image.mode = 'none';
        day.image.path = '';
        day.image.data_uri = '';
        day.image.name = '';
      }
      if (action === 'manual') {
        const sel = document.querySelector(`[data-img-bank="${idx}"]`);
        if (sel && sel.value) {
          const selected = (day.image.options || []).find(opt => opt.path === sel.value) || {};
          day.image.mode = 'manual';
          day.image.path = sel.value;
          day.image.data_uri = '';
          day.image.name = selected.name || sel.options[sel.selectedIndex]?.text || '';
          day.image.pending_preview = true;
        }
      }
      draw();
      
    });
  });
  document.querySelectorAll('[data-img-focus]').forEach(sel => {
    sel.addEventListener('change', () => {
      const idx = Number(sel.getAttribute('data-img-focus'));
      if (model.days[idx] && model.days[idx].image) model.days[idx].image.crop_focus = sel.value;
      markTouched(`days.${idx}.image`);
      
      const img = sel.closest('.image-stage')?.querySelector('img');
      if (img) img.style.objectPosition = focusPos(sel.value);
    });
  });
  document.querySelectorAll('[data-img-upload]').forEach(input => {
    input.addEventListener('change', () => {
      const idx = Number(input.getAttribute('data-img-upload'));
      const file = input.files && input.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        uploadedImages[idx] = {filename: file.name, data_uri: reader.result, season: 'Summer', label: file.name.replace(/\.[^.]+$/, '')};
        markTouched(`days.${idx}.image`);
        if (model.days[idx] && model.days[idx].image) {
          model.days[idx].image.mode = 'manual';
          model.days[idx].image.path = '';
          model.days[idx].image.data_uri = reader.result;
        }
        const stage = input.closest('.image-stage');
        if (stage) {
          stage.classList.remove('empty');
          const existing = stage.querySelector('img');
          if (existing) existing.src = reader.result;
          else stage.insertAdjacentHTML('afterbegin', `<img src="${reader.result}" style="object-position:${focusPos(model.days[idx].image.crop_focus)}" alt="Uploaded picture">`);
          requestAnimationFrame(adjustDayImages);
        }
        
      };
      reader.readAsDataURL(file);
    });
  });
}
window.addEventListener('beforeunload', () => {
  if (touchedKeys.size) {
    collect();
    persistLocalDraft();
  }
});
