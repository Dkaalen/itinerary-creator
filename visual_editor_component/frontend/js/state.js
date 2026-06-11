let initialPayload = null;
let model = null;
let uploadedImages = {};
let touchedKeys = new Set();
let lastCommitNonce = null;
let lastSavedPayload = '';
// Browser-local autosave is immediate; server-side autosave is debounced and quiet.
let activeEditKey = null;
let undoStack = [];
let restoredLocalDraftPendingSave = false;
let serverAutosaveTimer = null;
let serverAutosaveInFlight = false;
let lastServerAutosavePayload = "";
let lastServerAutosaveAt = 0;
const SERVER_AUTOSAVE_DELAY_MS = 12000;
const SERVER_AUTOSAVE_MIN_INTERVAL_MS = 9000;
const WARNING_PATTERNS = [
  /\bPls\b/i, /\bplz\b/i, /\baddon cost\b/i, /\bpaid on ground\b/i,
  /\btranfers\b/i, /\bDate dependant\b/i, /\bFight\s*:/i,
  /\bPrivate Hotel to\b/i, /\bPrivate Airport to\b/i, /\bPrivate Station to\b/i,
  /\bself Transfer\b/, /\blevi Bus Station\b/, /\brovaniemi Bus Station\b/
];
function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));
}
function escAttr(s) {
  return esc(s).replace(/'/g, '&#39;');
}
function focusPos(focus) {
  if (focus === 'bottom') return 'center 78%';
  if (focus === 'center') return 'center center';
  return 'center 22%';
}
function picturesAdded() {
  return !!model?.workflow?.pictures_added;
}
function draftStorageKey() {
  const fallback = [initialPayload?.cover?.trip_title || '', initialPayload?.cover?.trip_dates || '', (initialPayload?.days || []).length].join('|');
  return `itinerary-visual-editor-draft:${initialPayload?.draft_id || fallback}`;
}
function persistLocalDraft() {
  if (!model || !initialPayload) return;
  try {
    const snapshot = attachEditableDraft(compactFullPayloadForCommit(model));
    localStorage.setItem(draftStorageKey(), JSON.stringify({
      saved_at: Date.now(),
      source_signature: initialPayload?.meta?.source_signature || '',
      draft_schema_version: initialPayload?.meta?.draft_schema_version || 1,
      model: snapshot
    }));
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
    return true;
  } catch (err) {
    return false;
  }
}
function clearLocalDraft() {
  try { localStorage.removeItem(draftStorageKey()); } catch (err) {}
}
function editableText(value, key, cls='') {
  return `<div class="${cls} editable-inline" contenteditable="true" data-edit-key="${esc(key)}">${esc(value)}</div>`;
}
function editableSpan(value, key, cls='') {
  return `<span class="${cls} editable-inline" contenteditable="true" data-edit-key="${esc(key)}">${esc(value)}</span>`;
}
function editableHtml(value, key, cls='') {
  return `<div class="${cls}" contenteditable="true" data-edit-key="${esc(key)}">${value || ''}</div>`;
}
function splitRouteParts(value) {
  return String(value || '').replace(/\s*\n+\s*/g, ' · ').split('·').map(p => p.trim()).filter(Boolean);
}
function routeHtml(value) {
  const parts = splitRouteParts(value);
  if (parts.length < 5) return esc(parts.join(' · '));
  const first = parts.slice(0, -2).map(esc).join(' · ');
  const pair = `<span class="cover-destination-pair">${esc(parts[parts.length - 2])}&nbsp;·&nbsp;${esc(parts[parts.length - 1])}</span>`;
  return `<span class="cover-route-line">${first}</span><span class="cover-route-line">${pair}</span>`;
}
function editableRoute(value, key, cls='') {
  return `<div class="${cls} editable-inline" contenteditable="true" data-edit-key="${esc(key)}">${routeHtml(value)}</div>`;
}
