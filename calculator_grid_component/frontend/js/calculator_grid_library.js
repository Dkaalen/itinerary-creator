let preparedLibraryFingerprint = '';
let preparedLibraryRankingVersion = '';
let preparedLibraryBundle = null;
let preparedNormalizationVersion = '';
let preparedNormalizationRuntime = null;
let preparedRankingRuntimeVersion = '';
let preparedRankingRuntime = null;

function normalizationRuntime(rankingSpec = {}) {
  const version = String(rankingSpec.version || '');
  if (version && version === preparedNormalizationVersion && preparedNormalizationRuntime) {
    return preparedNormalizationRuntime;
  }
  const normalization = rankingSpec.normalization || {};
  const runtime = {
    unicodeForm: String(normalization.unicode_form || 'NFKD'),
    transliteration: Object.entries(normalization.transliteration || {}).map(([source, replacement]) => (
      [String(source), String(replacement)]
    ))
  };
  if (version) {
    preparedNormalizationVersion = version;
    preparedNormalizationRuntime = runtime;
  }
  return runtime;
}

function normalizeSearchText(value, rankingSpec = {}) {
  const runtime = normalizationRuntime(rankingSpec);
  let text = String(value || '').toLowerCase();
  for (const [source, replacement] of runtime.transliteration) {
    text = text.split(source).join(replacement);
  }
  return text
    .normalize(runtime.unicodeForm)
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function libraryRankingRuntime(rankingSpec = {}) {
  const version = String(rankingSpec.version || '');
  if (version && version === preparedRankingRuntimeVersion && preparedRankingRuntime) {
    return preparedRankingRuntime;
  }
  const runtime = {
    version,
    minimumQueryLength: Number(rankingSpec.minimum_query_length || 2),
    fieldRules: Array.isArray(rankingSpec.search_fields)
      ? rankingSpec.search_fields.filter((rule) => rule && rule.name).map((rule) => ({
          name: String(rule.name),
          weight: Number(rule.weight || 0)
        }))
      : [],
    matchWeights: Object.fromEntries(
      Object.entries(rankingSpec.match_weights || {}).map(([key, value]) => [key, Number(value || 0)])
    ),
    contextWeights: Object.fromEntries(
      Object.entries(rankingSpec.context_weights || {}).map(([key, value]) => [key, Number(value || 0)])
    ),
    routes: (rankingSpec.sheet_routes || []).map((route) => ({
      sheet: normalizeSearchText(route.sheet, rankingSpec),
      terms: (route.terms || []).map((term) => normalizeSearchText(term, rankingSpec)).filter(Boolean)
    })),
    aliases: (rankingSpec.cross_type_aliases || []).map((alias) => ({
      id: String(alias.id || ''),
      phrase: normalizeSearchText(alias.phrase, rankingSpec),
      contextTypes: normalizedAliasValues(alias.context_types, rankingSpec),
      contextSheets: normalizedAliasValues(alias.context_sheets, rankingSpec),
      sourceTypes: normalizedAliasValues(alias.source_types, rankingSpec),
      sourceSheets: normalizedAliasValues(alias.source_sheets, rankingSpec)
    })),
    tieBreak: Array.isArray(rankingSpec.tie_break) ? rankingSpec.tie_break.map(String) : []
  };
  if (version) {
    preparedRankingRuntimeVersion = version;
    preparedRankingRuntime = runtime;
  }
  return runtime;
}

function prepareLibraryBundle(rawRows, fieldNames = [], fingerprint = '', rankingSpec = {}) {
  const cacheKey = String(fingerprint || '');
  const runtime = libraryRankingRuntime(rankingSpec);
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

function expandLibraryItem(item, fieldNames = [], rankingSpec = {}, runtime = libraryRankingRuntime(rankingSpec)) {
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
    url: rowData.url
  }, rankingSpec, runtime);
}

function prepareExpandedLibraryItem(item, rankingSpec = {}, runtime = libraryRankingRuntime(rankingSpec)) {
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
    normalizeSearchText(librarySearchFieldValue(prepared, rule.name), rankingSpec)
  ));
  prepared._normalized_field_tokens = prepared._normalized_fields.map((text) => text.split(/\s+/).filter(Boolean));
  prepared._normalized_search_blob = prepared._normalized_fields.join(' ');
  prepared._search_bigrams = searchBigramsFromNormalized(prepared._normalized_search_blob);
  prepared._normalized_sheet = normalizeSearchText(prepared.source_sheet || prepared.category, rankingSpec);
  prepared._normalized_type = normalizeSearchText(prepared.type || prepared.category, rankingSpec);
  prepared._normalized_country = normalizeSearchText(prepared.country, rankingSpec);
  prepared._normalized_supplier = normalizeSearchText(prepared.supplier, rankingSpec);
  prepared._tie_break_values = runtime.tieBreak.map((fieldName) => libraryTieBreakValue(prepared, fieldName, rankingSpec));
  return prepared;
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
    item.url
  ];
  return parts.filter(Boolean).join(' • ').slice(0, 450);
}

function librarySearchFieldValue(item, fieldName) {
  if (Object.prototype.hasOwnProperty.call(item, fieldName)) return item[fieldName];
  return (item.row_data || {})[fieldName] ?? '';
}

function prepareLibrarySearchRequest(query, context = {}, rankingSpec = {}, runtime = libraryRankingRuntime(rankingSpec)) {
  const normalizedQuery = normalizeSearchText(query, rankingSpec);
  const rowType = normalizeSearchText(context.type, rankingSpec);
  const expectedSheet = expectedLibrarySheetFromRuntime(rowType, context.travel_element, rankingSpec, runtime);
  const aliases = runtime.aliases.filter((alias) => (
    alias.phrase
    && normalizedQuery.includes(alias.phrase)
    && alias.contextTypes.includes(rowType)
    && (!expectedSheet || alias.contextSheets.includes(expectedSheet))
  ));
  return {
    normalizedQuery,
    queryTokens: normalizedQuery.split(/\s+/).filter(Boolean),
    rowType,
    expectedSheet,
    rowText: normalizeSearchText(
      [context.travel_element, context.supplier, context.comments].filter(Boolean).join(' '),
      rankingSpec
    ),
    contextSupplier: normalizeSearchText(context.supplier, rankingSpec),
    aliases,
    runtime
  };
}

function scoreLibraryItem(item, query, context = {}, rankingSpec = {}) {
  const runtime = libraryRankingRuntime(rankingSpec);
  const request = prepareLibrarySearchRequest(query, context, rankingSpec, runtime);
  return scorePreparedLibraryItem(item, request);
}

function scorePreparedLibraryItem(item, request) {
  if (request.normalizedQuery.length < request.runtime.minimumQueryLength) return 0;
  let score = 0;
  item._normalized_fields.forEach((text, index) => {
    const fieldScore = libraryFieldMatchScore(
      text,
      item._normalized_field_tokens[index] || [],
      request.normalizedQuery,
      request.queryTokens,
      request.runtime.matchWeights
    );
    score += fieldScore * Number(request.runtime.fieldRules[index]?.weight || 0);
  });
  return score + preparedContextScore(item, request);
}

function libraryFieldMatchScore(text, fieldTokens, normalizedQuery, queryTokens, matchWeights = {}) {
  if (!text) return 0;
  let score = 0;
  if (text === normalizedQuery) score += matchWeights.query_exact || 0;
  else if (text.startsWith(normalizedQuery)) score += matchWeights.query_prefix || 0;
  else if (text.includes(normalizedQuery)) score += matchWeights.query_contains || 0;

  for (const token of queryTokens) {
    if (fieldTokens.includes(token)) score += matchWeights.token_exact || 0;
    else if (fieldTokens.some((fieldToken) => fieldToken.startsWith(token))) score += matchWeights.token_prefix || 0;
    else if (text.includes(token)) score += matchWeights.token_contains || 0;
  }
  return score;
}

function preparedContextScore(item, request) {
  const weights = request.runtime.contextWeights;
  const alias = matchingPreparedCrossTypeAlias(item, request);
  let score = 0;
  if (request.expectedSheet && item._normalized_sheet) {
    if (item._normalized_sheet === request.expectedSheet) score += weights.sheet_exact || 0;
    else if (alias) score += weights.sheet_alias || 0;
    else score += weights.sheet_mismatch || 0;
  }
  if (request.rowType && item._normalized_type) {
    if (item._normalized_type === request.rowType) score += weights.type_exact || 0;
    else if (alias) score += weights.type_alias || 0;
    else if (item._normalized_type.includes(request.rowType) || request.rowType.includes(item._normalized_type)) {
      score += weights.type_partial || 0;
    } else score += weights.type_mismatch || 0;
  }
  if (item._normalized_country && request.rowText.includes(item._normalized_country)) {
    score += weights.country_in_context || 0;
  }
  if (item._normalized_supplier && request.contextSupplier === item._normalized_supplier) {
    score += weights.supplier_exact || 0;
  }
  if (item._normalized_supplier && request.rowText.includes(item._normalized_supplier)) {
    score += weights.supplier_in_context || 0;
  }
  return score;
}

function expectedLibrarySheet(rowType, travelElement, rankingSpec = {}) {
  return expectedLibrarySheetFromRuntime(rowType, travelElement, rankingSpec, libraryRankingRuntime(rankingSpec));
}

function expectedLibrarySheetFromRuntime(rowType, travelElement, rankingSpec, runtime) {
  const text = normalizeSearchText(`${rowType || ''} ${travelElement || ''}`, rankingSpec);
  for (const route of runtime.routes) {
    if (route.terms.some((term) => text.includes(term))) return route.sheet;
  }
  return '';
}

function matchingPreparedCrossTypeAlias(item, request) {
  for (const alias of request.aliases) {
    if (!item._normalized_search_blob.includes(alias.phrase)) continue;
    if (!alias.sourceTypes.includes(item._normalized_type)) continue;
    if (!alias.sourceSheets.includes(item._normalized_sheet)) continue;
    return alias;
  }
  return null;
}

function normalizedAliasValues(values, rankingSpec = {}) {
  return (values || []).map((value) => normalizeSearchText(value, rankingSpec)).filter(Boolean);
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

function addLibraryIndexValue(index, key, rowIndex) {
  if (!key) return;
  const values = index.get(key);
  if (values) values.push(rowIndex);
  else index.set(key, [rowIndex]);
}

function searchBigramsFromNormalized(value) {
  const text = String(value || '').replaceAll(' ', '_');
  const result = new Set();
  if (text.length < 2) return result;
  for (let index = 0; index < text.length - 1; index += 1) result.add(text.slice(index, index + 2));
  return result;
}

function candidateLibraryIndexes(libraryRows, request, searchIndex) {
  if (!searchIndex) return libraryRows.map((_item, index) => index);
  const candidates = new Set();
  for (const bigram of searchBigramsFromNormalized(request.normalizedQuery)) {
    for (const index of searchIndex.bigrams.get(bigram) || []) candidates.add(index);
  }
  for (const index of searchIndex.sheets.get(request.expectedSheet) || []) candidates.add(index);
  for (const index of searchIndex.types.get(request.rowType) || []) candidates.add(index);
  return candidates.size ? [...candidates] : libraryRows.map((_item, index) => index);
}

function findLibrarySuggestions(libraryRows, query, limit = 8, context = {}, searchIndex = null, rankingSpec = {}) {
  const runtime = libraryRankingRuntime(rankingSpec);
  const request = prepareLibrarySearchRequest(query, context, rankingSpec, runtime);
  return candidateLibraryIndexes(libraryRows || [], request, searchIndex)
    .map((index) => libraryRows[index])
    .filter(Boolean)
    .map((item) => ({item, score: scorePreparedLibraryItem(item, request)}))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score || compareLibraryItems(a.item, b.item, rankingSpec, runtime))
    .slice(0, limit);
}

function libraryTieBreakValue(item, fieldName, rankingSpec = {}) {
  if (fieldName === 'source_row') {
    const raw = item.source_row;
    return raw !== null && raw !== undefined && String(raw).trim() !== '' && Number.isFinite(Number(raw))
      ? Number(raw)
      : Number.MAX_SAFE_INTEGER;
  }
  return normalizeSearchText(librarySearchFieldValue(item, fieldName), rankingSpec);
}

function compareLibraryItems(left, right, rankingSpec = {}, runtime = libraryRankingRuntime(rankingSpec)) {
  const leftValues = left._tie_break_values || runtime.tieBreak.map((fieldName) => libraryTieBreakValue(left, fieldName, rankingSpec));
  const rightValues = right._tie_break_values || runtime.tieBreak.map((fieldName) => libraryTieBreakValue(right, fieldName, rankingSpec));
  for (let index = 0; index < runtime.tieBreak.length; index += 1) {
    const leftValue = leftValues[index];
    const rightValue = rightValues[index];
    if (leftValue < rightValue) return -1;
    if (leftValue > rightValue) return 1;
  }
  return 0;
}

function applyLibrarySuggestion(row, suggestion) {
  const fetched = {...(suggestion.row_data || {})};
  const grossPerUnit = numberValue(fetched.gross_price_per_unit);
  const rawSalesPrice = fetched.sales_price_per_unit;
  const parsedSalesPrice = optionalNumberValue(rawSalesPrice);
  const hasExplicitSalesPrice = rawSalesPrice !== null
    && rawSalesPrice !== undefined
    && String(rawSalesPrice).trim() !== ''
    && !(parsedSalesPrice === 0 && grossPerUnit > 0);
  if (!hasExplicitSalesPrice) {
    fetched.sales_price_per_unit = '';
    fetched.sales_currency = row.sales_currency || DEFAULT_CURRENCY;
  }
  const preserved = {
    row_id: row.row_id,
    day: row.day || fetched.day || '',
    from_date: row.from_date || fetched.from_date || '',
    to_date: row.to_date || fetched.to_date || '',
    from_time: row.from_time || fetched.from_time || '',
    to_time: row.to_time || fetched.to_time || ''
  };
  return {
    ...fetched,
    ...preserved,
    _supplier_commission_touched: false,
    _sales_price_per_unit_touched: hasExplicitSalesPrice
  };
}
