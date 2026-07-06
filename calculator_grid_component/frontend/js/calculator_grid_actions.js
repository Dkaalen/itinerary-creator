function bindEvents() {
  document.querySelectorAll('[data-action="add"]').forEach((button) => {
    button.addEventListener('click', () => {
      calculatorState.rows = calculateRows(addRows(calculatorState.rows, Number(button.dataset.count || 1)), calculatorState.currencyRates);
      markLocalDraft();
      rerender();
    });
  });
  document.querySelector('[data-action="duplicate"]')?.addEventListener('click', () => {
    calculatorState.rows = calculateRows(duplicateRow(calculatorState.rows, calculatorState.selectedRowIndex), calculatorState.currencyRates);
    markLocalDraft();
    rerender();
  });
  document.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
    calculatorState.rows = calculateRows(deleteRow(calculatorState.rows, calculatorState.selectedRowIndex), calculatorState.currencyRates);
    calculatorState.selectedRowIndex = Math.min(calculatorState.selectedRowIndex, calculatorState.rows.length - 1);
    markLocalDraft();
    rerender();
  });
  document.querySelector('[data-action="toggle-advanced"]')?.addEventListener('change', (event) => {
    calculatorState.showAdvanced = Boolean(event.target.checked);
    markLocalDraft();
    rerender();
  });
  document.querySelector('[data-action="download"]')?.addEventListener('click', () => submitAction('download'));
  document.querySelector('[data-action="download-ready"]')?.addEventListener('click', () => triggerPendingDownload(calculatorState, true));
  document.querySelector('[data-action="generate-agent"]')?.addEventListener('click', () => submitAction('generate_agent'));
  document.querySelector('[data-action="generate-customer"]')?.addEventListener('click', () => submitAction('generate_customer'));
  document.querySelector('[data-action="toggle-fullscreen"]')?.addEventListener('click', toggleCalculatorFullscreen);

  document.querySelectorAll('.calc-row').forEach((rowElement) => {
    rowElement.addEventListener('mousedown', () => {
      calculatorState.selectedRowIndex = Number(rowElement.dataset.rowIndex || 0);
      document.querySelectorAll('.calc-row').forEach((row) => row.classList.remove('selected-row'));
      rowElement.classList.add('selected-row');
    });
  });

  document.querySelectorAll('td.editable').forEach((cell) => {
    cell.addEventListener('focus', handleCellFocus);
    cell.addEventListener('input', handleCellInput);
    cell.addEventListener('keydown', handleCellKeydown);
    cell.addEventListener('blur', handleCellBlur);
  });
  document.querySelectorAll('td.checkbox-cell input').forEach((checkbox) => {
    checkbox.addEventListener('change', handleCheckboxChange);
  });
  document.querySelectorAll('.suggestion-item').forEach((button) => {
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      applySuggestion(Number(button.dataset.suggestionIndex || 0));
    });
  });
}

function submitAction(action) {
  calculateRows(calculatorState.rows, calculatorState.currencyRates);
  saveCalculatorDraft(calculatorState, activeBackendRevision);
  const rows = normalizeRowsForPython(calculatorState.rows);
  Streamlit.setComponentValue(JSON.stringify({
    action,
    rows,
    show_advanced: calculatorState.showAdvanced,
    client_state_revision: activeBackendRevision
  }));
}
