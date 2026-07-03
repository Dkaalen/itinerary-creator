function setByPath(obj, path, value) {
  const parts = String(path || '').split('.').filter(Boolean);
  if (!parts.length || !obj || typeof obj !== 'object') return;
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    const nextPart = parts[i + 1];
    const shouldCreateArray = /^\d+$/.test(nextPart || '');
    if (Array.isArray(cur)) {
      const index = Number(part);
      if (!Number.isInteger(index) || index < 0) return;
      if (!cur[index] || typeof cur[index] !== 'object') cur[index] = shouldCreateArray ? [] : {};
      cur = cur[index];
    } else {
      if (!cur[part] || typeof cur[part] !== 'object') cur[part] = shouldCreateArray ? [] : {};
      cur = cur[part];
    }
  }
  const last = parts[parts.length - 1];
  if (Array.isArray(cur)) {
    const index = Number(last);
    if (Number.isInteger(index) && index >= 0) cur[index] = value;
  } else if (cur && typeof cur === 'object') {
    cur[last] = value;
  }
}
function saveComparableValue(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  return String(value);
}

function syncUploadedImages(options = {}) {
  const trackChanges = options?.trackChanges === true;
  Object.keys(uploadedImages || {}).forEach(idx => {
    if (!model.days?.[idx]) return;
    if (!model.days[idx].image) model.days[idx].image = {};
    model.days[idx].image.upload = uploadedImages[idx];
    if (trackChanges) touchedKeys.add(`days.${idx}.image`);
  });
}

function syncVisibleEditableFields(options = {}) {
  const trackChanges = options?.trackChanges === true;
  document.querySelectorAll('[data-edit-key]').forEach(el => {
    const key = el.getAttribute('data-edit-key');
    if (!key) return;
    const value = editableValue(el);
    const previous = getByPath(model, key);
    if (trackChanges && saveComparableValue(value) !== saveComparableValue(previous)) {
      touchedKeys.add(key);
    }
    setByPath(model, key, value);
  });
}

function collect() {
  syncVisibleEditableFields();
  syncUploadedImages();
  return model;
}

function collectTouched() {
  if (touchedKeys && touchedKeys.size) {
    touchedKeys.forEach(key => {
      const el = document.querySelector(`[data-edit-key="${cssEscapeValue(key)}"]`);
      if (el) setByPath(model, key, editableValue(el));
    });
  }
  syncUploadedImages({trackChanges: true});
  return model;
}

// Do not redraw during explicit PDF commit; the bridge returns before draw() so browser-local edits cannot be wiped.
function collectCommitDelta() {
  syncVisibleEditableFields({trackChanges: true});
  syncUploadedImages({trackChanges: true});
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
  delete source.brand;
  const coverDraft = JSON.parse(JSON.stringify(source.cover || {}));
  if (coverDraft.cover_image) coverDraft.cover_image = compactImage(coverDraft.cover_image);
  if (coverDraft.summary_image) coverDraft.summary_image = compactImage(coverDraft.summary_image);
  const draft = {
    schema_version: 3,
    cover: coverDraft,
    summary: source.summary || {},
    days: [],
    final_sections: [],
    document_pages: Array.isArray(source.document_pages) ? JSON.parse(JSON.stringify(source.document_pages)) : [],
    workflow: source.workflow || {},
    issue_flags: Array.isArray(source.issue_flags) ? source.issue_flags : []
  };
  (Array.isArray(source.days) ? source.days : []).forEach((day, index) => {
    const dayId = String(day?.day || day?.day_id || day?.label || `Day ${index + 1}`);
    const touched = new Set(Array.isArray(day?.touched_fields) ? day.touched_fields : []);
    ['label', 'date', 'title', 'city', 'intro', 'intro_generated_value', 'intro_generator_version', 'intro_source_signature', 'intro_manual_override', 'blocks_html_generated_value', 'blocks_html_generator_version', 'blocks_manual_override', 'image'].forEach(field => {
      if (Object.prototype.hasOwnProperty.call(day || {}, field)) touched.add(field);
    });
    if (Object.prototype.hasOwnProperty.call(day || {}, 'blocks_html') || Object.prototype.hasOwnProperty.call(day || {}, 'blocks')) touched.add('blocks');
    const draftDay = {day_id: dayId, touched_fields: Array.from(touched)};
    if (Object.prototype.hasOwnProperty.call(day || {}, 'label')) draftDay.label = String(day?.label || dayId);
    if (Object.prototype.hasOwnProperty.call(day || {}, 'date')) draftDay.date = String(day?.date || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'title')) draftDay.title = String(day?.title || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'city')) draftDay.city = String(day?.city || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'intro')) draftDay.intro = String(day?.intro || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'intro_generated_value')) draftDay.intro_generated_value = String(day?.intro_generated_value || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'intro_generator_version')) draftDay.intro_generator_version = String(day?.intro_generator_version || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'intro_source_signature')) draftDay.intro_source_signature = String(day?.intro_source_signature || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'intro_manual_override')) draftDay.intro_manual_override = !!day?.intro_manual_override;
    if (Object.prototype.hasOwnProperty.call(day || {}, 'blocks_html_generated_value')) draftDay.blocks_html_generated_value = String(day?.blocks_html_generated_value || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'blocks_html_generator_version')) draftDay.blocks_html_generator_version = String(day?.blocks_html_generator_version || '');
    if (Object.prototype.hasOwnProperty.call(day || {}, 'blocks_manual_override')) draftDay.blocks_manual_override = !!day?.blocks_manual_override;
    if (Object.prototype.hasOwnProperty.call(day || {}, 'blocks_html') || Object.prototype.hasOwnProperty.call(day || {}, 'blocks')) {
      draftDay.blocks = Object.prototype.hasOwnProperty.call(day || {}, 'blocks_html')
        ? [{block_id: 'main', kind: 'day_content', title: '', content_html: String(day?.blocks_html ?? '')}]
        : (Array.isArray(day?.blocks) && day.blocks.length
          ? day.blocks.map((block, blockIndex) => ({
              block_id: String(block?.block_id || `main-${blockIndex + 1}`),
              kind: String(block?.kind || 'day_content'),
              title: String(block?.title || ''),
              content_html: String(block?.content_html ?? block?.html ?? '')
            }))
          : [{block_id: 'main', kind: 'day_content', title: '', content_html: ''}]);
    }
    if (day?.image) draftDay.image = compactImage(day.image);
    draft.days.push(draftDay);
  });
  const finalPages = source.final_pages || {};
  if ('whats_included_pages_html' in finalPages || 'whats_included_html' in finalPages || 'whats_included_text' in finalPages) {
    const pages = Array.isArray(finalPages.whats_included_pages_html)
      ? finalPages.whats_included_pages_html.map((page, index) => ({page_id: `page-${index + 1}`, content_html: String(typeof page === 'string' ? page : (page?.html ?? page?.content_html ?? ''))}))
      : (finalPages.whats_included_html ? [{page_id: 'page-1', content_html: String(finalPages.whats_included_html || '')}] : []);
    draft.final_sections.push({section_id: 'whats_included', title: String(finalPages.whats_included_title || "What's included"), pages, text: String(finalPages.whats_included_text || ''), content_html: String(finalPages.whats_included_html || '')});
  }
  if ('whats_not_included_html' in finalPages || 'whats_not_included_text' in finalPages) {
    const html = String(finalPages.whats_not_included_html || '');
    draft.final_sections.push({section_id: 'whats_not_included', title: String(finalPages.whats_not_included_title || "What's not included"), pages: html ? [{page_id: 'page-1', content_html: html}] : [], text: String(finalPages.whats_not_included_text || ''), content_html: html});
  }
  if ('important_travel_notes_text' in finalPages) {
    draft.final_sections.push({section_id: 'important_travel_notes', title: String(finalPages.important_travel_notes_title || 'Important travel notes'), pages: [], text: String(finalPages.important_travel_notes_text || ''), content_html: ''});
  }
  return draft;
}
function attachEditableDraft(value) {
  const copy = JSON.parse(JSON.stringify(value || {}));
  delete copy.brand;
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
  delete full.brand;
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
      if (name === 'cover_image' || name === 'summary_image') payload.cover[name] = compactImage(full.cover?.[name] || {});
      else payload.cover[name] = full.cover?.[name] ?? '';
    } else if (key.startsWith('summary.trip_glance.')) {
      payload.summary.trip_glance = full.summary?.trip_glance || {};
    } else if (key.startsWith('summary.journey_arc.')) {
      payload.summary.journey_arc = full.summary?.journey_arc || [];
    } else if (key.startsWith('summary.')) {
      const name = key.slice('summary.'.length);
      setByPath(payload.summary, name, getByPath(full, key) ?? '');
    } else if (key.startsWith('days.')) {
      const parts = key.split('.');
      const index = Number(parts[1]);
      const field = parts[2];
      if (!Number.isFinite(index) || !field) return;
      const day = dayPayload(index);
      if (field === 'image') day.image = compactImage(full.days?.[index]?.image || {});
      else {
        day[field] = getByPath(full, key) ?? '';
        if (field === 'intro') day.intro_manual_override = true;
        if (field === 'blocks_html') day.blocks_manual_override = true;
      }
    } else if (key.startsWith('final_pages.whats_included_pages_html.')) {
      payload.final_pages.whats_included_pages_html = full.final_pages?.whats_included_pages_html || [];
    } else if (key === 'issue_flags') {
      payload.issue_flags = full.issue_flags || [];
    } else if (key.startsWith('final_pages.')) {
      const name = key.slice('final_pages.'.length);
      payload.final_pages[name] = full.final_pages?.[name] ?? '';
    }
  });

  if (touchedKeys.size) {
    const documentPagesTouched = Array.from(touchedKeys || []).some(key => key === 'document_pages' || String(key || '').startsWith('document_pages.'));
    if (documentPagesTouched) {
      payload.document_pages = Array.isArray(full.document_pages) ? JSON.parse(JSON.stringify(full.document_pages)) : [];
    }
    payload.editor_draft = buildEditableDraftFromPayload(payload);
  }
  return payload;
}

function compactFullPayloadForCommit(value) {
  const full = JSON.parse(JSON.stringify(value || {}));
  delete full.brand;
  if (full.cover?.cover_image) full.cover.cover_image = compactImage(full.cover.cover_image);
  if (full.cover?.summary_image) full.cover.summary_image = compactImage(full.cover.summary_image);
  (full.days || []).forEach((day, index) => {
    if (day.image) day.image = compactImage(day.image);
    if (touchedKeys.has(`days.${index}.intro`)) day.intro_manual_override = true;
    if (touchedKeys.has(`days.${index}.blocks_html`)) day.blocks_manual_override = true;
  });
  full.document_pages = Array.isArray(full.document_pages) ? full.document_pages : [];
  full.editor_draft = buildEditableDraftFromPayload(full);
  return full;
}
function buildSaveEnvelope(commitNonce = null) {
  const isPdfCommit = commitNonce !== null && commitNonce !== undefined && commitNonce !== '';
  if (isPdfCommit) collectCommitDelta();
  else collectTouched();
  // PDF export is the hard commit point, but it must stay fast. Scan the visible
  // editor for any missed browser-side edits, then send only the changed fields
  // (or a tiny no-op acknowledgement) instead of the full itinerary model.
  const payload = pruneForSave(model);
  if (isPdfCommit) {
    payload.meta = Object.assign({}, model.meta || {});
    const commitSourceSignature = (typeof activeCommitSourceSignature !== 'undefined' && activeCommitSourceSignature) ? String(activeCommitSourceSignature) : '';
    if (commitSourceSignature) payload.meta.source_signature = commitSourceSignature;
    payload.workflow = model.workflow || {};
    payload.save_mode = touchedKeys && touchedKeys.size ? 'commit_delta' : 'commit_noop';
    return JSON.stringify({commit_nonce: String(commitNonce), payload});
  }
  return JSON.stringify(payload);
}

function buildServerAutosaveEnvelope() {
  collectTouched();
  const payload = pruneForSave(model);
  // Server autosave is intentionally delta-based. Keep only changed fields plus
  // the small identity metadata needed for safe recovery/merge. PDF export uses
  // the same changed-field contract after scanning the visible editor for misses.
  payload.draft_id = model.draft_id || '';
  payload.meta = model.meta || {};
  payload.workflow = model.workflow || {};
  payload.save_mode = 'delta';
  if (!payload.editor_draft) payload.editor_draft = buildEditableDraftFromPayload(payload);
  return JSON.stringify({autosave: true, delta: true, payload});
}
