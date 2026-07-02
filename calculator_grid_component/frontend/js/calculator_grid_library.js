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
    item.type,
    item.comments,
    item.search_text,
    item.url,
    item.label,
    item.preview
  ];
}

function scoreLibraryItem(item, query) {
  const normalizedQuery = normalizeSearchText(query);
  if (normalizedQuery.length < 2) return 0;
  const tokens = normalizedQuery.split(/\s+/).filter(Boolean);
  const fieldWeights = [60, 38, 25, 25, 25, 15, 10, 5, 10, 8];
  let score = 0;
  librarySearchFields(item).forEach((field, index) => {
    const text = normalizeSearchText(field);
    if (!text) return;
    let fieldScore = 0;
    for (const token of tokens) {
      if (text === token) fieldScore += 5;
      else if (text.startsWith(token)) fieldScore += 4;
      else if (text.includes(token)) fieldScore += 2;
    }
    if (text.includes(normalizedQuery)) fieldScore += 5;
    score += fieldScore * fieldWeights[index];
  });
  return score;
}

function findLibrarySuggestions(libraryRows, query, limit = 8) {
  return (libraryRows || [])
    .map((item) => ({item, score: scoreLibraryItem(item, query)}))
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score || String(a.item.label || '').localeCompare(String(b.item.label || '')))
    .slice(0, limit);
}

function applyLibrarySuggestion(row, suggestion) {
  const fetched = {...(suggestion.row_data || {})};
  const grossPerUnit = numberValue(fetched.gross_price_per_unit);
  if (grossPerUnit > 0 && optionalNumberValue(fetched.supplier_commission) === 0) {
    fetched.supplier_commission = DEFAULT_SUPPLIER_COMMISSION_PERCENT;
  }
  if (grossPerUnit > 0 && optionalNumberValue(fetched.sales_price_per_unit) === 0) {
    fetched.sales_price_per_unit = '';
  }
  const preserved = {
    row_id: row.row_id,
    day: row.day || fetched.day || '',
    from_date: row.from_date || fetched.from_date || '',
    to_date: row.to_date || fetched.to_date || '',
    from_time: row.from_time || fetched.from_time || '',
    to_time: row.to_time || fetched.to_time || ''
  };
  return {...fetched, ...preserved, _supplier_commission_touched: false, _sales_price_per_unit_touched: false};
}
