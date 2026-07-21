let preparedLibraryFingerprint = '';
let preparedLibraryBundle = null;

function normalizeSearchText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replaceAll('ø', 'o')
    .replaceAll('Ø', 'O')
    .replaceAll('æ', 'ae')
    .replaceAll('Æ', 'AE')
    .replaceAll('å', 'a')
    .replaceAll('Å', 'A')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function prepareLibraryBundle(rawRows, fieldNames = [], fingerprint = '') {
  const cacheKey = String(fingerprint || '');
  if (cacheKey && cacheKey === preparedLibraryFingerprint && preparedLibraryBundle) {
    return preparedLibraryBundle;
  }

  const rows = (rawRows || []).map((item) => expandLibraryItem(item, fieldNames));
  const bundle = {rows, index: buildLibrarySearchIndex(rows)};
  if (cacheKey) {
    preparedLibraryFingerprint = cacheKey;
    preparedLibraryBundle = bundle;
  }
  return bundle;
}

function expandLibraryItem(item, fieldNames = []) {
  if (!item || typeof item !== 'object') return prepareExpandedLibraryItem({});
  if (!item.v || typeof item.v !== 'object') return prepareExpandedLibraryItem({...item});

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
  });
}

function prepareExpandedLibraryItem(item) {
  const prepared = {...item};
  prepared.row_data = {...(item.row_data || {})};
  prepared.travel_element = item.travel_element ?? prepared.row_data.travel_element ?? '';
  prepared.supplier = item.supplier ?? prepared.row_data.supplier ?? '';
  prepared.type = item.type ?? prepared.row_data.type ?? '';
  prepared.comments = item.comments ?? prepared.row_data.comments ?? '';
  prepared.url = item.url ?? prepared.row_data.url ?? '';
  prepared.label = item.label || buildLibraryLabel(prepared);
  prepared.preview = item.preview || buildLibraryPreview(prepared);
  prepared._normalized_fields = librarySearchFields(prepared).map(normalizeSearchText);
  prepared._search_bigrams = searchBigrams(prepared._normalized_fields.join(' '));
  prepared._normalized_sheet = normalizeSearchText(prepared.source_sheet || prepared.category);
  prepared._normalized_type = normalizeSearchText(prepared.type || prepared.category);
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

function librarySearchFields(item) {
  return [
    item.travel_element,
    item.supplier,
    item.country,
    item.category,
    item.source_sheet,
    item.type,
    item.comments,
    item.search_text,
    item.url,
    item.label,
    item.preview
  ];
}

function scoreLibraryItem(item, query, context = {}) {
  const normalizedQuery = normalizeSearchText(query);
  if (normalizedQuery.length < 2) return 0;
  const tokens = normalizedQuery.split(/\s+/).filter(Boolean);
  const fieldWeights = [70, 42, 25, 28, 34, 34, 12, 10, 3, 12, 8];
  const normalizedFields = item._normalized_fields || librarySearchFields(item).map(normalizeSearchText);
  let score = 0;
  normalizedFields.forEach((text, index) => {
    if (!text) return;
    let fieldScore = 0;
    for (const token of tokens) {
      if (text === token) fieldScore += 6;
      else if (text.startsWith(token)) fieldScore += 5;
      else if (text.includes(token)) fieldScore += 2;
    }
    if (text.includes(normalizedQuery)) fieldScore += 6;
    score += fieldScore * fieldWeights[index];
  });
  return score + contextScore(item, context);
}

function contextScore(item, context = {}) {
  let score = 0;
  const rowType = normalizeSearchText(context.type);
  const itemType = item._normalized_type || normalizeSearchText(item.type || item.category);
  const sourceSheet = item._normalized_sheet || normalizeSearchText(item.source_sheet || item.category);
  const expectedSheet = expectedLibrarySheet(rowType, normalizeSearchText(context.travel_element));
  if (expectedSheet && sourceSheet) {
    if (sourceSheet === expectedSheet) score += 1400;
    else score -= 220;
  }
  if (rowType && itemType) {
    if (itemType === rowType) score += 900;
    else if (itemType.includes(rowType) || rowType.includes(itemType)) score += 450;
    else score -= 160;
  }
  const rowText = normalizeSearchText([context.travel_element, context.supplier, context.comments].filter(Boolean).join(' '));
  const country = normalizeSearchText(item.country);
  const supplier = normalizeSearchText(item.supplier);
  if (country && rowText.includes(country)) score += 300;
  if (supplier && normalizeSearchText(context.supplier) === supplier) score += 360;
  if (supplier && rowText.includes(supplier)) score += 180;
  return score;
}

function expectedLibrarySheet(rowType, travelElement) {
  const text = `${rowType} ${travelElement}`;
  if (/hotel|accommodation|overnight/.test(text)) return 'hotels';
  if (/transfer|airport|station|pickup|drop off/.test(text)) return 'transfers';
  if (/coach|train|rail|flight|ferry|boat|transport/.test(text)) return 'transport';
  if (/activity|tour|museum|excursion|visit|experience/.test(text)) return 'activities';
  if (/arrival|departure|leisure|welcome/.test(text)) return 'general';
  return '';
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

function searchBigrams(value) {
  const text = normalizeSearchText(value).replaceAll(' ', '_');
  const result = new Set();
  if (text.length < 2) return result;
  for (let index = 0; index < text.length - 1; index += 1) result.add(text.slice(index, index + 2));
  return result;
}

function candidateLibraryIndexes(libraryRows, query, context, searchIndex) {
  if (!searchIndex) return libraryRows.map((_item, index) => index);
  const candidates = new Set();
  for (const bigram of searchBigrams(query)) {
    for (const index of searchIndex.bigrams.get(bigram) || []) candidates.add(index);
  }

  const expectedSheet = expectedLibrarySheet(normalizeSearchText(context.type), normalizeSearchText(context.travel_element));
  for (const index of searchIndex.sheets.get(expectedSheet) || []) candidates.add(index);
  const rowType = normalizeSearchText(context.type);
  for (const index of searchIndex.types.get(rowType) || []) candidates.add(index);

  return candidates.size ? [...candidates] : libraryRows.map((_item, index) => index);
}

function findLibrarySuggestions(libraryRows, query, limit = 8, context = {}, searchIndex = null) {
  return candidateLibraryIndexes(libraryRows || [], query, context, searchIndex)
    .map((index) => libraryRows[index])
    .filter(Boolean)
    .map((item) => ({item, score: scoreLibraryItem(item, query, context)}))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score || String(a.item.source_sheet || '').localeCompare(String(b.item.source_sheet || '')) || Number(a.item.source_row || 0) - Number(b.item.source_row || 0) || String(a.item.label || '').localeCompare(String(b.item.label || '')))
    .slice(0, limit);
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
