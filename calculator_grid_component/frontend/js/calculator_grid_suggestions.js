let suggestionDebounceTimer = null;
const SUGGESTION_MIN_QUERY_LENGTH = 3;
const SUGGESTION_DEBOUNCE_MS = 180;

function scheduleSuggestions(rowIndex, query) {
  window.clearTimeout(suggestionDebounceTimer);
  const text = String(query || '').trim();
  if (text.length < SUGGESTION_MIN_QUERY_LENGTH) {
    calculatorState.activeSuggestion = null;
    renderSuggestionPanelOnly();
    return;
  }
  suggestionDebounceTimer = window.setTimeout(() => {
    if (!activeCell || activeCell.rowIndex !== rowIndex || activeCell.key !== 'travel_element') return;
    const focused = document.activeElement;
    if (!focused || focused.dataset?.rowIndex !== String(rowIndex) || focused.dataset?.key !== 'travel_element') return;
    updateSuggestions(rowIndex, focused.textContent || text);
    renderSuggestionPanelOnly();
  }, SUGGESTION_DEBOUNCE_MS);
}

function updateSuggestions(rowIndex, query) {
  const text = String(query || '').trim();
  if (text.length < SUGGESTION_MIN_QUERY_LENGTH) {
    calculatorState.activeSuggestion = null;
    return;
  }
  calculatorState.activeSuggestion = {
    rowIndex,
    query: text,
    results: window.ItineraryCalculator.library.findSuggestions(
      calculatorState.libraryRows,
      text,
      8,
      calculatorState.rows[rowIndex] || {},
      calculatorState.libraryIndex,
      calculatorState.libraryRankingSpec
    )
  };
}

function applySuggestion(index) {
  const active = calculatorState.activeSuggestion;
  if (!active || !active.results[index]) return;
  recordHistory();
  const row = calculatorState.rows[active.rowIndex];
  calculatorState.rows[active.rowIndex] = window.ItineraryCalculator.library.applySuggestion(row, active.results[index].item);
  autofillDatesFromArrival(calculatorState.rows);
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  calculatorState.activeSuggestion = null;
  activeCell = {rowIndex: active.rowIndex, key: 'travel_element'};
  activeCellEditing = false;
  setSingleCellSelection(active.rowIndex, 'travel_element');
  markLocalDraft();
  rerender();
}

function renderSuggestionPanelOnly() {
  const oldPanel = document.querySelector('.suggestion-panel');
  if (oldPanel) oldPanel.remove();
  const html = buildSuggestionHtml(calculatorState);
  if (!html) return;
  document.querySelector('.calculator-grid-shell').insertAdjacentHTML('beforeend', html);
  document.querySelectorAll('.suggestion-item').forEach((button) => {
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      applySuggestion(Number(button.dataset.suggestionIndex || 0));
    });
  });
}
