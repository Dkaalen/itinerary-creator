// Explicit public boundary for the visual editor frontend.
(() => {
  const modules = new Map();
  let ready = false;

  function validateModuleName(name) {
    const normalized = String(name || '').trim();
    if (!normalized) throw new Error('Visual editor module name is required.');
    return normalized;
  }

  function define(name, api) {
    const moduleName = validateModuleName(name);
    if (modules.has(moduleName)) {
      throw new Error(`Visual editor module already defined: ${moduleName}`);
    }
    const exportedApi = api && typeof api === 'object' ? Object.freeze(api) : api;
    modules.set(moduleName, exportedApi);
    return exportedApi;
  }

  function requireModule(name) {
    const moduleName = validateModuleName(name);
    if (!modules.has(moduleName)) {
      throw new Error(`Visual editor module is not available: ${moduleName}`);
    }
    return modules.get(moduleName);
  }

  function markReady() {
    ready = true;
  }

  const namespace = Object.freeze({
    define,
    require: requireModule,
    has: (name) => modules.has(String(name || '').trim()),
    list: () => Object.freeze(Array.from(modules.keys())),
    isReady: () => ready,
    markReady,
  });

  Object.defineProperty(window, 'ItineraryVisualEditor', {
    value: namespace,
    configurable: false,
    enumerable: false,
    writable: false,
  });
})();
