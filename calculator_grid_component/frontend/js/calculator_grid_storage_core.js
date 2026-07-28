// IndexedDB-backed browser-recovery namespace, health, quota, and lifecycle primitives.

(() => {
  'use strict';

  const OWNER = 'calculator';
  const KIND_DRAFT = 'draft';
  const KIND_RECOVERY = 'recovery';
  let draftStorageKey = '';
  let storageContract = null;
  let ownerContract = null;
  let database = null;
  let storageReady = false;
  let storageInitialization = null;
  let writeQueue = Promise.resolve();
  const records = new Map();
  const storageWarnings = {draft: '', recovery: ''};
  let localRecoveryPaused = false;
  let localRecoveryPauseReason = '';

  function ownerSetting(name, fallback = 0) {
    const value = ownerContract?.[name];
    return value === undefined || value === null ? fallback : value;
  }

  function currentPrefix() {
    return String(ownerSetting('current_prefix', ''));
  }

  function recoverySuffix() {
    return String(ownerSetting('recovery_suffix', '.versions'));
  }

  function recoveryStorageKey(baseKey = draftStorageKey) {
    return `${String(baseKey || '')}${recoverySuffix()}`;
  }

  function statusPayload() {
    const unavailable = Boolean(storageWarnings.draft);
    const reduced = !unavailable && Boolean(storageWarnings.recovery);
    if (unavailable) {
      return {state: 'unavailable', summary: 'Local recovery unavailable', detail: storageWarnings.draft};
    }
    if (reduced) {
      return {state: 'reduced', summary: 'Local recovery reduced', detail: storageWarnings.recovery};
    }
    return {
      state: 'available',
      summary: 'Local recovery ready',
      detail: 'Calculator recovery is stored in a small, bounded browser database.',
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

  function pauseForStorageFailure(message) {
    localRecoveryPaused = true;
    localRecoveryPauseReason = 'failure';
    setWarning('draft', message || 'Browser recovery storage is unavailable. Your current work remains open, but local recovery is paused.');
  }

  function requestResult(request) {
    return new Promise((resolve, reject) => {
      request.addEventListener('success', () => resolve(request.result), {once: true});
      request.addEventListener('error', () => reject(request.error || new Error('IndexedDB request failed')), {once: true});
    });
  }

  function transactionDone(transaction) {
    return new Promise((resolve, reject) => {
      transaction.addEventListener('complete', resolve, {once: true});
      transaction.addEventListener('abort', () => reject(transaction.error || new Error('IndexedDB transaction aborted')), {once: true});
      transaction.addEventListener('error', () => reject(transaction.error || new Error('IndexedDB transaction failed')), {once: true});
    });
  }

  async function openDatabase(contract) {
    const indexedDb = window.indexedDB;
    if (!indexedDb) throw new Error('IndexedDB is unavailable');
    const dbContract = contract?.indexed_db || {};
    const name = String(dbContract.name || '');
    const storeName = String(dbContract.store || '');
    const version = Number(dbContract.version || 0);
    if (!name || !storeName || !Number.isInteger(version) || version < 1) throw new Error('Browser storage contract is invalid');
    const request = indexedDb.open(name, version);
    request.addEventListener('upgradeneeded', () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(storeName)) db.createObjectStore(storeName, {keyPath: 'id'});
    });
    return requestResult(request);
  }

  function storeName() {
    return String(storageContract?.indexed_db?.store || '');
  }

  function recordId(namespace, kind) {
    return `${OWNER}|${String(namespace || '')}|${String(kind || '')}`;
  }

  function recordFor(namespace, kind, payload) {
    const raw = String(payload || '');
    return {
      id: recordId(namespace, kind),
      owner: OWNER,
      namespace: String(namespace || ''),
      kind: String(kind || ''),
      payload: raw,
      savedAt: kind === KIND_RECOVERY ? storedRecoverySavedAt(raw) : storedDraftSavedAt(raw),
      bytes: utf8Bytes(raw),
      updatedAt: Date.now(),
    };
  }

  async function loadOwnerRecords() {
    const transaction = database.transaction(storeName(), 'readonly');
    const done = transactionDone(transaction);
    const all = await requestResult(transaction.objectStore(storeName()).getAll());
    await done;
    records.clear();
    for (const record of all || []) {
      if (record?.owner !== OWNER || !record?.id) continue;
      records.set(String(record.id), record);
    }
  }

  async function putRecordImmediately(record) {
    const transaction = database.transaction(storeName(), 'readwrite');
    transaction.objectStore(storeName()).put(record);
    await transactionDone(transaction);
  }

  async function deleteRecordImmediately(id) {
    const transaction = database.transaction(storeName(), 'readwrite');
    transaction.objectStore(storeName()).delete(String(id));
    await transactionDone(transaction);
  }

  async function reconcileOwnerRecordsAfterFailure() {
    try {
      await loadOwnerRecords();
    } catch (_error) {
      records.clear();
    }
  }

  function queueWrite(operation, warningKind = 'draft') {
    writeQueue = writeQueue.then(() => {
      if (localRecoveryPauseReason === 'failure') return false;
      return operation();
    }).catch(async (_error) => {
      pauseForStorageFailure('Browser recovery storage is unavailable. Your current work remains open, but local recovery is paused.');
      await reconcileOwnerRecordsAfterFailure();
      setWarning(warningKind, warningKind === 'recovery'
        ? 'Recent local recovery versions could not be stored. The current Calculator remains open.'
        : storageWarnings.draft);
      updateStorageUsage();
      return false;
    });
    return writeQueue;
  }

  function rawFor(namespace, kind) {
    return String(records.get(recordId(namespace, kind))?.payload || '');
  }

  function writeRaw(namespace, kind, payload) {
    if (!storageReady || localRecoveryPaused || !database) return false;
    const record = recordFor(namespace, kind, payload);
    records.set(record.id, record);
    queueWrite(() => putRecordImmediately(record), kind === KIND_RECOVERY ? 'recovery' : 'draft');
    return true;
  }

  function removeRaw(namespace, kind) {
    if (!storageReady || !database) return false;
    const id = recordId(namespace, kind);
    records.delete(id);
    queueWrite(() => deleteRecordImmediately(id), kind === KIND_RECOVERY ? 'recovery' : 'draft');
    return true;
  }

  function storedNamespaceKeys() {
    const namespaces = new Set();
    for (const record of records.values()) {
      if (record?.owner === OWNER && record?.namespace) namespaces.add(String(record.namespace));
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
    return Math.max(
      storedDraftSavedAt(rawFor(baseKey, KIND_DRAFT)),
      storedRecoverySavedAt(rawFor(baseKey, KIND_RECOVERY))
    );
  }

  function namespaceBytes(baseKey) {
    return utf8Bytes(rawFor(baseKey, KIND_DRAFT)) + utf8Bytes(rawFor(baseKey, KIND_RECOVERY));
  }

  function allCalculatorStorageBytes() {
    return storedNamespaceKeys().reduce((total, baseKey) => total + namespaceBytes(baseKey), 0);
  }

  function cleanupObsoleteNamespaces(now = Date.now()) {
    const cutoff = Number(now || Date.now()) - Number(ownerSetting('max_age_ms', 0));
    for (const baseKey of storedNamespaceKeys()) {
      if (baseKey === draftStorageKey) continue;
      const lastSavedAt = namespaceLastSavedAt(baseKey);
      if (!lastSavedAt || !cutoff || lastSavedAt >= cutoff) continue;
      removeRaw(baseKey, KIND_DRAFT);
      removeRaw(baseKey, KIND_RECOVERY);
    }
  }

  function pruneOtherNamespacesForQuota() {
    const candidates = storedNamespaceKeys()
      .filter((baseKey) => baseKey !== draftStorageKey)
      .map((baseKey) => ({baseKey, savedAt: namespaceLastSavedAt(baseKey), bytes: namespaceBytes(baseKey)}))
      .sort((left, right) => left.savedAt - right.savedAt);
    let removed = 0;
    const maxNamespaces = Number(ownerSetting('max_namespaces', 0));
    const maxBytes = Number(ownerSetting('max_total_bytes', 0));
    while (candidates.length && (
      (maxNamespaces && storedNamespaceKeys().length > maxNamespaces)
      || (maxBytes && allCalculatorStorageBytes() > maxBytes)
    )) {
      const candidate = candidates.shift();
      removeRaw(candidate.baseKey, KIND_DRAFT);
      removeRaw(candidate.baseKey, KIND_RECOVERY);
      removed += 1;
    }
    return removed;
  }

  function setDraftStorageKey(key) {
    const value = String(key || '').trim();
    const nextKey = value || `${currentPrefix()}global`;
    if (nextKey !== draftStorageKey) {
      storageWarnings.recovery = '';
      if (localRecoveryPauseReason !== 'failure') {
        storageWarnings.draft = '';
        localRecoveryPaused = false;
        localRecoveryPauseReason = '';
      }
    }
    draftStorageKey = nextKey;
    cleanupObsoleteNamespaces();
    pruneOtherNamespacesForQuota();
    return draftStorageKey;
  }

  function getDraftStorageKey() {
    return draftStorageKey;
  }

  function localStorageEntries() {
    const entries = [];
    try {
      for (let index = 0; index < window.localStorage.length; index += 1) {
        const key = window.localStorage.key(index);
        if (!key) continue;
        entries.push([String(key), window.localStorage.getItem(key) || '']);
      }
    } catch (_error) {
      return [];
    }
    return entries;
  }

  async function migrateLocalStorage() {
    const prefixes = [currentPrefix(), ...(ownerSetting('legacy_prefixes', []) || [])].filter(Boolean);
    const suffix = recoverySuffix();
    for (const [key, value] of localStorageEntries()) {
      if (!prefixes.some((prefix) => key.startsWith(String(prefix)))) continue;
      const isCurrent = key.startsWith(currentPrefix());
      if (isCurrent && value) {
        const kind = suffix && key.endsWith(suffix) ? KIND_RECOVERY : KIND_DRAFT;
        const namespace = kind === KIND_RECOVERY ? key.slice(0, -suffix.length) : key;
        const record = recordFor(namespace, kind, value);
        await putRecordImmediately(record);
        records.set(record.id, record);
      }
      try { window.localStorage.removeItem(key); } catch (_error) {}
    }
  }

  async function initializeStorage(contract, requestedKey) {
    storageContract = contract && typeof contract === 'object' ? contract : null;
    ownerContract = storageContract?.owners?.[OWNER] || null;
    draftStorageKey = String(requestedKey || `${currentPrefix()}global`);
    if (!storageContract || !ownerContract) {
      pauseForStorageFailure('Browser recovery configuration is unavailable. Calculator editing continues normally.');
      return false;
    }
    if (!storageInitialization) {
      storageInitialization = (async () => {
        try {
          database = await openDatabase(storageContract);
          await loadOwnerRecords();
          await migrateLocalStorage();
          storageReady = true;
          localRecoveryPaused = false;
          localRecoveryPauseReason = '';
          cleanupObsoleteNamespaces();
          pruneOtherNamespacesForQuota();
          await flushWrites();
          setWarning('draft', '');
          return true;
        } catch (_error) {
          storageReady = false;
          pauseForStorageFailure('Browser recovery storage is unavailable. Your current work remains open, but local recovery is paused.');
          return false;
        }
      })();
    }
    return storageInitialization;
  }

  function utf8Bytes(value) {
    const text = String(value || '');
    if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(text).length;
    return unescape(encodeURIComponent(text)).length;
  }

  function storageUsage(draftRaw = null, recoveryRaw = null) {
    const resolvedDraft = draftRaw === null ? rawFor(draftStorageKey, KIND_DRAFT) : String(draftRaw || '');
    const resolvedRecovery = recoveryRaw === null ? rawFor(draftStorageKey, KIND_RECOVERY) : String(recoveryRaw || '');
    const draftBytes = utf8Bytes(resolvedDraft);
    const recoveryBytes = utf8Bytes(resolvedRecovery);
    return {
      draftBytes,
      recoveryBytes,
      totalBytes: draftBytes + recoveryBytes,
    };
  }

  function formatStorageBytes(bytes) {
    const value = Math.max(0, Number(bytes || 0));
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(value < 10240 ? 1 : 0)} KB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }

  function updateStorageUsage() {
    if (calculatorState) calculatorState.recoveryStorageBytes = storageUsage().totalBytes;
  }

  function pauseLocalRecovery(reason = 'cleared') {
    localRecoveryPaused = true;
    localRecoveryPauseReason = String(reason || 'cleared');
  }

  function resumeLocalRecovery() {
    if (!storageReady) return false;
    if (!localRecoveryPaused) return true;
    if (localRecoveryPauseReason !== 'cleared') return false;
    localRecoveryPaused = false;
    localRecoveryPauseReason = '';
    return true;
  }

  function resumeSizeLimitedRecovery() {
    if (!storageReady) return false;
    if (!localRecoveryPaused) return true;
    if (localRecoveryPauseReason !== 'size') return false;
    localRecoveryPaused = false;
    localRecoveryPauseReason = '';
    return true;
  }

  function readDraftRaw(baseKey = draftStorageKey) {
    return rawFor(baseKey, KIND_DRAFT);
  }

  function readRecoveryRaw(baseKey = draftStorageKey) {
    return rawFor(baseKey, KIND_RECOVERY);
  }

  function writeDraftRaw(raw, baseKey = draftStorageKey) {
    return writeRaw(baseKey, KIND_DRAFT, raw);
  }

  function writeRecoveryRaw(raw, baseKey = draftStorageKey) {
    return writeRaw(baseKey, KIND_RECOVERY, raw);
  }

  function removeDraftRaw(baseKey = draftStorageKey) {
    return removeRaw(baseKey, KIND_DRAFT);
  }

  function removeRecoveryRaw(baseKey = draftStorageKey) {
    return removeRaw(baseKey, KIND_RECOVERY);
  }

  function flushWrites() {
    return writeQueue;
  }

  function debugRecords() {
    return [...records.values()].map((record) => ({...record}));
  }

  window.ItineraryCalculator.define('storage.core', {
    allCalculatorStorageBytes,
    cleanupObsoleteNamespaces,
    debugRecords,
    draftMaxAgeMs: () => Number(ownerSetting('max_age_ms', 0)),
    draftMaxBytes: () => Number(ownerSetting('max_draft_bytes', 0)),
    flushWrites,
    formatStorageBytes,
    getDraftStorageKey,
    initializeStorage,
    isLocalRecoveryPaused: () => localRecoveryPaused,
    localRecoveryPauseReason: () => localRecoveryPauseReason,
    maxSnapshots: () => Number(ownerSetting('max_snapshots', 0)),
    pauseLocalRecovery,
    pruneOtherNamespacesForQuota,
    readDraftRaw,
    readRecoveryRaw,
    recoverySchemaVersion: () => Number(ownerSetting('recovery_schema_version', 0)),
    recoveryStorageBudgetBytes: () => Number(ownerSetting('max_namespace_bytes', 0)),
    recoveryStorageKey,
    removeDraftRaw,
    removeRecoveryRaw,
    resumeLocalRecovery,
    resumeSizeLimitedRecovery,
    setDraftStorageKey,
    setWarning,
    statusPayload,
    storageUsage,
    updateStorageUsage,
    utf8Bytes,
    warningMessage,
    writeDraftRaw,
    writeRecoveryRaw,
  });
})();
