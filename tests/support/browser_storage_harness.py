"""Deterministic browser-storage doubles for navigation-free frontend tests."""

from __future__ import annotations


def fake_indexed_db_script() -> str:
    """Return a small IndexedDB implementation covering the app-owned contract."""

    return r"""
      <script>
        (() => {
          const databases = new Map();

          function eventTarget() {
            const listeners = new Map();
            return {
              addEventListener(type, callback, options = {}) {
                const bucket = listeners.get(type) || [];
                bucket.push({callback, once: Boolean(options && options.once)});
                listeners.set(type, bucket);
              },
              __dispatch(type, event = {}) {
                const bucket = [...(listeners.get(type) || [])];
                bucket.forEach((entry) => entry.callback.call(this, {type, target: this, ...event}));
                listeners.set(type, (listeners.get(type) || []).filter((entry) => !entry.once));
                const handler = this[`on${type}`];
                if (typeof handler === 'function') handler.call(this, {type, target: this, ...event});
              },
            };
          }

          function request() {
            return Object.assign(eventTarget(), {result: undefined, error: null});
          }

          function databaseState(name, version) {
            if (!databases.has(name)) databases.set(name, {version, stores: new Map()});
            const state = databases.get(name);
            state.version = Math.max(Number(state.version || 0), Number(version || 0));
            return state;
          }

          function database(name, state) {
            const api = {
              name,
              version: state.version,
              close() {},
              objectStoreNames: {contains: (storeName) => state.stores.has(String(storeName))},
              createObjectStore(storeName) {
                const key = String(storeName);
                if (!state.stores.has(key)) state.stores.set(key, new Map());
                return {};
              },
              transaction(storeName) {
                const key = String(storeName);
                if (!state.stores.has(key)) throw new Error(`Missing object store: ${key}`);
                const tx = Object.assign(eventTarget(), {error: null, __pending: 0, __completeScheduled: false});
                const store = state.stores.get(key);
                const scheduleComplete = () => {
                  if (tx.__pending || tx.__completeScheduled) return;
                  tx.__completeScheduled = true;
                  setTimeout(() => tx.__dispatch('complete'), 0);
                };
                const run = (operation) => {
                  const req = request();
                  tx.__pending += 1;
                  setTimeout(() => {
                    try {
                      req.result = operation();
                      req.__dispatch('success');
                    } catch (error) {
                      req.error = error;
                      tx.error = error;
                      req.__dispatch('error');
                      tx.__dispatch('error');
                    } finally {
                      tx.__pending -= 1;
                      scheduleComplete();
                    }
                  }, 0);
                  return req;
                };
                tx.objectStore = () => ({
                  getAll: () => run(() => [...store.values()].map((value) => structuredClone(value))),
                  put: (value) => run(() => {
                    window.__fakeIndexedDbPutAttemptCount = Number(window.__fakeIndexedDbPutAttemptCount || 0) + 1;
                    if (window.__failFakeIndexedDbWrites) throw new DOMException('IndexedDB write blocked', 'UnknownError');
                    const copy = structuredClone(value);
                    store.set(String(copy.id), copy);
                    window.__fakeIndexedDbPutCount = Number(window.__fakeIndexedDbPutCount || 0) + 1;
                    return copy.id;
                  }),
                  delete: (id) => run(() => {
                    if (window.__failFakeIndexedDbWrites) throw new DOMException('IndexedDB write blocked', 'UnknownError');
                    window.__fakeIndexedDbDeleteCount = Number(window.__fakeIndexedDbDeleteCount || 0) + 1;
                    return store.delete(String(id));
                  }),
                });
                return tx;
              },
            };
            return api;
          }

          const indexedDB = {
            open(name, version) {
              const req = request();
              setTimeout(() => {
                try {
                  const dbName = String(name);
                  const requestedVersion = Number(version || 1);
                  const existed = databases.has(dbName);
                  const state = databaseState(dbName, requestedVersion);
                  req.result = database(dbName, state);
                  if (!existed) req.__dispatch('upgradeneeded');
                  req.__dispatch('success');
                } catch (error) {
                  req.error = error;
                  req.__dispatch('error');
                }
              }, 0);
              return req;
            },
          };

          Object.defineProperty(window, 'indexedDB', {value: indexedDB, configurable: true});
          window.__fakeIndexedDbDatabases = databases;
        })();
      </script>
    """


__all__ = ["fake_indexed_db_script"]
