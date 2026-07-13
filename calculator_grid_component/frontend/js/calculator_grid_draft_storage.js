let calculatorDraftStorageKey = 'itineraryCalculatorBrowserDraft.v3.global';
const CALCULATOR_DRAFT_MAX_AGE_MS = 1000 * 60 * 60 * 24 * 30;

function setCalculatorDraftStorageKey(key) {
  const value = String(key || '').trim();
  calculatorDraftStorageKey = value || 'itineraryCalculatorBrowserDraft.v3.global';
  return calculatorDraftStorageKey;
}

function getCalculatorDraftStorageKey() {
  return calculatorDraftStorageKey;
}

function loadCalculatorDraft() {
  try {
    const raw = window.localStorage.getItem(calculatorDraftStorageKey);
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
    window.localStorage.setItem(calculatorDraftStorageKey, JSON.stringify({
      rows: normalizeRowsForPython(state.rows),
      numberOfPax: state.numberOfPax ?? null,
      showAdvanced: Boolean(state.showAdvanced),
      selectedRowIndex: Number(state.selectedRowIndex || 0),
      activeCell: activeCell ? {...activeCell} : null,
      selection: state.selection ? {...state.selection} : null,
      backendRevision: String(backendRevision || ''),
      savedAt: Date.now()
    }));
  } catch (_error) {
    // localStorage can be unavailable in private mode. The grid should still work.
  }
}

function clearCalculatorDraft() {
  try {
    window.localStorage.removeItem(calculatorDraftStorageKey);
  } catch (_error) {
    // No-op.
  }
}

function shouldRestoreCalculatorDraft(draft, incomingRows, incomingRevision) {
  if (!draft || !Array.isArray(draft.rows) || !draft.rows.length) return false;
  const draftRevision = String(draft.backendRevision || '');
  const revisionsMatch = Boolean(draftRevision && incomingRevision && draftRevision === String(incomingRevision));
  if (!Array.isArray(incomingRows) || !incomingRows.length) return revisionsMatch || !incomingRevision;
  if (gridRowsAreBlank(incomingRows)) return revisionsMatch;
  return revisionsMatch;
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
