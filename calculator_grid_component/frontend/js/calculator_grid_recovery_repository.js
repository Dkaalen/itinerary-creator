// Versioned recovery snapshots, delta encoding, retention, and restoration.

(() => {
  'use strict';

  const core = window.ItineraryCalculator.require('storage.core');

  function recoveryHash(value) {
    const text = String(value || '');
    let first = 0xdeadbeef ^ text.length;
    let second = 0x41c6ce57 ^ text.length;
    for (let index = 0; index < text.length; index += 1) {
      const code = text.charCodeAt(index);
      first = Math.imul(first ^ code, 2654435761);
      second = Math.imul(second ^ code, 1597334677);
    }
    first = Math.imul(first ^ (first >>> 16), 2246822507) ^ Math.imul(second ^ (second >>> 13), 3266489909);
    second = Math.imul(second ^ (second >>> 16), 2246822507) ^ Math.imul(first ^ (first >>> 13), 3266489909);
    return `${(second >>> 0).toString(16).padStart(8, '0')}${(first >>> 0).toString(16).padStart(8, '0')}`;
  }

  function comparable(snapshot) {
    return {
      rows: snapshot.rows,
      numberOfPax: snapshot.numberOfPax ?? null,
      showAdvanced: Boolean(snapshot.showAdvanced),
      columnWidths: {...(snapshot.columnWidths || {})},
    };
  }

  function snapshotFromState(state, backendRevision, reason) {
    const snapshot = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      rows: normalizeRowsForPython(state.rows),
      numberOfPax: state.numberOfPax ?? null,
      showAdvanced: Boolean(state.showAdvanced),
      selectedRowIndex: Number(state.selectedRowIndex || 0),
      activeCell: activeCell ? {...activeCell} : null,
      selection: state.selection ? {...state.selection} : null,
      columnWidths: {...(state.columnWidths || {})},
      backendRevision: String(backendRevision || ''),
      savedAt: Date.now(),
      reason: String(reason || 'edit'),
    };
    snapshot.hash = recoveryHash(JSON.stringify(comparable(snapshot)));
    return snapshot;
  }

  function snapshotLimit(snapshotBytes) {
    const size = Math.max(0, Number(snapshotBytes || 0));
    if (size <= 64 * 1024) return core.maxSnapshots;
    if (size <= 192 * 1024) return Math.min(core.maxSnapshots, 4);
    if (size <= 512 * 1024) return Math.min(core.maxSnapshots, 3);
    if (size <= 1024 * 1024) return Math.min(core.maxSnapshots, 2);
    return 1;
  }

  function rowsDelta(baseRows, targetRows) {
    const source = Array.isArray(baseRows) ? baseRows : [];
    const target = Array.isArray(targetRows) ? targetRows : [];
    const changes = [];
    for (let index = 0; index < target.length; index += 1) {
      const sourceRow = source[index];
      const targetRow = target[index];
      if (JSON.stringify(sourceRow) !== JSON.stringify(targetRow)) changes.push([index, targetRow]);
    }
    return {rowCount: target.length, rowChanges: changes};
  }

  function applyRowsDelta(baseRows, entry) {
    const rowCount = Math.max(0, Number(entry.rowCount || 0));
    const rows = cloneRows(baseRows).slice(0, rowCount);
    while (rows.length < rowCount) rows.push({});
    for (const change of entry.rowChanges || []) {
      if (!Array.isArray(change) || change.length !== 2) continue;
      const index = Number(change[0]);
      if (!Number.isInteger(index) || index < 0 || index >= rowCount) continue;
      rows[index] = {...(change[1] || {})};
    }
    return rows;
  }

  function metadata(snapshot) {
    return {
      id: String(snapshot.id || ''),
      numberOfPax: snapshot.numberOfPax ?? null,
      showAdvanced: Boolean(snapshot.showAdvanced),
      selectedRowIndex: Number(snapshot.selectedRowIndex || 0),
      activeCell: snapshot.activeCell ? {...snapshot.activeCell} : null,
      selection: snapshot.selection ? {...snapshot.selection} : null,
      columnWidths: {...(snapshot.columnWidths || {})},
      backendRevision: String(snapshot.backendRevision || ''),
      savedAt: Number(snapshot.savedAt || 0),
      reason: String(snapshot.reason || 'edit'),
      hash: String(snapshot.hash || recoveryHash(JSON.stringify(comparable(snapshot)))),
    };
  }

  function encodeSnapshots(snapshots) {
    const entries = [];
    let newerSnapshot = null;
    for (const snapshot of snapshots || []) {
      const base = metadata(snapshot);
      if (!newerSnapshot) {
        entries.push({...base, kind: 'full', rows: snapshot.rows});
        newerSnapshot = snapshot;
        continue;
      }
      const delta = rowsDelta(newerSnapshot.rows, snapshot.rows);
      const deltaEntry = {...base, kind: 'delta', ...delta};
      const fullEntry = {...base, kind: 'full', rows: snapshot.rows};
      entries.push(JSON.stringify(deltaEntry).length < JSON.stringify(fullEntry).length ? deltaEntry : fullEntry);
      newerSnapshot = snapshot;
    }
    return JSON.stringify({schemaVersion: core.recoverySchemaVersion, entries});
  }

  function decodePayload(parsed) {
    if (Array.isArray(parsed)) {
      return parsed.map((snapshot) => ({
        ...snapshot,
        rows: cloneRows(snapshot?.rows || []),
        hash: String(snapshot?.hash || recoveryHash(JSON.stringify(comparable(snapshot || {})))),
      }));
    }
    if (!parsed || Number(parsed.schemaVersion) !== core.recoverySchemaVersion || !Array.isArray(parsed.entries)) return [];
    const snapshots = [];
    let newerRows = [];
    for (const entry of parsed.entries) {
      if (!entry || !entry.id) continue;
      let rows;
      if (entry.kind === 'full' && Array.isArray(entry.rows)) rows = cloneRows(entry.rows);
      else if (entry.kind === 'delta' && snapshots.length) rows = applyRowsDelta(newerRows, entry);
      else continue;
      const snapshot = {...metadata({...entry, rows}), rows};
      snapshots.push(snapshot);
      newerRows = rows;
    }
    return snapshots;
  }

  function readSnapshots() {
    const raw = window.localStorage.getItem(core.recoveryStorageKey());
    if (!raw) return [];
    return decodePayload(JSON.parse(raw));
  }

  function loadSnapshots() {
    try {
      const cutoff = Date.now() - core.draftMaxAgeMs;
      return readSnapshots()
        .filter((snapshot) => snapshot && Array.isArray(snapshot.rows) && Number(snapshot.savedAt || 0) >= cutoff)
        .slice(0, core.maxSnapshots);
    } catch (_error) {
      core.setWarning('recovery', 'Recent local recovery versions could not be read and will be rebuilt from the current draft.');
      return [];
    }
  }

  function serializedWithinBudget(snapshots, draftRaw = null) {
    let retained = [...(snapshots || [])];
    let serialized = encodeSnapshots(retained);
    while (retained.length && core.storageUsage(draftRaw, serialized).quotaBytes > core.recoveryStorageBudgetBytes) {
      retained = retained.slice(0, -1);
      serialized = encodeSnapshots(retained);
    }
    return {snapshots: retained, serialized};
  }

  function clearStorageOnly() {
    try {
      window.localStorage.removeItem(core.recoveryStorageKey());
    } catch (_error) {
      // The visible warning is set by the caller.
    }
    if (calculatorState) calculatorState.recoverySnapshots = [];
    if (typeof refreshVersionHistoryCount === 'function') refreshVersionHistoryCount();
  }

  function writeSnapshots(snapshots, draftRaw = null) {
    let candidate = serializedWithinBudget(snapshots, draftRaw);
    while (candidate.snapshots.length) {
      try {
        window.localStorage.setItem(core.recoveryStorageKey(), candidate.serialized);
        core.setWarning('recovery', candidate.snapshots.length < snapshots.length
          ? 'Older local recovery versions were removed to stay within browser storage limits.'
          : '');
        core.updateStorageUsage();
        return candidate.snapshots;
      } catch (error) {
        if (!core.errorIsQuota(error)) break;
        candidate = serializedWithinBudget(candidate.snapshots.slice(0, -1), draftRaw);
      }
    }
    clearStorageOnly();
    core.setWarning('recovery', 'Older local recovery versions could not be kept. The current Calculator draft remains the priority.');
    core.updateStorageUsage();
    return [];
  }

  function pruneForDraft(draftRaw) {
    const snapshots = loadSnapshots();
    if (!snapshots.length) return;
    const candidate = serializedWithinBudget(snapshots, draftRaw);
    if (candidate.snapshots.length === snapshots.length) return;
    const retained = writeSnapshots(candidate.snapshots, draftRaw);
    if (retained.length < snapshots.length) {
      core.setWarning('recovery', 'Older local recovery versions were removed to protect the current Calculator draft.');
    }
  }

  function saveSnapshot(state, backendRevision, reason = 'edit') {
    if (!state || !Array.isArray(state.rows) || core.isLocalRecoveryPaused()) return [];
    const snapshots = loadSnapshots();
    const snapshot = snapshotFromState(state, backendRevision, reason);
    if (snapshots[0]?.hash === snapshot.hash) return snapshots;
    const retentionLimit = snapshotLimit(core.utf8Bytes(JSON.stringify(snapshot)));
    return writeSnapshots([snapshot, ...snapshots].slice(0, retentionLimit));
  }

  function restoreSnapshot(snapshotId) {
    const snapshot = loadSnapshots().find((item) => item.id === snapshotId);
    if (!snapshot || !calculatorState) return false;
    recordHistory();
    calculatorState.rows = calculateRows(cloneRows(snapshot.rows), calculatorState.currencyRates);
    calculatorState.numberOfPax = snapshot.numberOfPax ?? null;
    calculatorState.showAdvanced = Boolean(snapshot.showAdvanced);
    calculatorState.selectedRowIndex = Number(snapshot.selectedRowIndex || 0);
    calculatorState.selection = snapshot.selection ? {...snapshot.selection} : null;
    calculatorState.columnWidths = {...(snapshot.columnWidths || {})};
    activeCell = snapshot.activeCell ? {...snapshot.activeCell} : null;
    calculatorState.dirty = true;
    calculatorState.syncStatus = `Recovered version from ${new Date(snapshot.savedAt).toLocaleString()}`;
    calculatorState.showVersionHistory = false;
    calculatorState.recoverySnapshots = saveSnapshot(calculatorState, activeBackendRevision, 'restored');
    hasLocalDraft = true;
    validateCalculatorState(calculatorState);
    window.ItineraryCalculator.require('storage.draft').saveDraft(calculatorState, activeBackendRevision);
    rerender();
    return true;
  }

  function cancelPendingWrites({includeDraft = false} = {}) {
    if (includeDraft && typeof localDraftSaveTimer !== 'undefined') {
      window.clearTimeout(localDraftSaveTimer);
      localDraftSaveTimer = null;
    }
    if (typeof recoverySnapshotTimer !== 'undefined') {
      window.clearTimeout(recoverySnapshotTimer);
      recoverySnapshotTimer = null;
    }
  }

  function clearSnapshots() {
    cancelPendingWrites();
    clearStorageOnly();
    core.setWarning('recovery', '');
    if (calculatorState) calculatorState.recoverySnapshots = [];
    core.updateStorageUsage();
  }

  function clearLocalRecoveryData() {
    cancelPendingWrites({includeDraft: true});
    try {
      window.localStorage.removeItem(core.getDraftStorageKey());
      window.localStorage.removeItem(core.recoveryStorageKey());
      core.setWarning('draft', '');
      core.setWarning('recovery', '');
      core.pauseLocalRecovery();
      if (calculatorState) {
        calculatorState.recoverySnapshots = [];
        calculatorState.recoveryStatus = core.statusPayload();
        calculatorState.recoveryWarning = '';
      }
      core.updateStorageUsage();
      return true;
    } catch (_error) {
      core.setWarning('draft', 'This browser cannot change local recovery storage right now. Calculator editing continues normally.');
      core.updateStorageUsage();
      return false;
    }
  }

  window.ItineraryCalculator.define('storage.recovery', {
    cancelPendingWrites,
    clearLocalRecoveryData,
    clearSnapshots,
    clearStorageOnly,
    decodePayload,
    encodeSnapshots,
    loadSnapshots,
    pruneForDraft,
    restoreSnapshot,
    saveSnapshot,
  });
})();
