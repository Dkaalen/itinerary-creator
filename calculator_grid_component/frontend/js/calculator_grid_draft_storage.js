const CALCULATOR_DRAFT_STORAGE_KEY = 'itineraryCalculatorBrowserDraft.v2';
const CALCULATOR_DRAFT_MAX_AGE_MS = 1000 * 60 * 60 * 24 * 30;

function loadCalculatorDraft() {
  try {
    const raw = window.localStorage.getItem(CALCULATOR_DRAFT_STORAGE_KEY);
    if (!raw) return null;
    const draft = JSON.parse(raw);
    if (!draft || !Array.isArray(draft.rows)) return null;
    if (Date.now() - Number(draft.savedAt || 0) > CALCULATOR_DRAFT_MAX_AGE_MS) {
      clearCalculatorDraft();
      return null;
    }
    return draft;
  } catch (_error) {
    return null;
  }
}

function saveCalculatorDraft(state, backendRevision) {
  if (!state || !Array.isArray(state.rows)) return;
  try {
    window.localStorage.setItem(CALCULATOR_DRAFT_STORAGE_KEY, JSON.stringify({
      rows: normalizeRowsForPython(state.rows),
      showAdvanced: Boolean(state.showAdvanced),
      selectedRowIndex: Number(state.selectedRowIndex || 0),
      backendRevision: String(backendRevision || ''),
      savedAt: Date.now()
    }));
  } catch (_error) {
    // localStorage can be unavailable in private mode. The grid should still work.
  }
}

function clearCalculatorDraft() {
  try {
    window.localStorage.removeItem(CALCULATOR_DRAFT_STORAGE_KEY);
  } catch (_error) {
    // No-op.
  }
}

function shouldRestoreCalculatorDraft(draft, incomingRows, incomingRevision) {
  if (!draft || !Array.isArray(draft.rows) || !draft.rows.length) return false;
  if (!Array.isArray(incomingRows) || !incomingRows.length) return true;
  if (gridRowsAreBlank(incomingRows)) return true;
  const draftRevision = String(draft.backendRevision || '');
  return Boolean(draftRevision && incomingRevision && draftRevision === String(incomingRevision));
}

function gridRowsAreBlank(rows) {
  return (rows || []).every((row) => !rowHasUserContent(row));
}


function rowHasUserContent(row) {
  const ignored = new Set(['row_id', 'supplier_currency', 'sales_currency']);
  for (const [key, value] of Object.entries(row || {})) {
    if (ignored.has(key) || key.endsWith('_override')) continue;
    if (typeof value === 'boolean') {
      if (value) return true;
      continue;
    }
    if (value === null || value === undefined) continue;
    if (String(value).trim() !== '' && String(value).trim() !== '0') return true;
  }
  return false;
}
