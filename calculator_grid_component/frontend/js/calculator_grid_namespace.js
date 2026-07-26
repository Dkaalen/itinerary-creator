// Explicit module registry for the Calculator frontend.

(() => {
  'use strict';

  if (window.ItineraryCalculator) {
    throw new Error('ItineraryCalculator namespace was initialized more than once.');
  }

  const modules = Object.create(null);
  const publicApi = Object.create(null);

  function define(name, factory) {
    const moduleName = String(name || '').trim();
    if (!moduleName) throw new Error('Calculator module name is required.');
    if (Object.prototype.hasOwnProperty.call(modules, moduleName)) {
      throw new Error(`Calculator module already defined: ${moduleName}`);
    }
    const exports = typeof factory === 'function' ? factory(namespace) : factory;
    if (!exports || typeof exports !== 'object') {
      throw new Error(`Calculator module must export an object: ${moduleName}`);
    }
    modules[moduleName] = Object.freeze(exports);
    return modules[moduleName];
  }

  function requireModule(name) {
    const moduleName = String(name || '').trim();
    const exports = modules[moduleName];
    if (!exports) throw new Error(`Calculator module is not available: ${moduleName}`);
    return exports;
  }

  function publish(name, value) {
    const publicName = String(name || '').trim();
    if (!publicName) throw new Error('Calculator public API name is required.');
    if (Object.prototype.hasOwnProperty.call(publicApi, publicName)) {
      throw new Error(`Calculator public API already published: ${publicName}`);
    }
    const published = value && typeof value === 'object' ? Object.freeze(value) : value;
    publicApi[publicName] = published;
    Object.defineProperty(namespace, publicName, {
      configurable: false,
      enumerable: true,
      writable: false,
      value: published,
    });
    return published;
  }

  const namespace = {
    define,
    has: (name) => Object.prototype.hasOwnProperty.call(modules, String(name || '').trim()),
    publish,
    require: requireModule,
  };

  Object.defineProperty(window, 'ItineraryCalculator', {
    configurable: false,
    enumerable: true,
    writable: false,
    value: namespace,
  });
})();
