function bindEvents() {
  document.querySelectorAll('[data-action="add"]').forEach((button) => {
    button.addEventListener('click', () => {
      recordHistory();
      calculatorState.rows = calculateRows(addRows(calculatorState.rows, Number(button.dataset.count || 1)), calculatorState.currencyRates);
      markLocalDraft();
      rerender();
    });
  });
  document.querySelector('[data-action="insert-above"]')?.addEventListener('click', () => insertRowsAtSelection('above'));
  document.querySelector('[data-action="insert-below"]')?.addEventListener('click', () => insertRowsAtSelection('below'));
  document.querySelector('[data-action="duplicate"]')?.addEventListener('click', duplicateSelectedRows);
  document.querySelector('[data-action="delete"]')?.addEventListener('click', deleteSelectedRows);
  document.querySelector('[data-action="toggle-advanced"]')?.addEventListener('change', (event) => {
    recordHistory();
    calculatorState.showAdvanced = Boolean(event.target.checked);
    calculatorState.selection = null;
    markLocalDraft();
    rerender();
  });
  document.querySelector('[data-action="undo"]')?.addEventListener('click', undoCalculatorChange);
  document.querySelector('[data-action="redo"]')?.addEventListener('click', redoCalculatorChange);
  document.querySelector('[data-action="fill-down"]')?.addEventListener('click', () => fillSelection('down'));
  document.querySelector('[data-action="fill-right"]')?.addEventListener('click', () => fillSelection('right'));
  document.querySelector('[data-action="find-replace"]')?.addEventListener('click', () => toggleFindReplace());
  document.querySelector('[data-action="version-history"]')?.addEventListener('click', () => { calculatorState.showVersionHistory = !calculatorState.showVersionHistory; rerender(); });
  document.querySelector('[data-action="close-versions"]')?.addEventListener('click', () => { calculatorState.showVersionHistory = false; rerender(); });
  document.querySelector('[data-action="clear-versions"]')?.addEventListener('click', () => { clearCalculatorRecoverySnapshots(); calculatorState.showVersionHistory = false; rerender(); });
  document.querySelectorAll('[data-version-id]').forEach((button) => button.addEventListener('click', () => restoreCalculatorRecoverySnapshot(button.dataset.versionId)));
  document.querySelector('[data-action="close"]')?.addEventListener('click', () => submitAction('close'));
  document.querySelector('[data-action="open-library"]')?.addEventListener('click', () => submitAction('open_library'));
  document.querySelector('[data-action="download"]')?.addEventListener('click', () => {
    if (calculatorState.pendingDownload?.content_base64) downloadPreparedExcel(calculatorState.pendingDownload);
    else submitAction('download');
  });
  document.querySelector('[data-action="generate-agent"]')?.addEventListener('click', () => submitAction('generate_agent'));
  document.querySelector('[data-action="generate-customer"]')?.addEventListener('click', () => submitAction('generate_customer'));
  document.querySelector('[data-action="toggle-fullscreen"]')?.addEventListener('click', toggleCalculatorFullscreen);
  document.querySelectorAll('[data-action="sales-margin"]').forEach((button) => {
    button.addEventListener('click', () => applySalesMargin(Number(button.dataset.margin || 0)));
  });
  document.querySelector('[data-action="sales-price-use-gross"]')?.addEventListener('click', useGrossAsSalesPrice);

  const paxInput = document.querySelector('[data-action="set-pax"]');
  paxInput?.addEventListener('focus', beginCellEdit);
  paxInput?.addEventListener('input', (event) => {
    calculatorState.numberOfPax = event.target.value;
    markLocalDraft(false, false);
    refreshTotalsOnly();
    refreshValidationAndStatus();
  });
  paxInput?.addEventListener('blur', commitCellEdit);

  const formulaBar = document.querySelector('[data-action="formula-bar"]');
  formulaBar?.addEventListener('focus', beginCellEdit);
  formulaBar?.addEventListener('input', (event) => updateActiveCellFromFormulaBar(event.target.value));
  formulaBar?.addEventListener('blur', commitCellEdit);
  formulaBar?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      event.currentTarget.blur();
    }
  });

  document.querySelectorAll('.calc-row').forEach((rowElement) => {
    rowElement.addEventListener('mousedown', () => {
      calculatorState.selectedRowIndex = Number(rowElement.dataset.rowIndex || 0);
      document.querySelectorAll('.calc-row').forEach((row) => row.classList.remove('selected-row'));
      rowElement.classList.add('selected-row');
    });
  });

  document.querySelectorAll('td.editable').forEach((cell) => {
    cell.addEventListener('mousedown', handleCellMouseDown);
    cell.addEventListener('mouseenter', handleCellMouseEnter);
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
  bindClipboardEvents();
  bindAdvancedCalculatorEvents();
  restoreActiveCellFocus();
}

function applySalesMargin(margin) {
  if (!activeCell || activeCell.key !== 'sales_price_per_unit') return;
  if (!(margin > 0 && margin < 1)) return;
  const rowIndex = activeCell.rowIndex;
  const row = calculatorState.rows[rowIndex];
  if (!row) return;
  const evaluator = new CalculatorGridFormulaEvaluator(calculatorState.rows, calculatorState.currencyRates);
  let gross;
  try {
    gross = evaluator.evaluateCell(`Q${CALCULATOR_DATA_START_ROW + rowIndex}`);
  } catch (_error) {
    gross = numberValue(row.gross_price_per_unit);
  }
  if (!Number.isFinite(gross) || gross <= 0) {
    calculatorState.syncStatus = 'Enter a gross price first';
    refreshSyncStatusOnly();
    return;
  }
  recordHistory();
  row._sales_price_per_unit_touched = true;
  row.sales_price_per_unit = gross / (1 - margin);
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  markLocalDraft();
  rerender();
}

function useGrossAsSalesPrice() {
  if (!activeCell || activeCell.key !== 'sales_price_per_unit') return;
  const row = calculatorState.rows[activeCell.rowIndex];
  if (!row) return;
  recordHistory();
  row._sales_price_per_unit_touched = false;
  row.sales_price_per_unit = null;
  calculatorState.rows = calculateRows(calculatorState.rows, calculatorState.currencyRates);
  markLocalDraft();
  rerender();
}

function downloadPreparedExcel(download) {
  const encoded = String(download?.content_base64 || '');
  if (!encoded) return;
  const binary = window.atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  const blob = new Blob([bytes], {type: String(download.mime || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')});
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = String(download.filename || 'itinerary-calculation.xlsx');
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  calculatorState.syncStatus = 'Excel downloaded';
  refreshSyncStatusOnly();
}

function submitAction(action) {
  commitCellEdit();
  flushLocalDraftSave();
  flushRecoverySnapshot();
  calculateRows(calculatorState.rows, calculatorState.currencyRates);
  const errors = validateCalculatorState(calculatorState);
  if (errors.length) {
    calculatorState.syncStatus = 'Fix validation errors';
    refreshValidationAndStatus();
    return;
  }
  saveCalculatorDraft(calculatorState, activeBackendRevision);
  const rows = normalizeRowsForPython(calculatorState.rows);
  calculatorState.dirty = false;
  calculatorState.syncStatus = action === 'sync' ? 'Syncing…' : 'Preparing latest grid…';
  refreshSyncStatusOnly();
  Streamlit.setComponentValue(JSON.stringify({
    action,
    rows,
    number_of_pax: positiveIntegerOrNull(calculatorState.numberOfPax),
    show_advanced: calculatorState.showAdvanced,
    client_state_revision: activeBackendRevision
  }));
}

function handleGlobalCalculatorShortcut(event) {
  const modifier = event.ctrlKey || event.metaKey;
  if (!modifier) return;
  const key = event.key.toLowerCase();
  if (key === 'z' && !event.shiftKey) {
    event.preventDefault();
    undoCalculatorChange();
  } else if (key === 'y' || (key === 'z' && event.shiftKey)) {
    event.preventDefault();
    redoCalculatorChange();
  } else if (key === 'd') {
    event.preventDefault();
    fillSelection('down');
  } else if (key === 'r') {
    event.preventDefault();
    fillSelection('right');
  } else if (key === 'f' || key === 'h') {
    event.preventDefault();
    toggleFindReplace(true);
  }
}

document.addEventListener('keydown', handleGlobalCalculatorShortcut);

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState !== 'hidden' || !calculatorState?.dirty) return;
  flushLocalDraftSave();
  flushRecoverySnapshot();
});

window.addEventListener('beforeunload', (event) => {
  if (!calculatorState?.dirty) return;
  flushLocalDraftSave();
  flushRecoverySnapshot();
  event.preventDefault();
  event.returnValue = '';
});
