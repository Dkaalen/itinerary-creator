function setByPath(obj, path, value) {
  const parts = path.split('.');
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    const nextPart = parts[i+1];
    if (Array.isArray(cur)) cur = cur[Number(part)];
    else cur = cur[part] ?? (cur[part] = /^\d+$/.test(nextPart) ? [] : {});
  }
  const last = parts[parts.length - 1];
  if (Array.isArray(cur)) cur[Number(last)] = value;
  else cur[last] = value;
}
function collect() {
  document.querySelectorAll('[data-edit-key]').forEach(el => {
    const key = el.getAttribute('data-edit-key');
    const value = editableValue(el);
    setByPath(model, key, value);
  });
  Object.keys(uploadedImages).forEach(idx => {
    if (model.days[idx]) model.days[idx].image.upload = uploadedImages[idx];
  });
  return model;
}

function compactImage(image) {
  const copy = JSON.parse(JSON.stringify(image || {}));
  delete copy.data_uri;
  delete copy.auto_data_uri;
  delete copy.options;
  if (copy.upload && !copy.upload.data_uri) delete copy.upload;
  return copy;
}

function buildEditableDraftFromPayload(value) {
  const source = JSON.parse(JSON.stringify(value || {}));
  const draft = {
    schema_version: 3,
    cover: source.cover || {},
    summary: source.summary || {},
    days: [],
    final_sections: [],
    workflow: source.workflow || {},
    issue_flags: Array.isArray(source.issue_flags) ? source.issue_flags : []
  };
  (Array.isArray(source.days) ? source.days : []).forEach((day, index) => {
    const dayId = String(day?.day || day?.day_id || day?.label || `Day ${index + 1}`);
    const blocks = Object.prototype.hasOwnProperty.call(day || {}, 'blocks_html')
      ? [{block_id: 'main', kind: 'day_content', title: '', content_html: String(day?.blocks_html ?? '')}]
      : (Array.isArray(day?.blocks) && day.blocks.length
        ? day.blocks.map((block, blockIndex) => ({
            block_id: String(block?.block_id || `main-${blockIndex + 1}`),
            kind: String(block?.kind || 'day_content'),
            title: String(block?.title || ''),
            content_html: String(block?.content_html ?? block?.html ?? '')
          }))
        : [{block_id: 'main', kind: 'day_content', title: '', content_html: ''}]);
    const draftDay = {
      day_id: dayId,
      label: String(day?.label || dayId),
      date: String(day?.date || ''),
      title: String(day?.title || ''),
      city: String(day?.city || ''),
      intro: String(day?.intro || ''),
      blocks
    };
    if (day?.image) draftDay.image = compactImage(day.image);
    draft.days.push(draftDay);
  });
  const finalPages = source.final_pages || {};
  if ('whats_included_pages_html' in finalPages || 'whats_included_html' in finalPages || 'whats_included_text' in finalPages) {
    const pages = Array.isArray(finalPages.whats_included_pages_html)
      ? finalPages.whats_included_pages_html.map((page, index) => ({page_id: `page-${index + 1}`, content_html: String(typeof page === 'string' ? page : (page?.html ?? page?.content_html ?? ''))}))
      : (finalPages.whats_included_html ? [{page_id: 'page-1', content_html: String(finalPages.whats_included_html || '')}] : []);
    draft.final_sections.push({section_id: 'whats_included', title: "What's included", pages, text: String(finalPages.whats_included_text || ''), content_html: String(finalPages.whats_included_html || '')});
  }
  if ('whats_not_included_html' in finalPages || 'whats_not_included_text' in finalPages) {
    const html = String(finalPages.whats_not_included_html || '');
    draft.final_sections.push({section_id: 'whats_not_included', title: "What's not included", pages: html ? [{page_id: 'page-1', content_html: html}] : [], text: String(finalPages.whats_not_included_text || ''), content_html: html});
  }
  if ('important_travel_notes_text' in finalPages) {
    draft.final_sections.push({section_id: 'important_travel_notes', title: 'Important travel notes', pages: [], text: String(finalPages.important_travel_notes_text || ''), content_html: ''});
  }
  return draft;
}
function attachEditableDraft(value) {
  const copy = JSON.parse(JSON.stringify(value || {}));
  copy.editor_draft = buildEditableDraftFromPayload(copy);
  return copy;
}
function getByPath(obj, path) {
  return path.split('.').reduce((cur, part) => {
    if (cur == null) return undefined;
    return Array.isArray(cur) ? cur[Number(part)] : cur[part];
  }, obj);
}
function pruneForSave(value) {
  const full = JSON.parse(JSON.stringify(value || {}));
  const payload = {cover: {}, summary: {}, days: [], final_pages: {}};
  const dayMap = {};
  function dayPayload(index) {
    if (!dayMap[index]) {
      dayMap[index] = {day: full.days?.[index]?.day || `Day ${index + 1}`};
      payload.days.push(dayMap[index]);
    }
    return dayMap[index];
  }

  touchedKeys.forEach(key => {
    if (key.startsWith('cover.')) {
      const name = key.slice('cover.'.length);
      payload.cover[name] = full.cover?.[name] ?? '';
    } else if (key.startsWith('summary.trip_glance.')) {
      payload.summary.trip_glance = full.summary?.trip_glance || {};
    } else if (key.startsWith('summary.journey_arc.')) {
      payload.summary.journey_arc = full.summary?.journey_arc || [];
    } else if (key.startsWith('days.')) {
      const parts = key.split('.');
      const index = Number(parts[1]);
      const field = parts[2];
      if (!Number.isFinite(index) || !field) return;
      const day = dayPayload(index);
      if (field === 'image') day.image = compactImage(full.days?.[index]?.image || {});
      else day[field] = getByPath(full, key) ?? '';
    } else if (key.startsWith('final_pages.whats_included_pages_html.')) {
      payload.final_pages.whats_included_pages_html = full.final_pages?.whats_included_pages_html || [];
    } else if (key === 'issue_flags') {
      payload.issue_flags = full.issue_flags || [];
    } else if (key.startsWith('final_pages.')) {
      const name = key.slice('final_pages.'.length);
      payload.final_pages[name] = full.final_pages?.[name] ?? '';
    }
  });

  if (touchedKeys.size) payload.editor_draft = buildEditableDraftFromPayload(payload);
  return payload;
}
function markTouched(key) {
  if (key) touchedKeys.add(key);
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = 'Unsaved edits';
    note.classList.add('show');
  }
  persistLocalDraft();
  updateEditorStats();
}
function isHtmlEditKey(key) {
  return key && (key.endsWith('.blocks_html') || key.endsWith('.whats_included_html') || key.endsWith('.whats_not_included_html') || key.includes('.whats_included_pages_html.'));
}
function editableValue(el) {
  if (!el) return '';
  const key = el.getAttribute('data-edit-key') || '';
  if (isHtmlEditKey(key)) return el.innerHTML.trim();
  return el.innerText.replace(/\u00a0/g, ' ').replace(/\s*\n+\s*/g, key === 'cover.destinations_line' ? ' · ' : ' ').trim();
}
function writeEditableValue(el, value) {
  if (!el) return;
  const key = el.getAttribute('data-edit-key') || '';
  if (isHtmlEditKey(key)) el.innerHTML = value || '';
  else el.innerText = value || '';
  setByPath(model, key, editableValue(el));
  markTouched(key);
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); });
}
function findEditableByKey(key) {
  if (!key) return null;
  return document.querySelector(`[data-edit-key="${CSS.escape(key)}"]`);
}
function selectedEditable() {
  const active = document.activeElement?.closest?.('[data-edit-key]');
  if (active) return active;
  if (activeEditKey) return findEditableByKey(activeEditKey);
  return null;
}
function initialValueForKey(key) {
  const value = getByPath(initialPayload, key);
  if (value && typeof value === 'object' && 'html' in value) return value.html || '';
  return value ?? '';
}
function pushUndo(el, previousValue) {
  const key = el?.getAttribute('data-edit-key');
  if (!key) return;
  undoStack.push({key, value: previousValue});
  if (undoStack.length > 80) undoStack.shift();
}
function undoLastEdit() {
  const last = undoStack.pop();
  if (!last) return;
  const el = findEditableByKey(last.key);
  if (el) writeEditableValue(el, last.value);
}
function resetSelectedBlock() {
  const el = selectedEditable();
  if (!el) return;
  pushUndo(el, editableValue(el));
  writeEditableValue(el, String(initialValueForKey(el.getAttribute('data-edit-key')) ?? ''));
}
function replaceAllText() {
  const find = document.getElementById('findText')?.value || '';
  const repl = document.getElementById('replaceText')?.value || '';
  if (!find) return;
  document.querySelectorAll('[data-edit-key]').forEach(el => {
    const before = isHtmlEditKey(el.getAttribute('data-edit-key')) ? el.innerHTML : el.innerText;
    if (!before || !before.includes(find)) return;
    pushUndo(el, editableValue(el));
    if (isHtmlEditKey(el.getAttribute('data-edit-key'))) el.innerHTML = before.split(find).join(repl);
    else el.innerText = before.split(find).join(repl);
    markTouched(el.getAttribute('data-edit-key'));
  });
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); });
}
function notifyEditor(message) {
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = message;
    note.classList.add('show');
  }
}
function closestEditableBlock() {
  const selection = window.getSelection();
  let node = selection?.anchorNode || document.activeElement;
  if (node && node.nodeType === Node.TEXT_NODE) node = node.parentElement;
  const editable = node?.closest?.('[data-edit-key]') || selectedEditable();
  if (!editable) return null;
  const candidate = node?.closest?.('li,p,div,span') || editable;
  if (!editable.contains(candidate) && candidate !== editable) return editable;
  return candidate === editable ? editable : candidate;
}
function makeSelectedBlockClass(className) {
  const editable = selectedEditable();
  const block = closestEditableBlock();
  if (!editable || !block) return;
  pushUndo(editable, editableValue(editable));
  ['section-title','row-type','strong-line','body-text','meta-line','inclusion-entry-title','inclusion-entry-detail'].forEach(cls => block.classList?.remove(cls));
  if (className) block.classList?.add(className);
  markTouched(editable.getAttribute('data-edit-key'));
  requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); });
}
function plainTextToCleanPasteHtml(text) {
  const lines = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const chunks = [];
  let list = [];
  function flushList() {
    if (list.length) {
      chunks.push('<ul>' + list.map(item => `<li>${esc(item)}</li>`).join('') + '</ul>');
      list = [];
    }
  }
  lines.forEach(raw => {
    const line = raw.trim();
    if (!line) { flushList(); return; }
    const bullet = line.match(/^(?:[•\-*]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      list.push(bullet[1].trim());
    } else {
      flushList();
      chunks.push(`<div>${esc(line)}</div>`);
    }
  });
  flushList();
  return chunks.join('') || esc(text || '');
}
function sanitizeClipboardHtml(html, fallbackText) {
  if (!html || !String(html).trim()) return plainTextToCleanPasteHtml(fallbackText || '');
  const box = document.createElement('div');
  box.innerHTML = html;
  const allowedTags = new Set(['DIV','P','BR','UL','OL','LI','STRONG','B','EM','I','SPAN']);
  const allowedClasses = new Set(['section-title','row-type','strong-line','body-text','detail-list','final-list','inclusion-entry','inclusion-entry-title','inclusion-entry-detail','inclusion-entry-spacer','meta-line','meta-label','small-section','content-block']);
  box.querySelectorAll('*').forEach(node => {
    const tag = node.tagName;
    if (!allowedTags.has(tag)) {
      const parent = node.parentNode;
      while (node.firstChild) parent.insertBefore(node.firstChild, node);
      parent.removeChild(node);
      return;
    }
    const classes = node.classList ? Array.from(node.classList).filter(cls => allowedClasses.has(cls)) : [];
    Array.from(node.attributes).forEach(attr => node.removeAttribute(attr.name));
    if (classes.length) node.setAttribute('class', classes.join(' '));
  });
  const cleaned = box.innerHTML.trim();
  return cleaned || plainTextToCleanPasteHtml(fallbackText || '');
}
function insertCleanClipboardHtml(event) {
  event.preventDefault();
  const data = event.clipboardData || window.clipboardData;
  const html = sanitizeClipboardHtml(data?.getData('text/html') || '', data?.getData('text/plain') || '');
  document.execCommand('insertHTML', false, html);
}
function pageObjectAt(index) {
  const pages = Array.isArray(model.final_pages?.whats_included_pages_html) ? model.final_pages.whats_included_pages_html : [];
  if (index < 0 || index >= pages.length) return {pages, page: null};
  const page = typeof pages[index] === 'string' ? {html: pages[index]} : (pages[index] || {html: ''});
  pages[index] = page;
  return {pages, page};
}
function htmlTextContent(html) {
  const box = document.createElement('div');
  box.innerHTML = html || '';
  return (box.textContent || '').replace(/\s+/g, ' ').trim();
}
function currentListItem() {
  const selection = window.getSelection();
  let node = selection?.anchorNode || document.activeElement;
  if (node && node.nodeType === Node.TEXT_NODE) node = node.parentElement;
  return node?.closest?.('li') || null;
}
function editableForListAction() {
  const li = currentListItem();
  if (li) return li.closest('[data-edit-key]');
  return selectedEditable();
}
function addBullet() {
  const el = editableForListAction();
  if (!el) return;
  pushUndo(el, editableValue(el));
  let list = currentListItem()?.parentElement || el.querySelector('ul,ol');
  if (!list) {
    el.insertAdjacentHTML('beforeend', '<ul><li>New item</li></ul>');
  } else {
    const li = currentListItem();
    const newLi = document.createElement('li');
    newLi.textContent = 'New item';
    if (li && li.parentElement === list) li.insertAdjacentElement('afterend', newLi);
    else list.appendChild(newLi);
  }
  markTouched(el.getAttribute('data-edit-key'));
  requestAnimationFrame(adjustDayImages);
}
function deleteBullet() {
  const li = currentListItem();
  const el = li?.closest?.('[data-edit-key]');
  if (!li || !el) return;
  pushUndo(el, editableValue(el));
  li.remove();
  markTouched(el.getAttribute('data-edit-key'));
  requestAnimationFrame(adjustDayImages);
}
function moveBullet(direction) {
  const li = currentListItem();
  const el = li?.closest?.('[data-edit-key]');
  if (!li || !el) return;
  pushUndo(el, editableValue(el));
  if (direction < 0 && li.previousElementSibling) li.parentElement.insertBefore(li, li.previousElementSibling);
  if (direction > 0 && li.nextElementSibling) li.parentElement.insertBefore(li.nextElementSibling, li);
  markTouched(el.getAttribute('data-edit-key'));
  requestAnimationFrame(adjustDayImages);
}
function stripEditorArtifactsFromHtml(html) {
  const box = document.createElement('div');
  box.innerHTML = html || '';
  box.querySelectorAll('*').forEach(node => {
    node.removeAttribute('style');
    node.removeAttribute('contenteditable');
    node.removeAttribute('data-edit-key');
    node.classList.remove('warning-hit');
  });
  return box.innerHTML;
}
function deleteInclusionPage(index) {
  collect();
  if (!model.final_pages) model.final_pages = {};
  const {pages, page} = pageObjectAt(index);
  if (!pages.length || !page) return;
  const pageText = htmlTextContent(page.html || '');
  if (pageText) {
    notifyEditor('Page still has content — move content up or clear it before removing the page.');
    return;
  }
  pages.splice(index, 1);
  model.final_pages.whats_included_pages_html = pages.length ? pages : [{html: ''}];
  markTouched('final_pages.whats_included_pages_html');
  draw();
}
function mergeInclusionPageUp(index) {
  collect();
  if (!model.final_pages) model.final_pages = {};
  const pages = Array.isArray(model.final_pages.whats_included_pages_html) ? model.final_pages.whats_included_pages_html : [];
  if (index <= 0 || index >= pages.length) return;
  const previous = typeof pages[index - 1] === 'string' ? {html: pages[index - 1]} : (pages[index - 1] || {html: ''});
  const current = typeof pages[index] === 'string' ? {html: pages[index]} : (pages[index] || {html: ''});
  const previousHtml = stripEditorArtifactsFromHtml(previous.html || '');
  const currentHtml = stripEditorArtifactsFromHtml(current.html || '');
  if (!htmlTextContent(currentHtml)) {
    notifyEditor('Nothing to move from this page.');
    return;
  }
  previous.html = `${previousHtml}${previousHtml && currentHtml ? '<div class="inclusion-entry-spacer"></div>' : ''}${currentHtml}`;
  pages[index - 1] = previous;
  pages.splice(index, 1);
  model.final_pages.whats_included_pages_html = pages;
  markTouched('final_pages.whats_included_pages_html');
  draw();
}
function flagSelectedIssue() {
  const el = selectedEditable();
  if (!el) return;
  const key = el.getAttribute('data-edit-key');
  const flag = {
    key,
    label: el.closest('.page-wrap')?.querySelector('.page-label')?.innerText || '',
    original: String(initialValueForKey(key) ?? ''),
    corrected: editableValue(el),
  };
  if (!Array.isArray(model.issue_flags)) model.issue_flags = [];
  model.issue_flags.push(flag);
  markTouched('issue_flags');
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = 'Issue flagged';
    note.classList.add('show');
  }
}
function highlightWarnings() {
  let count = 0;
  document.querySelectorAll('[data-edit-key]').forEach(el => {
    const text = el.innerText || '';
    const hit = WARNING_PATTERNS.some(pattern => pattern.test(text));
    el.classList.toggle('warning-hit', hit);
    if (hit) count += 1;
  });
  const serverWarnings = Array.isArray(model.client_output_warnings) ? model.client_output_warnings.length : 0;
  const warningCount = document.getElementById('warningCount');
  if (warningCount) warningCount.textContent = `${Math.max(count, serverWarnings)} warnings`;
}
function updateEditorStats() {
  const editCount = document.getElementById('editCount');
  if (editCount) editCount.textContent = `${touchedKeys.size} manual edits pending`;
  highlightWarnings();
}

function compactFullPayloadForCommit(value) {
  const full = JSON.parse(JSON.stringify(value || {}));
  (full.days || []).forEach(day => {
    if (day.image) day.image = compactImage(day.image);
  });
  full.editor_draft = buildEditableDraftFromPayload(full);
  return full;
}
function buildSaveEnvelope(commitNonce = null) {
  collect();
  const isPdfCommit = commitNonce !== null && commitNonce !== undefined && commitNonce !== '';
  // PDF export is the hard commit point. Send the full visible editor model,
  // not only keys that browser input events noticed, so the PDF cannot miss
  // a direct preview edit. Normal "Save for now" remains minimal.
  const payload = isPdfCommit ? compactFullPayloadForCommit(model) : pruneForSave(model);
  if (isPdfCommit) {
    return JSON.stringify({commit_nonce: String(commitNonce), payload});
  }
  return JSON.stringify(payload);
}

function saveRestoredLocalDraftToServer() {
  if (!restoredLocalDraftPendingSave) return;
  restoredLocalDraftPendingSave = false;
  collect();
  const serialized = JSON.stringify(compactFullPayloadForCommit(model));
  if (serialized === lastSavedPayload) return;
  lastSavedPayload = serialized;
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
  if (!touchedKeys.size && !commitNonce) return;
  const serialized = buildSaveEnvelope(commitNonce);
  if (!commitNonce && serialized === lastSavedPayload) return;
  lastSavedPayload = serialized;
  persistLocalDraft();
  Streamlit.setComponentValue(serialized);
  touchedKeys = new Set();
  const note = document.getElementById('savedNote');
  if (note) {
    note.textContent = commitNonce ? 'Applying edits before PDF…' : 'Saved';
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
  document.getElementById('addBulletBtn')?.addEventListener('click', addBullet);
  document.getElementById('deleteBulletBtn')?.addEventListener('click', deleteBullet);
  document.getElementById('moveBulletUpBtn')?.addEventListener('click', () => moveBullet(-1));
  document.getElementById('moveBulletDownBtn')?.addEventListener('click', () => moveBullet(1));
  document.getElementById('makeHeadingBtn')?.addEventListener('click', () => makeSelectedBlockClass('section-title'));
  document.getElementById('makeNormalBtn')?.addEventListener('click', () => makeSelectedBlockClass(''));
  document.getElementById('flagIssueBtn')?.addEventListener('click', flagSelectedIssue);
  document.getElementById('resetBtn')?.addEventListener('click', () => {
    clearLocalDraft();
    model = JSON.parse(JSON.stringify(initialPayload));
    uploadedImages = {};
    touchedKeys = new Set();
    draw();
  });
  document.querySelectorAll('[data-page-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.getAttribute('data-page-index'));
      const action = btn.getAttribute('data-page-action');
      if (action === 'merge-up') mergeInclusionPageUp(idx);
      if (action === 'delete') deleteInclusionPage(idx);
    });
  });
  document.querySelectorAll('[contenteditable="true"]').forEach(el => {
    const key = el.getAttribute('data-edit-key');
    el.dataset.lastValue = editableValue(el);
    el.addEventListener('focus', () => {
      activeEditKey = key;
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
      requestAnimationFrame(() => { highlightWarnings(); adjustDayImages(); });
    });
  });
  updateEditorStats();
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
