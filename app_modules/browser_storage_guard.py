"""Render a silent, bounded cleanup guard for browser-local recovery data."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

_GUARD_RENDERED_KEY = "browser_storage_guard_rendered_v1"

_BROWSER_STORAGE_GUARD = r"""
<script>
(() => {
  'use strict';
  const DAY = 24 * 60 * 60 * 1000;
  const MAX_AGE = 7 * DAY;
  const MAX_CALC_NAMESPACES = 3;
  const MAX_CALC_BYTES = 1.5 * 1024 * 1024;
  const MAX_EDITOR_DRAFTS = 3;
  const MAX_EDITOR_BYTES = 1.0 * 1024 * 1024;
  const LEGACY_PREFIXES = [
    'itineraryCalculatorBrowserDraft.v1.',
    'itineraryCalculatorBrowserDraft.v2.',
    'itineraryCalculatorDraft.',
    'calculatorDraft.'
  ];
  const calcPrefix = 'itineraryCalculatorBrowserDraft.v3.';
  const editorPrefix = 'itineraryVisualEditorDraft.';

  function storage() {
    try { return window.parent.localStorage; } catch (_error) {}
    try { return window.localStorage; } catch (_error) {}
    return null;
  }
  function bytes(value) {
    const text = String(value || '');
    try { return new TextEncoder().encode(text).length; } catch (_error) { return text.length * 2; }
  }
  function savedAt(raw) {
    try {
      const parsed = JSON.parse(String(raw || ''));
      if (Array.isArray(parsed)) return parsed.reduce((n, item) => Math.max(n, Number(item?.savedAt || item?.saved_at || 0)), 0);
      const entries = Array.isArray(parsed?.entries) ? parsed.entries : [];
      return Math.max(Number(parsed?.savedAt || parsed?.saved_at || 0), ...entries.map(item => Number(item?.savedAt || 0)), 0);
    } catch (_error) { return 0; }
  }
  function entries(store) {
    const result = [];
    try {
      for (let index = 0; index < store.length; index += 1) {
        const key = store.key(index);
        if (!key) continue;
        const value = store.getItem(key) || '';
        result.push({key, value, bytes: bytes(key) + bytes(value), savedAt: savedAt(value)});
      }
    } catch (_error) {}
    return result;
  }
  function remove(store, key) { try { store.removeItem(key); } catch (_error) {} }
  function pruneGroup(store, group, maxItems, maxBytes, pairVersions) {
    const now = Date.now();
    const sorted = group.slice().sort((a, b) => (b.savedAt || 0) - (a.savedAt || 0));
    let used = 0;
    let kept = 0;
    for (const item of sorted) {
      const stale = item.savedAt && now - item.savedAt > MAX_AGE;
      const over = kept >= maxItems || used + item.bytes > maxBytes;
      if (stale || over) {
        remove(store, item.key);
        if (pairVersions) remove(store, `${item.key}.versions`);
      } else {
        kept += 1;
        used += item.bytes;
      }
    }
  }

  const store = storage();
  if (!store) return;
  const all = entries(store);
  all.forEach(item => {
    if (LEGACY_PREFIXES.some(prefix => item.key.startsWith(prefix))) remove(store, item.key);
  });
  const refreshed = entries(store);
  const calcBases = refreshed.filter(item => item.key.startsWith(calcPrefix) && !item.key.endsWith('.versions'));
  pruneGroup(store, calcBases, MAX_CALC_NAMESPACES, MAX_CALC_BYTES, true);
  const editorDrafts = refreshed.filter(item => item.key.startsWith(editorPrefix));
  pruneGroup(store, editorDrafts, MAX_EDITOR_DRAFTS, MAX_EDITOR_BYTES, false);
})();
</script>
"""


def render_browser_storage_guard(state: MutableMapping[str, Any]) -> None:
    """Mount the cleanup script once per Streamlit session."""

    if state.get(_GUARD_RENDERED_KEY):
        return
    try:
        import streamlit.components.v1 as components

        components.html(_BROWSER_STORAGE_GUARD, height=0, width=0)
    except Exception:
        return
    state[_GUARD_RENDERED_KEY] = True


__all__ = ["render_browser_storage_guard"]
