/** Browser-local editor draft serialization, restoration, and merge behavior. */
const LOCAL_DRAFT_SAVE_MODE_DELTA = 'local_delta';
const LOCAL_DRAFT_SAVE_MODE_SNAPSHOT = 'local_snapshot';
let lastLocalDraftStoragePayload = '';

function localDraftStorage() {
  return ItineraryVisualEditor.require('draftStorage');
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

function localDraftTouchedKeys() {
  return Array.from(touchedKeys || []).map(key => String(key || '')).filter(Boolean).sort();
}

function attachLocalDraftIdentity(payload, saveMode) {
  payload.draft_id = model?.draft_id || initialPayload?.draft_id || '';
  payload.meta = Object.assign({}, initialPayload?.meta || {}, model?.meta || {});
  payload.workflow = Object.assign({}, initialPayload?.workflow || {}, model?.workflow || {});
  payload.save_mode = saveMode;
  payload.local_draft_touched_keys = localDraftTouchedKeys();
  return payload;
}

function buildLocalDraftDeltaPayload() {
  if (typeof collectTouched === 'function') collectTouched();
  const payload = stripUploadBinaryForLocalDraft(pruneForSave(model));
  return attachLocalDraftIdentity(payload, LOCAL_DRAFT_SAVE_MODE_DELTA);
}

function buildLocalDraftSnapshotPayload() {
  if (typeof collect === 'function') collect();
  const payload = stripUploadBinaryForLocalDraft(compactFullPayloadForCommit(model));
  return attachLocalDraftIdentity(payload, LOCAL_DRAFT_SAVE_MODE_SNAPSHOT);
}

function buildLocalDraftPayload(options = {}) {
  return options?.fullSnapshot ? buildLocalDraftSnapshotPayload() : buildLocalDraftDeltaPayload();
}

function persistLocalDraft(options = {}) {
  if (localDraftTimer) {
    clearTimeout(localDraftTimer);
    localDraftTimer = null;
  }
  if (!model || !initialPayload) return;
  const storage = localDraftStorage();
  const pauseReason = storage.pauseReason();
  if (storage.isPaused() && pauseReason !== 'size') return;
  if (!options?.fullSnapshot && (!touchedKeys || !touchedKeys.size)) return;
  try {
    const snapshot = buildLocalDraftPayload(options);
    const saveMode = snapshot.save_mode || (options?.fullSnapshot ? LOCAL_DRAFT_SAVE_MODE_SNAPSHOT : LOCAL_DRAFT_SAVE_MODE_DELTA);
    const storageBody = {
      source_signature: initialPayload?.meta?.source_signature || '',
      draft_schema_version: initialPayload?.meta?.draft_schema_version || 1,
      save_mode: saveMode,
      model: snapshot
    };
    const stableStoragePayload = JSON.stringify(storageBody);
    if (!options?.fullSnapshot && stableStoragePayload === lastLocalDraftStoragePayload) return;
    const serialized = JSON.stringify(Object.assign({saved_at: Date.now()}, storageBody));
    if (storage.bytes(serialized) > storage.maxDraftBytes()) {
      storage.pause('size');
      return;
    }
    if (pauseReason === 'size' && !storage.resumeAfterSize()) return;
    storage.prune();
    if (!storage.write(serialized)) {
      storage.pause('failure');
      return;
    }
    storage.prune();
    lastLocalDraftStoragePayload = stableStoragePayload;
    const localDraftAt = Date.now();
    if (pauseReason === 'size') {
      updateSaveState('dirty', {localRecoveryAvailable: true, message: '', localDraftAt});
    } else {
      saveState.localRecoveryAvailable = true;
      saveState.message = '';
      saveState.localDraftAt = localDraftAt;
    }
  } catch (_error) {
    storage.pause('failure');
  }
}

function scheduleLocalDraftPersist(delayMs = LOCAL_DRAFT_SAVE_DELAY_MS, options = {}) {
  if (localDraftTimer) clearTimeout(localDraftTimer);
  localDraftTimer = setTimeout(() => {
    localDraftTimer = null;
    persistLocalDraft(options);
  }, Math.max(0, Number(delayMs) || 0));
}

function sameDraftDay(a, b, fallbackIndex) {
  const left = String(a?.day || a?.day_id || a?.label || fallbackIndex || '').trim();
  const right = String(b?.day || b?.day_id || b?.label || fallbackIndex || '').trim();
  return left && right && left === right;
}

function findServerDayForLocalDraft(mergedDays, localDay, fallbackIndex) {
  if (!Array.isArray(mergedDays)) return null;
  const byIdentity = mergedDays.find(day => sameDraftDay(day, localDay, fallbackIndex));
  if (byIdentity) return byIdentity;
  return mergedDays[fallbackIndex] || null;
}

function mergeDraftImageOntoServer(serverImage, localImage) {
  const merged = Object.assign({}, serverImage || {}, localImage || {});
  if (!merged.data_uri && serverImage?.data_uri) merged.data_uri = serverImage.data_uri;
  if (!merged.auto_data_uri && serverImage?.auto_data_uri) merged.auto_data_uri = serverImage.auto_data_uri;
  if (!merged.options && serverImage?.options) merged.options = serverImage.options;
  return merged;
}

function mergeTopLevelObjectFields(target, source) {
  if (!source || typeof source !== 'object') return;
  Object.keys(source).forEach(key => {
    target[key] = JSON.parse(JSON.stringify(source[key]));
  });
}

function localDraftHasFields(value) {
  return value && typeof value === 'object' && Object.keys(value).length > 0;
}

function mergeFinalPagesForLocalDraft(merged, localDraft, isSnapshot) {
  const localFinalPages = localDraft.final_pages || {};
  if (!localDraftHasFields(localFinalPages)) return;
  if (isSnapshot) {
    merged.final_pages = JSON.parse(JSON.stringify(localFinalPages));
    return;
  }
  if (!merged.final_pages || typeof merged.final_pages !== 'object') merged.final_pages = {};
  Object.keys(localFinalPages).forEach(key => {
    merged.final_pages[key] = JSON.parse(JSON.stringify(localFinalPages[key]));
  });
}

function mergeEditorDraftForLocalDraft(merged, localDraft, isSnapshot) {
  if (isSnapshot && localDraft.editor_draft) {
    merged.editor_draft = JSON.parse(JSON.stringify(localDraft.editor_draft));
    return;
  }
  if (typeof buildEditableDraftFromPayload === 'function') {
    merged.editor_draft = buildEditableDraftFromPayload(merged);
  }
}


function localDraftDayIdentity(day, index) {
  const identity = String(day?.day || day?.day_id || day?.label || '').trim();
  return identity || `Day ${index + 1}`;
}

function localDraftEditorSlug(value) {
  if (typeof editorSlug === 'function') return editorSlug(value);
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'page';
}

function localDraftDayPageId(day, index) {
  if (typeof canonicalPageIdForDay === 'function') return canonicalPageIdForDay(day || {}, index);
  return `day-${localDraftEditorSlug(localDraftDayIdentity(day || {}, index))}`;
}

function cloneLocalDraftValue(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function pageMatchesLocalDraftDay(page, dayIdentity, pageId) {
  if (!page || page.page_type !== 'generated_day') return false;
  if (String(page?.page_id || '') === pageId) return true;
  return String(page?.source_day_id || '').trim() === dayIdentity;
}

function generatedDayPageForLocalDraft(serverPages, localPages, day, index) {
  const dayIdentity = localDraftDayIdentity(day || {}, index);
  const pageId = localDraftDayPageId(day || {}, index);
  const serverPage = (serverPages || []).find(page => pageMatchesLocalDraftDay(page, dayIdentity, pageId)) || {};
  const localPage = (localPages || []).find(page => pageMatchesLocalDraftDay(page, dayIdentity, pageId)) || {};
  const page = Object.assign({}, cloneLocalDraftValue(serverPage));
  ['is_hidden', 'style_overrides', 'page_overrides', 'validation_status'].forEach(key => {
    if (Object.prototype.hasOwnProperty.call(localPage, key)) page[key] = cloneLocalDraftValue(localPage[key]);
  });
  page.page_id = pageId;
  page.page_type = 'generated_day';
  page.title = String(serverPage.title || localPage.title || day?.title || dayIdentity);
  page.source_day_id = dayIdentity;
  page.sort_order = index + 3;
  page.page_actions = Object.assign(
    {hide: true, restore: true, move: false, duplicate: false, reset: true},
    page.page_actions || {},
    {move: false, duplicate: false}
  );
  return page;
}

function normaliseDocumentPagesForLocalDraftMerge(mergedPayload, localDocumentPages) {
  const serverPages = Array.isArray(mergedPayload?.document_pages) ? mergedPayload.document_pages : [];
  const localPages = Array.isArray(localDocumentPages) ? localDocumentPages : [];
  if (!serverPages.length && !localPages.length) return [];

  const byId = new Map();
  serverPages.forEach(page => {
    const pageId = String(page?.page_id || '').trim();
    if (pageId) byId.set(pageId, cloneLocalDraftValue(page));
  });
  localPages.forEach(page => {
    const pageId = String(page?.page_id || '').trim();
    if (!pageId || page?.page_type === 'generated_day') return;
    byId.set(pageId, Object.assign({}, byId.get(pageId) || {}, cloneLocalDraftValue(page)));
  });

  (Array.isArray(mergedPayload?.days) ? mergedPayload.days : []).forEach((day, index) => {
    const page = generatedDayPageForLocalDraft(serverPages, localPages, day || {}, index);
    byId.set(page.page_id, page);
  });

  return Array.from(byId.values()).sort((a, b) => Number(a?.sort_order || 0) - Number(b?.sort_order || 0));
}

function mergeLocalDraftOntoServerPayload(localDraft) {
  const merged = JSON.parse(JSON.stringify(initialPayload || {}));
  const saveMode = String(localDraft?.save_mode || '').trim();
  const isSnapshot = saveMode !== LOCAL_DRAFT_SAVE_MODE_DELTA;
  const serverPicturesAdded = !!initialPayload?.workflow?.pictures_added;
  const localPicturesAdded = !!localDraft.workflow?.pictures_added;
  if (localDraft.cover) {
    if (!merged.cover || typeof merged.cover !== 'object') merged.cover = {};
    const serverCover = merged.cover || {};
    Object.keys(localDraft.cover).forEach(key => {
      if (key === 'cover_image' || key === 'summary_image') {
        merged.cover[key] = mergeDraftImageOntoServer(serverCover[key] || {}, localDraft.cover[key] || {});
      } else {
        merged.cover[key] = JSON.parse(JSON.stringify(localDraft.cover[key]));
      }
    });
    if (!merged.cover.cover_background_data_uri && serverCover.cover_background_data_uri) {
      merged.cover.cover_background_data_uri = serverCover.cover_background_data_uri;
    }
  }
  if (localDraft.summary) {
    if (!merged.summary || typeof merged.summary !== 'object') merged.summary = {};
    if (isSnapshot) merged.summary = JSON.parse(JSON.stringify(localDraft.summary));
    else mergeTopLevelObjectFields(merged.summary, localDraft.summary);
  }
  const localDays = Array.isArray(localDraft.days) ? localDraft.days : [];
  if (!Array.isArray(merged.days)) merged.days = [];
  localDays.forEach((localDay, idx) => {
    let targetDay = findServerDayForLocalDraft(merged.days, localDay, idx);
    if (!targetDay) {
      targetDay = {day: localDay.day || localDay.day_id || `Day ${idx + 1}`};
      merged.days.push(targetDay);
    }
    ['day','day_id','label','date','title','city','intro','blocks_html','blocks','intro_generated_value','intro_generator_version','intro_source_signature','intro_manual_override','blocks_html_generated_value','blocks_html_generator_version','blocks_manual_override'].forEach(field => {
      if (field in localDay) targetDay[field] = JSON.parse(JSON.stringify(localDay[field]));
    });
    if (serverPicturesAdded && localPicturesAdded && localDay.image) {
      targetDay.image = mergeDraftImageOntoServer(targetDay.image || {}, localDay.image);
    }
  });
  mergeFinalPagesForLocalDraft(merged, localDraft, isSnapshot);
  if (Array.isArray(localDraft.document_pages)) {
    merged.document_pages = normaliseDocumentPagesForLocalDraftMerge(merged, localDraft.document_pages);
  } else if (isSnapshot && Array.isArray(localDraft.editor_draft?.document_pages)) {
    merged.document_pages = normaliseDocumentPagesForLocalDraftMerge(merged, localDraft.editor_draft.document_pages);
  } else if (Array.isArray(merged.document_pages)) {
    merged.document_pages = normaliseDocumentPagesForLocalDraftMerge(merged, []);
  }
  mergeEditorDraftForLocalDraft(merged, localDraft, isSnapshot);
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
    const raw = localDraftStorage().read();
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
  lastLocalDraftStoragePayload = '';
  localDraftStorage().remove();
}


ItineraryVisualEditor.define('drafts', {
  clear: clearLocalDraft,
  flush: () => localDraftStorage().flush(),
  persist: persistLocalDraft,
  prepare: (payload) => localDraftStorage().prepare(payload),
  read: () => localDraftStorage().read(),
  restore: restoreLocalDraftIfAvailable,
});
