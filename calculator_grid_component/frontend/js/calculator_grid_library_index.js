// Local Library payload expansion and browser search-index ownership.

(() => {
  'use strict';

  const normalization = window.ItineraryCalculator.require('library.normalization');
  let preparedLibraryFingerprint = '';
  let preparedLibraryRankingVersion = '';
  let preparedLibraryBundle = null;

  function librarySearchFieldValue(item, fieldName) {
    if (Object.prototype.hasOwnProperty.call(item, fieldName)) return item[fieldName];
    return (item.row_data || {})[fieldName] ?? '';
  }

  function buildLibraryLabel(item) {
    const prefix = [item.country, item.category || item.type, item.supplier].filter(Boolean).join(' · ');
    const title = item.travel_element || item.comments || item.url || item.library_id || '';
    return prefix ? `${prefix} — ${title}` : title;
  }

  function buildLibraryPreview(item) {
    const row = item.row_data || {};
    const parts = [
      item.travel_element,
      item.supplier ? `Supplier: ${item.supplier}` : '',
      item.type ? `Type: ${item.type}` : '',
      item.country ? `Country: ${item.country}` : '',
      numberValue(row.gross_price_per_unit) ? `Price/unit: ${row.gross_price_per_unit} ${row.supplier_currency || ''}` : '',
      optionalNumberValue(row.sales_price_per_unit) ? `Sales/unit: ${row.sales_price_per_unit} ${row.sales_currency || ''}` : '',
      item.comments,
      item.url,
    ];
    return parts.filter(Boolean).join(' • ').slice(0, 450);
  }

  function searchBigramsFromNormalized(value) {
    const text = String(value || '').replaceAll(' ', '_');
    const result = new Set();
    if (text.length < 2) return result;
    for (let index = 0; index < text.length - 1; index += 1) result.add(text.slice(index, index + 2));
    return result;
  }

  function libraryTieBreakValue(item, fieldName, rankingSpec = {}) {
    if (fieldName === 'source_row') {
      const raw = item.source_row;
      return raw !== null && raw !== undefined && String(raw).trim() !== '' && Number.isFinite(Number(raw))
        ? Number(raw)
        : Number.MAX_SAFE_INTEGER;
    }
    return normalization.normalizeSearchText(librarySearchFieldValue(item, fieldName), rankingSpec);
  }

  function prepareExpandedLibraryItem(item, rankingSpec = {}, runtime = normalization.libraryRankingRuntime(rankingSpec)) {
    const prepared = {...item};
    prepared.row_data = {...(item.row_data || {})};
    prepared.travel_element = item.travel_element ?? prepared.row_data.travel_element ?? '';
    prepared.supplier = item.supplier ?? prepared.row_data.supplier ?? '';
    prepared.type = item.type ?? prepared.row_data.type ?? '';
    prepared.comments = item.comments ?? prepared.row_data.comments ?? '';
    prepared.url = item.url ?? prepared.row_data.url ?? '';
    prepared.label = item.label || buildLibraryLabel(prepared);
    prepared.preview = item.preview || buildLibraryPreview(prepared);
    prepared._normalized_fields = runtime.fieldRules.map((rule) => (
      normalization.normalizeSearchText(librarySearchFieldValue(prepared, rule.name), rankingSpec)
    ));
    prepared._normalized_field_tokens = prepared._normalized_fields.map((text) => text.split(/\s+/).filter(Boolean));
    prepared._normalized_search_blob = prepared._normalized_fields.join(' ');
    prepared._search_bigrams = searchBigramsFromNormalized(prepared._normalized_search_blob);
    prepared._normalized_sheet = normalization.normalizeSearchText(prepared.source_sheet || prepared.category, rankingSpec);
    prepared._normalized_type = normalization.normalizeSearchText(prepared.type || prepared.category, rankingSpec);
    prepared._normalized_country = normalization.normalizeSearchText(prepared.country, rankingSpec);
    prepared._normalized_supplier = normalization.normalizeSearchText(prepared.supplier, rankingSpec);
    prepared._tie_break_values = runtime.tieBreak.map((fieldName) => libraryTieBreakValue(prepared, fieldName, rankingSpec));
    return prepared;
  }

  function expandLibraryItem(item, fieldNames = [], rankingSpec = {}, runtime = normalization.libraryRankingRuntime(rankingSpec)) {
    if (!item || typeof item !== 'object') return prepareExpandedLibraryItem({}, rankingSpec, runtime);
    if (!item.v || typeof item.v !== 'object') return prepareExpandedLibraryItem({...item}, rankingSpec, runtime);

    const rowData = {};
    if (Array.isArray(item.v)) {
      fieldNames.forEach((fieldName, index) => {
        rowData[fieldName] = item.v[index];
      });
    } else {
      Object.entries(item.v).forEach(([index, value]) => {
        const fieldName = fieldNames[Number(index)];
        if (fieldName) rowData[fieldName] = value;
      });
    }
    return prepareExpandedLibraryItem({
      library_id: item.i,
      source_sheet: item.w,
      source_row: item.x,
      country: item.c,
      category: item.g,
      row_data: rowData,
      travel_element: rowData.travel_element,
      supplier: rowData.supplier,
      type: rowData.type,
      comments: rowData.comments,
      url: rowData.url,
    }, rankingSpec, runtime);
  }

  function addLibraryIndexValue(index, key, rowIndex) {
    if (!key) return;
    const values = index.get(key);
    if (values) values.push(rowIndex);
    else index.set(key, [rowIndex]);
  }

  function buildLibrarySearchIndex(rows) {
    const bigrams = new Map();
    const sheets = new Map();
    const types = new Map();
    rows.forEach((item, index) => {
      addLibraryIndexValue(sheets, item._normalized_sheet, index);
      addLibraryIndexValue(types, item._normalized_type, index);
      for (const bigram of item._search_bigrams || []) addLibraryIndexValue(bigrams, bigram, index);
    });
    return {bigrams, sheets, types};
  }

  function prepareLibraryBundle(rawRows, fieldNames = [], fingerprint = '', rankingSpec = {}) {
    const cacheKey = String(fingerprint || '');
    const runtime = normalization.libraryRankingRuntime(rankingSpec);
    if (
      cacheKey
      && cacheKey === preparedLibraryFingerprint
      && runtime.version === preparedLibraryRankingVersion
      && preparedLibraryBundle
    ) {
      return preparedLibraryBundle;
    }

    const rows = (rawRows || []).map((item) => expandLibraryItem(item, fieldNames, rankingSpec, runtime));
    const bundle = {rows, index: buildLibrarySearchIndex(rows)};
    if (cacheKey) {
      preparedLibraryFingerprint = cacheKey;
      preparedLibraryRankingVersion = runtime.version;
      preparedLibraryBundle = bundle;
    }
    return bundle;
  }

  window.ItineraryCalculator.define('library.index', {
    buildLibrarySearchIndex,
    librarySearchFieldValue,
    libraryTieBreakValue,
    prepareLibraryBundle,
    searchBigramsFromNormalized,
  });
})();
