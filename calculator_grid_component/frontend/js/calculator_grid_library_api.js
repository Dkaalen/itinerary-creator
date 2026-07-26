// Stable public Local Library API assembled from explicit Calculator modules.

(() => {
  'use strict';

  const normalization = window.ItineraryCalculator.require('library.normalization');
  const transport = window.ItineraryCalculator.require('library.transport');
  const indexApi = window.ItineraryCalculator.require('library.index');
  const search = window.ItineraryCalculator.require('library.search');
  const selection = window.ItineraryCalculator.require('library.selection');

  function prepareBundle(payload = {}) {
    const fingerprint = String(payload.library_fingerprint || '');
    const rankingSpec = payload.library_ranking_spec || {};
    const rows = transport.resolveRows({
      rows: payload.library_rows || [],
      fingerprint,
      payloadVersion: payload.library_payload_version || '',
      rowCount: payload.library_row_count || 0,
    });
    return indexApi.prepareLibraryBundle(
      rows,
      payload.library_row_fields || [],
      fingerprint,
      rankingSpec
    );
  }

  window.ItineraryCalculator.publish('library', {
    applySuggestion: selection.applyLibrarySuggestion,
    buildSearchIndex: indexApi.buildLibrarySearchIndex,
    clearRetainedRows: transport.clearRetainedRows,
    expectedSheet: search.expectedLibrarySheet,
    findSuggestions: search.findLibrarySuggestions,
    normalizeSearchText: normalization.normalizeSearchText,
    prepareBundle,
    scoreItem: search.scoreLibraryItem,
  });
})();
