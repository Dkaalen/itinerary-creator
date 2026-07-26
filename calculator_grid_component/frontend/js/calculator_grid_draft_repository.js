// Current browser-draft persistence and restoration eligibility.

(() => {
  'use strict';

  const core = window.ItineraryCalculator.require('storage.core');

  function loadDraft() {
    try {
      const raw = window.localStorage.getItem(core.getDraftStorageKey());
      if (!raw) return null;
      const draft = JSON.parse(raw);
      if (!draft || !Array.isArray(draft.rows)) return null;
      if (Date.now() - Number(draft.savedAt || 0) > core.draftMaxAgeMs) {
        clearDraft();
        return null;
      }
      return draft;
    } catch (_error) {
      core.setWarning('draft', 'This browser could not read the local recovery copy. Calculator editing continues normally.');
      return null;
    }
  }

  function draftPayload(state, backendRevision) {
    return {
      schemaVersion: core.recoverySchemaVersion,
      rows: normalizeRowsForPython(state.rows),
      numberOfPax: state.numberOfPax ?? null,
      showAdvanced: Boolean(state.showAdvanced),
      selectedRowIndex: Number(state.selectedRowIndex || 0),
      activeCell: activeCell ? {...activeCell} : null,
      selection: state.selection ? {...state.selection} : null,
      columnWidths: {...(state.columnWidths || {})},
      backendRevision: String(backendRevision || ''),
      savedAt: Date.now(),
    };
  }

  function saveAfterPruningActiveRecovery(serialized) {
    const recovery = window.ItineraryCalculator.require('storage.recovery');
    let snapshots = recovery.loadSnapshots();
    while (snapshots.length) {
      snapshots = snapshots.slice(0, -1);
      try {
        if (snapshots.length) {
          window.localStorage.setItem(core.recoveryStorageKey(), recovery.encodeSnapshots(snapshots));
        } else {
          window.localStorage.removeItem(core.recoveryStorageKey());
        }
        if (calculatorState) calculatorState.recoverySnapshots = snapshots;
        if (typeof refreshVersionHistoryCount === 'function') refreshVersionHistoryCount();
        window.localStorage.setItem(core.getDraftStorageKey(), serialized);
        return true;
      } catch (error) {
        if (!core.errorIsQuota(error)) return false;
      }
    }
    recovery.clearStorageOnly();
    try {
      window.localStorage.setItem(core.getDraftStorageKey(), serialized);
      return true;
    } catch (_error) {
      return false;
    }
  }

  function saveDraft(state, backendRevision) {
    if (!state || !Array.isArray(state.rows)) return false;
    if (core.isLocalRecoveryPaused()) return true;
    const recovery = window.ItineraryCalculator.require('storage.recovery');
    const serialized = JSON.stringify(draftPayload(state, backendRevision));
    recovery.pruneForDraft(serialized);
    try {
      window.localStorage.setItem(core.getDraftStorageKey(), serialized);
      core.setWarning('draft', '');
      core.updateStorageUsage();
      return true;
    } catch (error) {
      if (core.errorIsQuota(error)) {
        const removed = core.pruneOtherNamespacesForQuota();
        if (removed) {
          try {
            window.localStorage.setItem(core.getDraftStorageKey(), serialized);
            core.setWarning('draft', '');
            core.setWarning('recovery', 'Older local recovery versions from inactive projects were removed to protect the current Calculator draft.');
            core.updateStorageUsage();
            return true;
          } catch (_retryError) {
            // Continue by pruning the active project's older versions.
          }
        }
        if (saveAfterPruningActiveRecovery(serialized)) {
          core.setWarning('draft', '');
          core.setWarning('recovery', 'Older local recovery versions were removed to protect the current Calculator draft.');
          core.updateStorageUsage();
          return true;
        }
      }
      core.setWarning('draft', 'This browser cannot store a local recovery copy right now. Calculator editing continues normally.');
      core.updateStorageUsage();
      return false;
    }
  }

  function clearDraft() {
    try {
      window.localStorage.removeItem(core.getDraftStorageKey());
      core.setWarning('draft', '');
    } catch (_error) {
      core.setWarning('draft', 'This browser cannot change local recovery storage right now. Calculator editing continues normally.');
    }
    core.updateStorageUsage();
  }

  function rowHasUserContent(row) {
    const ignored = new Set(['row_id', 'supplier_currency', 'sales_currency']);
    for (const [key, value] of Object.entries(row || {})) {
      if (ignored.has(key) || key.startsWith('_') || key.endsWith('_override')) continue;
      if (typeof value === 'boolean') {
        if (value) return true;
        continue;
      }
      if (value === null || value === undefined) continue;
      if (String(value).trim() !== '' && String(value).trim() !== '0') return true;
    }
    return false;
  }

  function gridRowsAreBlank(rows) {
    return (rows || []).every((row) => !rowHasUserContent(row));
  }

  function shouldRestoreDraft(draft, incomingRows, incomingRevision) {
    if (!draft || !Array.isArray(draft.rows) || !draft.rows.length) return false;
    const draftRevision = String(draft.backendRevision || '');
    const revisionsMatch = Boolean(draftRevision && incomingRevision && draftRevision === String(incomingRevision));
    if (!Array.isArray(incomingRows) || !incomingRows.length) return revisionsMatch || !incomingRevision;
    if (gridRowsAreBlank(incomingRows)) return revisionsMatch;
    return revisionsMatch;
  }

  window.ItineraryCalculator.define('storage.draft', {
    clearDraft,
    loadDraft,
    rowHasUserContent,
    saveDraft,
    shouldRestoreDraft,
  });
})();
