/** IndexedDB ownership, migration, health, and retention for Visual Editor drafts. */
(() => {
  'use strict';
const LOCAL_DRAFT_OWNER = 'visual_editor';
let localDraftPersistencePaused = false;
let visualDraftPauseReason = '';
let visualDraftContract = null;
let visualDraftOwnerContract = null;
let visualDraftDatabase = null;
let visualDraftStorageReady = false;
let visualDraftStorageInitialization = null;
let visualDraftWriteQueue = Promise.resolve();
let visualDraftActiveKey = '';
const visualDraftRecords = new Map();

function visualDraftOwnerSetting(name, fallback = null) {
  const value = visualDraftOwnerContract?.[name];
  return value === undefined || value === null ? fallback : value;
}

function draftStorageKeyForPayload(payload) {
  const fallback = [payload?.cover?.trip_title || '', payload?.cover?.trip_dates || '', (payload?.days || []).length].join('|');
  return `${String(visualDraftOwnerSetting('current_prefix', ''))}${payload?.draft_id || fallback}`;
}

function draftStorageKey() {
  if (visualDraftActiveKey) return visualDraftActiveKey;
  return draftStorageKeyForPayload(initialPayload || {});
}

function localDraftBytes(value) {
  const text = String(value || '');
  try { return new TextEncoder().encode(text).length; } catch (err) { return text.length * 2; }
}

function visualDraftRequestResult(request) {
  return new Promise((resolve, reject) => {
    request.addEventListener('success', () => resolve(request.result), {once: true});
    request.addEventListener('error', () => reject(request.error || new Error('IndexedDB request failed')), {once: true});
  });
}

function visualDraftTransactionDone(transaction) {
  return new Promise((resolve, reject) => {
    transaction.addEventListener('complete', resolve, {once: true});
    transaction.addEventListener('abort', () => reject(transaction.error || new Error('IndexedDB transaction aborted')), {once: true});
    transaction.addEventListener('error', () => reject(transaction.error || new Error('IndexedDB transaction failed')), {once: true});
  });
}

async function openVisualDraftDatabase(contract) {
  if (!window.indexedDB) throw new Error('IndexedDB is unavailable');
  const dbContract = contract?.indexed_db || {};
  const name = String(dbContract.name || '');
  const storeName = String(dbContract.store || '');
  const version = Number(dbContract.version || 0);
  if (!name || !storeName || !Number.isInteger(version) || version < 1) throw new Error('Browser storage contract is invalid');
  const request = window.indexedDB.open(name, version);
  request.addEventListener('upgradeneeded', () => {
    const db = request.result;
    if (!db.objectStoreNames.contains(storeName)) db.createObjectStore(storeName, {keyPath: 'id'});
  });
  return visualDraftRequestResult(request);
}

function visualDraftStoreName() {
  return String(visualDraftContract?.indexed_db?.store || '');
}

function visualDraftRecordId(key) {
  return `${LOCAL_DRAFT_OWNER}|${String(key || '')}|draft`;
}

function visualDraftSavedAt(raw) {
  try { return Number(JSON.parse(String(raw || ''))?.saved_at || 0); } catch (_error) { return 0; }
}

function visualDraftRecord(key, payload) {
  const raw = String(payload || '');
  return {
    id: visualDraftRecordId(key),
    owner: LOCAL_DRAFT_OWNER,
    namespace: String(key || ''),
    kind: 'draft',
    payload: raw,
    savedAt: visualDraftSavedAt(raw),
    bytes: localDraftBytes(raw),
    updatedAt: Date.now(),
  };
}

async function loadVisualDraftRecords() {
  const transaction = visualDraftDatabase.transaction(visualDraftStoreName(), 'readonly');
  const done = visualDraftTransactionDone(transaction);
  const all = await visualDraftRequestResult(transaction.objectStore(visualDraftStoreName()).getAll());
  await done;
  visualDraftRecords.clear();
  for (const record of all || []) {
    if (record?.owner === LOCAL_DRAFT_OWNER && record?.id) visualDraftRecords.set(String(record.id), record);
  }
}

async function putVisualDraftRecordImmediately(record) {
  const transaction = visualDraftDatabase.transaction(visualDraftStoreName(), 'readwrite');
  transaction.objectStore(visualDraftStoreName()).put(record);
  await visualDraftTransactionDone(transaction);
}

async function deleteVisualDraftRecordImmediately(id) {
  const transaction = visualDraftDatabase.transaction(visualDraftStoreName(), 'readwrite');
  transaction.objectStore(visualDraftStoreName()).delete(String(id));
  await visualDraftTransactionDone(transaction);
}

function pauseVisualDraftPersistence(reason = 'failure') {
  localDraftPersistencePaused = true;
  visualDraftPauseReason = String(reason || 'failure');
  updateSaveState('dirty', {message: 'Browser recovery paused. Use Save changes to sync your work.', localRecoveryAvailable: false});
}

function resumeVisualDraftPersistenceAfterSize() {
  if (!visualDraftStorageReady) return false;
  if (!localDraftPersistencePaused) return true;
  if (visualDraftPauseReason !== 'size') return false;
  localDraftPersistencePaused = false;
  visualDraftPauseReason = '';
  return true;
}

async function reconcileVisualDraftRecordsAfterFailure() {
  try {
    await loadVisualDraftRecords();
  } catch (_error) {
    visualDraftRecords.clear();
  }
}

function queueVisualDraftWrite(operation) {
  visualDraftWriteQueue = visualDraftWriteQueue.then(() => {
    if (visualDraftPauseReason === 'failure') return false;
    return operation();
  }).catch(async () => {
    pauseVisualDraftPersistence('failure');
    await reconcileVisualDraftRecordsAfterFailure();
    return false;
  });
  return visualDraftWriteQueue;
}

function readVisualDraftRaw(key = draftStorageKey()) {
  return String(visualDraftRecords.get(visualDraftRecordId(key))?.payload || '');
}

function writeVisualDraftRaw(key, payload) {
  if (!visualDraftStorageReady || localDraftPersistencePaused || !visualDraftDatabase) return false;
  const record = visualDraftRecord(key, payload);
  visualDraftRecords.set(record.id, record);
  queueVisualDraftWrite(() => putVisualDraftRecordImmediately(record));
  return true;
}

function removeVisualDraftRaw(key = draftStorageKey()) {
  if (!visualDraftStorageReady || !visualDraftDatabase) return false;
  const id = visualDraftRecordId(key);
  visualDraftRecords.delete(id);
  queueVisualDraftWrite(() => deleteVisualDraftRecordImmediately(id));
  return true;
}

function localStorageDraftEntries() {
  const entries = [];
  try {
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (!key) continue;
      entries.push([String(key), localStorage.getItem(key) || '']);
    }
  } catch (_error) {
    return [];
  }
  return entries;
}

async function migrateVisualDraftLocalStorage() {
  const currentPrefix = String(visualDraftOwnerSetting('current_prefix', ''));
  const prefixes = [currentPrefix, ...(visualDraftOwnerSetting('legacy_prefixes', []) || [])].filter(Boolean);
  for (const [key, value] of localStorageDraftEntries()) {
    if (!prefixes.some((prefix) => key.startsWith(String(prefix)))) continue;
    if (currentPrefix && key.startsWith(currentPrefix) && value) {
      const record = visualDraftRecord(key, value);
      await putVisualDraftRecordImmediately(record);
      visualDraftRecords.set(record.id, record);
    }
    try { localStorage.removeItem(key); } catch (_error) {}
  }
}

function pruneEditorLocalDrafts(activeKey = draftStorageKey()) {
  const drafts = [...visualDraftRecords.values()]
    .filter((record) => record?.owner === LOCAL_DRAFT_OWNER)
    .sort((a, b) => Number(b.savedAt || 0) - Number(a.savedAt || 0));
  const now = Date.now();
  const maxAge = Number(visualDraftOwnerSetting('max_age_ms', 0));
  const maxProjects = Number(visualDraftOwnerSetting('max_namespaces', 0));
  const maxBytes = Number(visualDraftOwnerSetting('max_total_bytes', 0));
  let retained = 0;
  let total = 0;
  drafts.forEach((record) => {
    const key = String(record.namespace || '');
    const bytes = Number(record.bytes || localDraftBytes(record.payload));
    const stale = Boolean(maxAge && record.savedAt && now - Number(record.savedAt) > maxAge);
    const over = key !== activeKey && (
      (maxProjects && retained >= maxProjects)
      || (maxBytes && total + bytes > maxBytes)
    );
    if (stale || over) removeVisualDraftRaw(key);
    else { retained += 1; total += bytes; }
  });
}

async function prepareLocalDraftStorage(payload) {
  const contract = payload?.browser_storage_contract;
  visualDraftContract = contract && typeof contract === 'object' ? contract : null;
  visualDraftOwnerContract = visualDraftContract?.owners?.[LOCAL_DRAFT_OWNER] || null;
  if (!payload?.workflow?.commit_signal_only || !visualDraftActiveKey) {
    const nextKey = draftStorageKeyForPayload(payload || {});
    if (nextKey !== visualDraftActiveKey && visualDraftPauseReason === 'size') {
      localDraftPersistencePaused = false;
      visualDraftPauseReason = '';
    }
    visualDraftActiveKey = nextKey;
  }
  if (!visualDraftContract || !visualDraftOwnerContract) {
    pauseVisualDraftPersistence('failure');
    return false;
  }
  if (!visualDraftStorageInitialization) {
    visualDraftStorageInitialization = (async () => {
      try {
        visualDraftDatabase = await openVisualDraftDatabase(visualDraftContract);
        await loadVisualDraftRecords();
        await migrateVisualDraftLocalStorage();
        visualDraftStorageReady = true;
        localDraftPersistencePaused = false;
        visualDraftPauseReason = '';
        pruneEditorLocalDrafts(visualDraftActiveKey);
        await flushVisualDraftWrites();
        return true;
      } catch (_error) {
        visualDraftStorageReady = false;
        pauseVisualDraftPersistence('failure');
        return false;
      }
    })();
  }
  const ready = await visualDraftStorageInitialization;
  if (ready) pruneEditorLocalDrafts(visualDraftActiveKey);
  return ready;
}

function flushVisualDraftWrites() {
  return visualDraftWriteQueue;
}

  ItineraryVisualEditor.define('draftStorage', {
    bytes: localDraftBytes,
    flush: flushVisualDraftWrites,
    isPaused: () => localDraftPersistencePaused,
    pauseReason: () => visualDraftPauseReason,
    key: draftStorageKey,
    maxDraftBytes: () => Number(visualDraftOwnerSetting('max_draft_bytes', 0)),
    pause: pauseVisualDraftPersistence,
    prepare: prepareLocalDraftStorage,
    prune: pruneEditorLocalDrafts,
    read: readVisualDraftRaw,
    resumeAfterSize: resumeVisualDraftPersistenceAfterSize,
    remove: removeVisualDraftRaw,
    write: (payload) => writeVisualDraftRaw(draftStorageKey(), payload),
  });
})();
