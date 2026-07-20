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
  let score = 0;
  librarySearchFields(item).forEach((field, index) => {
    const text = normalizeSearchText(field);
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
  const itemType = normalizeSearchText(item.type || item.category);
  const sourceSheet = normalizeSearchText(item.source_sheet || item.category);
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

function findLibrarySuggestions(libraryRows, query, limit = 8, context = {}) {
  return (libraryRows || [])
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
