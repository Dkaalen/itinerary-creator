// Browser retention handshake for the compact Local Library payload.

(() => {
  'use strict';

  const CACHE_SCHEMA_VERSION = 'calculator-library-browser-v1';
  const CACHE_STORAGE_KEY = 'itineraryCalculator.localLibrary.v1';

  function normalizeRowCount(value) {
    const parsed = Number(value || 0);
    return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
  }

  function compactRowsAreComplete(rows, rowCount) {
    return Array.isArray(rows) && rows.length === normalizeRowCount(rowCount);
  }

  function cacheEnvelope({rows, fingerprint, payloadVersion, rowCount}) {
    return {
      schemaVersion: CACHE_SCHEMA_VERSION,
      payloadVersion: String(payloadVersion || ''),
      fingerprint: String(fingerprint || ''),
      rowCount: normalizeRowCount(rowCount),
      rows,
    };
  }

  function envelopeMatches(envelope, {fingerprint, payloadVersion, rowCount}) {
    return Boolean(
      envelope
      && envelope.schemaVersion === CACHE_SCHEMA_VERSION
      && String(envelope.payloadVersion || '') === String(payloadVersion || '')
      && String(envelope.fingerprint || '') === String(fingerprint || '')
      && normalizeRowCount(envelope.rowCount) === normalizeRowCount(rowCount)
      && compactRowsAreComplete(envelope.rows, rowCount)
    );
  }

  function readRetainedRows(contract) {
    try {
      const raw = window.sessionStorage.getItem(CACHE_STORAGE_KEY);
      if (!raw) return null;
      const envelope = JSON.parse(raw);
      return envelopeMatches(envelope, contract) ? envelope.rows : null;
    } catch (_error) {
      return null;
    }
  }

  function retainRows(rows, contract) {
    try {
      window.sessionStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(cacheEnvelope({...contract, rows})));
      return true;
    } catch (_error) {
      return false;
    }
  }

  function clearRetainedRows() {
    try {
      window.sessionStorage.removeItem(CACHE_STORAGE_KEY);
      return true;
    } catch (_error) {
      return false;
    }
  }

  function reportStatus(status, contract) {
    return Streamlit.setComponentValue(JSON.stringify({
      action: 'library_transport',
      library_transport: {
        status: String(status || ''),
        fingerprint: String(contract.fingerprint || ''),
        payload_version: String(contract.payloadVersion || ''),
        row_count: normalizeRowCount(contract.rowCount),
      },
    }));
  }

  function resolveRows({rows, fingerprint, payloadVersion, rowCount}) {
    const incomingRows = Array.isArray(rows) ? rows : [];
    const reportedRowCount = normalizeRowCount(rowCount);
    const contract = {
      fingerprint: String(fingerprint || ''),
      payloadVersion: String(payloadVersion || ''),
      rowCount: reportedRowCount || incomingRows.length,
    };
    if (incomingRows.length) {
      if (!compactRowsAreComplete(incomingRows, contract.rowCount)) return [];
      if (retainRows(incomingRows, contract)) reportStatus('retained', contract);
      return incomingRows;
    }

    const retained = readRetainedRows(contract);
    if (retained) {
      reportStatus('retained', contract);
      return retained;
    }
    reportStatus('cache_miss', contract);
    return [];
  }

  window.ItineraryCalculator.define('library.transport', {
    cacheSchemaVersion: CACHE_SCHEMA_VERSION,
    clearRetainedRows,
    resolveRows,
  });
})();
