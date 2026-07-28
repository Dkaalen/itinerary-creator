// Current IndexedDB-backed browser-draft persistence and restoration eligibility.

(() => {
  'use strict';

  const core = window.ItineraryCalculator.require('storage.core');

  function loadDraft() {
    try {
      const raw = core.readDraftRaw();
      if (!raw) return null;
      const draft = JSON.parse(raw);
      if (!draft || !Array.isArray(draft.rows)) return null;
      if (Date.now() - Number(draft.savedAt || 0) > core.draftMaxAgeMs()) {
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
      schemaVersion: core.recoverySchemaVersion(),
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

  function saveDraft(state, backendRevision) {
    if (!state || !Array.isArray(state.rows)) return false;
    const pauseReason = core.localRecoveryPauseReason();
    if (core.isLocalRecoveryPaused() && pauseReason !== 'size') return false;
    const recovery = window.ItineraryCalculator.require('storage.recovery');
    const serialized = JSON.stringify(draftPayload(state, backendRevision));
    if (core.utf8Bytes(serialized) > core.draftMaxBytes()) {
      core.pauseLocalRecovery('size');
      core.setWarning('draft', 'This Calculator draft is too large for browser recovery. Your current work remains open and can still be saved explicitly.');
      return false;
    }
    if (pauseReason === 'size' && !core.resumeSizeLimitedRecovery()) return false;
    recovery.pruneForDraft(serialized);
    core.pruneOtherNamespacesForQuota();
    if (!core.writeDraftRaw(serialized)) {
      core.pauseLocalRecovery('failure');
      core.setWarning('draft', 'Browser recovery storage is unavailable. Your current work remains open, but local recovery is paused.');
      core.updateStorageUsage();
      return false;
    }
    core.setWarning('draft', '');
    core.pruneOtherNamespacesForQuota();
    core.updateStorageUsage();
    return true;
  }

  function clearDraft() {
    if (core.removeDraftRaw()) {
      core.setWarning('draft', '');
    } else if (!core.isLocalRecoveryPaused()) {
      core.setWarning('draft', 'This browser cannot change local recovery storage right now. Calculator editing continues normally.');
    }
    core.updateStorageUsage();
  }

  function rowHasUserContent(row) {
    const ignored = new Set(['row_id', 'library_id', 'source_workbook', 'source_sheet', 'source_row', 'supplier_currency', 'sales_currency']);
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
