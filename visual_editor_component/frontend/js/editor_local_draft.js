/** Responsibility split from state.js. */
function draftStorageKey() {
  const fallback = [initialPayload?.cover?.trip_title || '', initialPayload?.cover?.trip_dates || '', (initialPayload?.days || []).length].join('|');
  return `itinerary-visual-editor-draft:${initialPayload?.draft_id || fallback}`;
}

function stripUploadBinaryForLocalDraft(value) {
  const copy = JSON.parse(JSON.stringify(value || {}));
  (copy.days || []).forEach(day => {
    const upload = day?.image?.upload;
    if (upload && typeof upload === 'object') {
      delete upload.data_uri;
      upload.data_omitted = true;
    }
  });
  return copy;
}

function persistLocalDraft() {
  if (!model || !initialPayload) return;
  try {
    const compact = stripUploadBinaryForLocalDraft(compactFullPayloadForCommit(model));
    const snapshot = attachEditableDraft(compact);
    localStorage.setItem(draftStorageKey(), JSON.stringify({
      saved_at: Date.now(),
      source_signature: initialPayload?.meta?.source_signature || '',
      draft_schema_version: initialPayload?.meta?.draft_schema_version || 1,
      model: snapshot
    }));
    saveState.localDraftAt = Date.now();
  } catch (err) {}
}

function sameDraftDay(a, b, fallbackIndex) {
  const left = String(a?.day || a?.label || fallbackIndex || '').trim();
  const right = String(b?.day || b?.label || fallbackIndex || '').trim();
  return left && right && left === right;
}

function findServerDayForLocalDraft(mergedDays, localDay, fallbackIndex) {
  if (!Array.isArray(mergedDays)) return null;
  const byIdentity = mergedDays.find(day => sameDraftDay(day, localDay, fallbackIndex));
  if (byIdentity) return byIdentity;
  return mergedDays[fallbackIndex] || null;
}

function mergeLocalDraftOntoServerPayload(localDraft) {
  const merged = JSON.parse(JSON.stringify(initialPayload || {}));
  const serverPicturesAdded = !!initialPayload?.workflow?.pictures_added;
  const localPicturesAdded = !!localDraft.workflow?.pictures_added;
  if (localDraft.cover) {
    const serverCover = merged.cover || {};
    merged.cover = Object.assign({}, serverCover, localDraft.cover);
    ['cover_image', 'summary_image'].forEach(key => {
      if (localDraft.cover?.[key]) {
        // Local drafts intentionally omit heavy preview data URIs. Preserve the
        // server image contract so picture-review preview stays in parity with
        // the PDF after a browser/local-draft restore.
        merged.cover[key] = Object.assign({}, serverCover[key] || {}, localDraft.cover[key] || {});
        if (!merged.cover[key].data_uri && serverCover[key]?.data_uri) merged.cover[key].data_uri = serverCover[key].data_uri;
        if (!merged.cover[key].auto_data_uri && serverCover[key]?.auto_data_uri) merged.cover[key].auto_data_uri = serverCover[key].auto_data_uri;
        if (!merged.cover[key].options && serverCover[key]?.options) merged.cover[key].options = serverCover[key].options;
      }
    });
    if (!merged.cover.cover_background_data_uri && serverCover.cover_background_data_uri) {
      merged.cover.cover_background_data_uri = serverCover.cover_background_data_uri;
    }
  }
  if (localDraft.summary) merged.summary = JSON.parse(JSON.stringify(localDraft.summary));
  const localDays = Array.isArray(localDraft.days) ? localDraft.days : [];
  if (!Array.isArray(merged.days)) merged.days = [];
  localDays.forEach((localDay, idx) => {
    let targetDay = findServerDayForLocalDraft(merged.days, localDay, idx);
    if (!targetDay) {
      targetDay = {day: localDay.day || `Day ${idx + 1}`};
      merged.days.push(targetDay);
    }
    ['day','label','date','title','city','intro','blocks_html','blocks'].forEach(field => {
      if (field in localDay) targetDay[field] = localDay[field];
    });
    if (serverPicturesAdded && localPicturesAdded && localDay.image) {
      targetDay.image = Object.assign({}, targetDay.image || {}, localDay.image);
    }
  });
  if (localDraft.final_pages) merged.final_pages = JSON.parse(JSON.stringify(localDraft.final_pages));
  if (Array.isArray(localDraft.document_pages)) {
    merged.document_pages = JSON.parse(JSON.stringify(localDraft.document_pages));
  } else if (Array.isArray(localDraft.editor_draft?.document_pages)) {
    merged.document_pages = JSON.parse(JSON.stringify(localDraft.editor_draft.document_pages));
  }
  if (localDraft.editor_draft) merged.editor_draft = JSON.parse(JSON.stringify(localDraft.editor_draft));
  if (Array.isArray(localDraft.issue_flags)) merged.issue_flags = JSON.parse(JSON.stringify(localDraft.issue_flags));
  merged.workflow = JSON.parse(JSON.stringify(initialPayload?.workflow || {pictures_added: false}));
  // Server workflow state is authoritative. Browser-local drafts may restore
  // text edits, but they must never downgrade an app-level transition such as
  // text-only → picture review.
  if (serverPicturesAdded) {
    merged.workflow.pictures_added = true;
  }
  return merged;
}

function restoreLocalDraftIfAvailable() {
  if (!initialPayload) return false;
  try {
    const raw = localStorage.getItem(draftStorageKey());
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    if (!parsed || !parsed.model) return false;
    const currentSourceSignature = initialPayload?.meta?.source_signature || '';
    const savedSourceSignature = parsed.source_signature || parsed.model?.meta?.source_signature || '';
    if (currentSourceSignature && savedSourceSignature && currentSourceSignature !== savedSourceSignature) return false;
    const merged = mergeLocalDraftOntoServerPayload(parsed.model);
    const serverSnapshot = JSON.stringify(compactFullPayloadForCommit(initialPayload));
    const localSnapshot = JSON.stringify(compactFullPayloadForCommit(merged));
    if (serverSnapshot === localSnapshot) return false;
    model = merged;
    restoredLocalDraftPendingSave = true;
    restoredLocalDraftInfo = {saved_at: parsed.saved_at || 0, source_signature: savedSourceSignature};
    updateSaveState('recovered', {recovered: true, localDraftAt: parsed.saved_at || 0, message: 'Recovered browser draft'});
    return true;
  } catch (err) {
    return false;
  }
}

function clearLocalDraft() {
  try { localStorage.removeItem(draftStorageKey()); } catch (err) {}
}
