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
  document.querySelector('[data-action="download"]')?.addEventListener('click', () => submitAction('download'));
  document.querySelector('[data-action="generate-agent"]')?.addEventListener('click', () => submitAction('generate_agent'));
  document.querySelector('[data-action="generate-customer"]')?.addEventListener('click', () => submitAction('generate_customer'));
  document.querySelector('[data-action="toggle-fullscreen"]')?.addEventListener('click', toggleCalculatorFullscreen);

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
