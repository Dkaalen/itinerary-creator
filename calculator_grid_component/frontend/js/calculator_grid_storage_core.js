// Browser-storage namespace, health, quota, and lifecycle primitives.

(() => {
  'use strict';

  let draftStorageKey = 'itineraryCalculatorBrowserDraft.v3.global';
  const DRAFT_STORAGE_PREFIX = 'itineraryCalculatorBrowserDraft.v3.';
  const DRAFT_MAX_AGE_MS = 1000 * 60 * 60 * 24 * 7;
  const RECOVERY_SCHEMA_VERSION = 4;
  const RECOVERY_MAX_SNAPSHOTS = 5;
  const RECOVERY_STORAGE_BUDGET_BYTES = 1250 * 1024;
  const DRAFT_MAX_BYTES = 900 * 1024;
  const GLOBAL_STORAGE_BUDGET_BYTES = 1536 * 1024;
  const MAX_STORED_NAMESPACES = 3;
  const storageWarnings = {draft: '', recovery: ''};
  let localRecoveryPaused = false;

  function recoveryStorageKey(baseKey = draftStorageKey) {
    return `${baseKey}.versions`;
  }

  function statusPayload() {
    const unavailable = Boolean(storageWarnings.draft);
    const reduced = !unavailable && Boolean(storageWarnings.recovery);
    if (unavailable) {
      return {state: 'unavailable', summary: 'Browser recovery paused', detail: storageWarnings.draft};
    }
    if (reduced) {
      return {state: 'reduced', summary: 'Local recovery reduced', detail: storageWarnings.recovery};
    }
    return {
      state: 'available',
      summary: 'Local recovery ready',
      detail: 'A small, bounded Calculator recovery draft can be stored in this browser.',
    };
  }

  function warningMessage() {
    const status = statusPayload();
    return status.state === 'available' ? '' : status.summary;
  }

  function setWarning(kind, message) {
    if (!(kind in storageWarnings)) return;
    const previous = JSON.stringify(statusPayload());
    storageWarnings[kind] = String(message || '');
    const currentStatus = statusPayload();
    const current = JSON.stringify(currentStatus);
    if (calculatorState) {
      calculatorState.recoveryStatus = currentStatus;
      calculatorState.recoveryWarning = currentStatus.state === 'available' ? '' : currentStatus.summary;
    }
    if (previous !== current && typeof refreshRecoveryStatusOnly === 'function') refreshRecoveryStatusOnly();
  }

  function recognizedDraftBaseKey(key) {
    const value = String(key || '');
    if (!value.startsWith(DRAFT_STORAGE_PREFIX)) return '';
    return value.endsWith('.versions') ? value.slice(0, -'.versions'.length) : value;
  }

  function storedNamespaceKeys() {
    const namespaces = new Set();
    try {
      for (let index = 0; index < window.localStorage.length; index += 1) {
        const baseKey = recognizedDraftBaseKey(window.localStorage.key(index));
        if (baseKey) namespaces.add(baseKey);
      }
    } catch (_error) {
      setWarning('draft', 'This browser cannot access local recovery storage right now. Calculator editing continues normally.');
    }
    return [...namespaces];
  }

  function storedDraftSavedAt(raw) {
    try {
      const parsed = JSON.parse(String(raw || ''));
      return Number(parsed?.savedAt || 0);
    } catch (_error) {
      return 0;
    }
  }

  function storedRecoverySavedAt(raw) {
    try {
      const parsed = JSON.parse(String(raw || ''));
      const entries = Array.isArray(parsed) ? parsed : parsed?.entries;
      if (!Array.isArray(entries)) return 0;
      return entries.reduce((latest, entry) => Math.max(latest, Number(entry?.savedAt || 0)), 0);
    } catch (_error) {
      return 0;
    }
  }

  function namespaceLastSavedAt(baseKey) {
    try {
      return Math.max(
        storedDraftSavedAt(window.localStorage.getItem(baseKey)),
        storedRecoverySavedAt(window.localStorage.getItem(recoveryStorageKey(baseKey)))
      );
    } catch (_error) {
      return 0;
    }
  }

  function cleanupObsoleteNamespaces(now = Date.now()) {
    const cutoff = Number(now || Date.now()) - DRAFT_MAX_AGE_MS;
    for (const baseKey of storedNamespaceKeys()) {
      if (baseKey === draftStorageKey) continue;
      const lastSavedAt = namespaceLastSavedAt(baseKey);
      if (!lastSavedAt || lastSavedAt >= cutoff) continue;
      try {
        window.localStorage.removeItem(baseKey);
        window.localStorage.removeItem(recoveryStorageKey(baseKey));
      } catch (_error) {
        setWarning('draft', 'This browser cannot change local recovery storage right now. Calculator editing continues normally.');
        return;
      }
    }
  }

  function setDraftStorageKey(key) {
    const value = String(key || '').trim();
    const nextKey = value || 'itineraryCalculatorBrowserDraft.v3.global';
    if (nextKey !== draftStorageKey) {
      storageWarnings.draft = '';
      storageWarnings.recovery = '';
      localRecoveryPaused = false;
    }
    draftStorageKey = nextKey;
    cleanupLegacyKeys();
    cleanupObsoleteNamespaces();
    pruneOtherNamespacesForQuota();
    return draftStorageKey;
  }

  function getDraftStorageKey() {
    return draftStorageKey;
  }

  function namespaceBytes(baseKey) {
    return utf8Bytes(storedValue(baseKey)) + utf8Bytes(storedValue(recoveryStorageKey(baseKey)));
  }

  function pruneOtherNamespacesForQuota() {
    const candidates = storedNamespaceKeys()
      .filter((baseKey) => baseKey !== draftStorageKey)
      .map((baseKey) => ({baseKey, savedAt: namespaceLastSavedAt(baseKey), bytes: namespaceBytes(baseKey)}))
      .sort((left, right) => left.savedAt - right.savedAt);
    let removed = 0;
    while (candidates.length && (storedNamespaceKeys().length > MAX_STORED_NAMESPACES || allCalculatorStorageBytes() > GLOBAL_STORAGE_BUDGET_BYTES)) {
      const candidate = candidates.shift();
      try {
        window.localStorage.removeItem(candidate.baseKey);
        window.localStorage.removeItem(recoveryStorageKey(candidate.baseKey));
        removed += 1;
      } catch (_error) {
        break;
      }
    }
    return removed;
  }

  function allCalculatorStorageBytes() {
    return storedNamespaceKeys().reduce((total, baseKey) => total + namespaceBytes(baseKey), 0);
  }

  function cleanupLegacyKeys() {
    const prefixes = [
      'itineraryCalculatorBrowserDraft.v1.',
      'itineraryCalculatorBrowserDraft.v2.',
      'itineraryCalculatorDraft.',
      'calculatorDraft.',
    ];
    try {
      const keys = [];
      for (let index = 0; index < window.localStorage.length; index += 1) keys.push(window.localStorage.key(index));
      for (const key of keys) {
        if (prefixes.some((prefix) => String(key || '').startsWith(prefix))) window.localStorage.removeItem(key);
      }
    } catch (_error) {
      // Startup guard and later quota recovery remain best-effort.
    }
  }


  function utf8Bytes(value) {
    const text = String(value || '');
    if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(text).length;
    return unescape(encodeURIComponent(text)).length;
  }

  function quotaBytes(key, value) {
    const text = `${String(key || '')}${String(value || '')}`;
    return Math.max(utf8Bytes(text), text.length * 2);
  }

  function storedValue(key) {
    try {
      return window.localStorage.getItem(key) || '';
    } catch (_error) {
      return '';
    }
  }

  function storageUsage(draftRaw = null, recoveryRaw = null) {
    const resolvedDraft = draftRaw === null ? storedValue(draftStorageKey) : String(draftRaw || '');
    const resolvedRecovery = recoveryRaw === null ? storedValue(recoveryStorageKey()) : String(recoveryRaw || '');
    const draftBytes = utf8Bytes(resolvedDraft);
    const recoveryBytes = utf8Bytes(resolvedRecovery);
    return {
      draftBytes,
      recoveryBytes,
      totalBytes: draftBytes + recoveryBytes,
      quotaBytes: quotaBytes(draftStorageKey, resolvedDraft) + quotaBytes(recoveryStorageKey(), resolvedRecovery),
    };
  }

  function formatStorageBytes(bytes) {
    const value = Math.max(0, Number(bytes || 0));
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(value < 10240 ? 1 : 0)} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  function errorIsQuota(error) {
    return Boolean(
      error
      && (
        error.name === 'QuotaExceededError'
        || error.name === 'NS_ERROR_DOM_QUOTA_REACHED'
        || Number(error.code) === 22
        || Number(error.code) === 1014
      )
    );
  }

  function updateStorageUsage() {
    if (calculatorState) calculatorState.recoveryStorageBytes = storageUsage().totalBytes;
  }

  function pauseLocalRecovery() {
    localRecoveryPaused = true;
  }

  function resumeLocalRecovery() {
    localRecoveryPaused = false;
  }

  window.ItineraryCalculator.define('storage.core', {
    allCalculatorStorageBytes,
    cleanupLegacyKeys,
    cleanupObsoleteNamespaces,
    draftMaxAgeMs: DRAFT_MAX_AGE_MS,
    draftMaxBytes: DRAFT_MAX_BYTES,
    globalStorageBudgetBytes: GLOBAL_STORAGE_BUDGET_BYTES,
    errorIsQuota,
    formatStorageBytes,
    getDraftStorageKey,
    isLocalRecoveryPaused: () => localRecoveryPaused,
    maxSnapshots: RECOVERY_MAX_SNAPSHOTS,
    maxStoredNamespaces: MAX_STORED_NAMESPACES,
    pauseLocalRecovery,
    pruneOtherNamespacesForQuota,
    recoverySchemaVersion: RECOVERY_SCHEMA_VERSION,
    recoveryStorageBudgetBytes: RECOVERY_STORAGE_BUDGET_BYTES,
    recoveryStorageKey,
    resumeLocalRecovery,
    setDraftStorageKey,
    setWarning,
    statusPayload,
    storageUsage,
    updateStorageUsage,
    utf8Bytes,
    warningMessage,
  });
})();
