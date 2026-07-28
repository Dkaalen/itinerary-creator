"""Mount an idempotent browser-recovery migration and cleanup guard."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from typing import Any

from app_modules.browser_storage_contract import browser_storage_contract


def _guard_script() -> str:
    contract_json = json.dumps(browser_storage_contract(), separators=(",", ":"), sort_keys=True)
    return rf"""
<script>
(async () => {{
  'use strict';
  const CONTRACT = {contract_json};
  const OWNER_CALCULATOR = 'calculator';
  const OWNER_EDITOR = 'visual_editor';

  function bytes(value) {{
    const text = String(value || '');
    try {{ return new TextEncoder().encode(text).length; }} catch (_error) {{ return text.length * 2; }}
  }}
  function savedAt(owner, kind, raw) {{
    try {{
      const parsed = JSON.parse(String(raw || ''));
      if (owner === OWNER_EDITOR) return Number(parsed?.saved_at || 0);
      if (kind === 'recovery') {{
        const entries = Array.isArray(parsed) ? parsed : parsed?.entries;
        return Array.isArray(entries)
          ? entries.reduce((latest, entry) => Math.max(latest, Number(entry?.savedAt || 0)), 0)
          : 0;
      }}
      return Number(parsed?.savedAt || 0);
    }} catch (_error) {{ return 0; }}
  }}
  function requestResult(request) {{
    return new Promise((resolve, reject) => {{
      request.addEventListener('success', () => resolve(request.result), {{once: true}});
      request.addEventListener('error', () => reject(request.error || new Error('IndexedDB request failed')), {{once: true}});
    }});
  }}
  function transactionDone(transaction) {{
    return new Promise((resolve, reject) => {{
      transaction.addEventListener('complete', resolve, {{once: true}});
      transaction.addEventListener('abort', () => reject(transaction.error || new Error('IndexedDB transaction aborted')), {{once: true}});
      transaction.addEventListener('error', () => reject(transaction.error || new Error('IndexedDB transaction failed')), {{once: true}});
    }});
  }}
  async function openDatabase(indexedDb) {{
    const spec = CONTRACT.indexed_db || {{}};
    const request = indexedDb.open(String(spec.name || ''), Number(spec.version || 0));
    request.addEventListener('upgradeneeded', () => {{
      const db = request.result;
      const store = String(spec.store || '');
      if (!db.objectStoreNames.contains(store)) db.createObjectStore(store, {{keyPath: 'id'}});
    }});
    return requestResult(request);
  }}
  function storageEntries(store) {{
    const result = [];
    for (let index = 0; index < store.length; index += 1) {{
      const key = store.key(index);
      if (!key) continue;
      result.push([String(key), store.getItem(key) || '']);
    }}
    return result;
  }}
  function record(owner, namespace, kind, payload) {{
    const raw = String(payload || '');
    return {{
      id: `${{owner}}|${{namespace}}|${{kind}}`,
      owner,
      namespace,
      kind,
      payload: raw,
      savedAt: savedAt(owner, kind, raw),
      bytes: bytes(raw),
      updatedAt: Date.now(),
    }};
  }}
  async function putRecord(db, value) {{
    const transaction = db.transaction(String(CONTRACT.indexed_db.store), 'readwrite');
    transaction.objectStore(String(CONTRACT.indexed_db.store)).put(value);
    await transactionDone(transaction);
  }}
  async function deleteRecords(db, ids) {{
    if (!ids.length) return;
    const transaction = db.transaction(String(CONTRACT.indexed_db.store), 'readwrite');
    const store = transaction.objectStore(String(CONTRACT.indexed_db.store));
    ids.forEach((id) => store.delete(String(id)));
    await transactionDone(transaction);
  }}
  async function allRecords(db) {{
    const transaction = db.transaction(String(CONTRACT.indexed_db.store), 'readonly');
    const done = transactionDone(transaction);
    const values = await requestResult(transaction.objectStore(String(CONTRACT.indexed_db.store)).getAll());
    await done;
    return values || [];
  }}
  function pruneOwner(records, owner, config) {{
    const owned = records.filter((item) => item?.owner === owner);
    const grouped = new Map();
    owned.forEach((item) => {{
      const namespace = String(item.namespace || '');
      if (!grouped.has(namespace)) grouped.set(namespace, []);
      grouped.get(namespace).push(item);
    }});
    const now = Date.now();
    const groups = [...grouped.entries()].map(([namespace, items]) => ({{
      namespace,
      items,
      bytes: items.reduce((total, item) => total + Number(item.bytes || bytes(item.payload)), 0),
      savedAt: items.reduce((latest, item) => Math.max(latest, Number(item.savedAt || 0)), 0),
    }})).sort((left, right) => right.savedAt - left.savedAt);
    const remove = [];
    let retained = 0;
    let total = 0;
    groups.forEach((group) => {{
      const stale = Boolean(config.max_age_ms && group.savedAt && now - group.savedAt > Number(config.max_age_ms));
      const over = Boolean(
        (config.max_namespaces && retained >= Number(config.max_namespaces))
        || (config.max_total_bytes && total + group.bytes > Number(config.max_total_bytes))
      );
      if (stale || over) group.items.forEach((item) => remove.push(String(item.id)));
      else {{ retained += 1; total += group.bytes; }}
    }});
    return remove;
  }}

  let parentStorage;
  let parentSession;
  let parentIndexedDb;
  try {{
    parentStorage = window.parent.localStorage;
    parentSession = window.parent.sessionStorage;
    parentIndexedDb = window.parent.indexedDB;
    void parentStorage.length;
    void parentSession.length;
    if (!parentIndexedDb) return;
  }} catch (_error) {{
    return;
  }}

  const cleanupKey = String(CONTRACT.cleanup_session_key || '');
  const completionValue = String(CONTRACT.schema_version || 1);
  try {{
    if (cleanupKey && parentSession.getItem(cleanupKey) === completionValue) return;
  }} catch (_error) {{ return; }}

  try {{
    const db = await openDatabase(parentIndexedDb);
    const calculator = CONTRACT.owners.calculator || {{}};
    const editor = CONTRACT.owners.visual_editor || {{}};
    const currentEntries = storageEntries(parentStorage);
    for (const [key, value] of currentEntries) {{
      const calcCurrent = String(calculator.current_prefix || '');
      const calcLegacy = calculator.legacy_prefixes || [];
      const editorCurrent = String(editor.current_prefix || '');
      const editorLegacy = editor.legacy_prefixes || [];
      if (calcCurrent && key.startsWith(calcCurrent)) {{
        const suffix = String(calculator.recovery_suffix || '.versions');
        const kind = suffix && key.endsWith(suffix) ? 'recovery' : 'draft';
        const namespace = kind === 'recovery' ? key.slice(0, -suffix.length) : key;
        if (value) await putRecord(db, record(OWNER_CALCULATOR, namespace, kind, value));
        parentStorage.removeItem(key);
      }} else if (editorCurrent && key.startsWith(editorCurrent)) {{
        if (value) await putRecord(db, record(OWNER_EDITOR, key, 'draft', value));
        parentStorage.removeItem(key);
      }} else if (
        calcLegacy.some((prefix) => key.startsWith(String(prefix)))
        || editorLegacy.some((prefix) => key.startsWith(String(prefix)))
      ) {{
        parentStorage.removeItem(key);
      }}
    }}
    const records = await allRecords(db);
    const deleteIds = [
      ...pruneOwner(records, OWNER_CALCULATOR, calculator),
      ...pruneOwner(records, OWNER_EDITOR, editor),
    ];
    await deleteRecords(db, [...new Set(deleteIds)]);
    if (cleanupKey) parentSession.setItem(cleanupKey, completionValue);
    db.close();
  }} catch (_error) {{
    // No completion marker is written. The idempotent guard retries later.
  }}
}})();
</script>
"""


_BROWSER_STORAGE_GUARD = _guard_script()


def render_browser_storage_guard(state: MutableMapping[str, Any]) -> None:
    """Mount the idempotent cleanup script; the browser owns completion state."""

    from app_modules.performance_telemetry import record_trace, telemetry_is_active

    try:
        import streamlit.components.v1 as components

        components.html(_BROWSER_STORAGE_GUARD, height=0, width=0)
    except Exception as exc:
        if telemetry_is_active(state):
            record_trace(
                state,
                "browser_storage_guard_mount",
                status="failed",
                error_type=type(exc).__name__,
            )
        return
    if telemetry_is_active(state):
        record_trace(
            state,
            "browser_storage_guard_mount",
            status="mounted_idempotent",
        )


__all__ = ["render_browser_storage_guard"]
