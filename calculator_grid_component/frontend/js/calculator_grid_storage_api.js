// Stable public browser-recovery API assembled from explicit storage modules.

(() => {
  'use strict';

  const core = window.ItineraryCalculator.require('storage.core');
  const draft = window.ItineraryCalculator.require('storage.draft');
  const recovery = window.ItineraryCalculator.require('storage.recovery');

  window.ItineraryCalculator.publish('storage', {
    clearDraft: draft.clearDraft,
    clearLocalRecoveryData: recovery.clearLocalRecoveryData,
    clearRecoverySnapshots: recovery.clearSnapshots,
    formatBytes: core.formatStorageBytes,
    debugRecords: core.debugRecords,
    flushWrites: core.flushWrites,
    getDraftStorageKey: core.getDraftStorageKey,
    initializeStorage: core.initializeStorage,
    loadDraft: draft.loadDraft,
    readDraftRaw: core.readDraftRaw,
    readRecoveryRaw: core.readRecoveryRaw,
    loadRecoverySnapshots: recovery.loadSnapshots,
    recoveryStorageKey: core.recoveryStorageKey,
    restoreRecoverySnapshot: recovery.restoreSnapshot,
    resumeLocalRecovery: core.resumeLocalRecovery,
    rowHasUserContent: draft.rowHasUserContent,
    saveDraft: draft.saveDraft,
    saveRecoverySnapshot: recovery.saveSnapshot,
    setDraftStorageKey: core.setDraftStorageKey,
    shouldRestoreDraft: draft.shouldRestoreDraft,
    statusPayload: core.statusPayload,
    storageUsage: core.storageUsage,
    warningMessage: core.warningMessage,
  });
})();
