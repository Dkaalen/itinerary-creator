// Dedicated Calculator rendering owner.

function buildSuggestionHtml(state) {
  if (!state.activeSuggestion) return '';
  const {rowIndex, query, results} = state.activeSuggestion;
  if (!results.length) return `<div class="suggestion-panel"><div class="suggestion-empty">No Local Library matches for “${escapeHtml(query)}”.</div></div>`;
  const buttons = results.map((result, index) => {
    const item = result.item;
    return `<button class="suggestion-item" data-suggestion-index="${index}"><strong>${escapeHtml(item.label || item.travel_element || item.library_id)}</strong><span>${escapeHtml(item.preview || '')}</span></button>`;
  }).join('');
  return `<div class="suggestion-panel"><div class="suggestion-title">Suggestions for row ${escapeHtml(state.rows[rowIndex]?.row_id || rowIndex + 1)}: “${escapeHtml(query)}”</div>${buttons}</div>`;
}
