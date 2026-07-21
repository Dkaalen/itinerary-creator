function buildToolbarHtml(state) {
  const libraryText = state.libraryStatus || 'Local Library status unknown.';
  const undoDisabled = state.undoStack.length ? '' : 'disabled';
  const redoDisabled = state.redoStack.length ? '' : 'disabled';
  const excelReady = Boolean(state.pendingDownload?.content_base64);
  const excelClass = excelReady ? 'calc-btn primary ready' : 'calc-btn primary';
  const excelTitle = excelReady ? 'Excel ready — click to download' : 'Create and download the current calculation workbook';
  return `
    <div class="calculator-toolbar">
      <div class="calculator-toolbar-main-row">
        <div class="toolbar-group toolbar-group-navigation" aria-label="Workspace">
          <button class="calc-btn" data-action="close" title="Return to the main workspace">Back</button>
          <button class="calc-btn" data-action="open-library" title="View workbook source and refresh status">Local Library</button>
        </div>
        <div class="toolbar-group toolbar-group-delivery" aria-label="Delivery actions">
          <input class="calculator-excel-file-input" data-action="excel-file-input" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden>
          <button class="calc-btn" data-action="open-excel" title="Open a local calculation Excel file in this Calculator">Open project</button>
          <button class="${excelClass}" data-action="download" title="${excelTitle}">Download Excel</button>
          <button class="calc-btn" data-action="generate-agent" title="Build an itinerary for an agent">Agent itinerary</button>
          <button class="calc-btn" data-action="generate-customer" title="Build a customer-facing itinerary">Customer itinerary</button>
        </div>
      </div>
      <div class="calculator-toolbar-tools-row">
        <div class="toolbar-group toolbar-group-rows" aria-label="Row tools">
          <span class="toolbar-group-label">Rows</span>
          <button class="calc-btn compact" data-action="add" data-count="1" title="Add one blank row">Add row</button>
          <button class="calc-btn compact" data-action="add" data-count="5" title="Add five blank rows">Add 5</button>
          <button class="calc-btn compact" data-action="insert-above" aria-label="Insert above" title="Insert a blank row above the selection">Above</button>
          <button class="calc-btn compact" data-action="insert-below" aria-label="Insert below" title="Insert a blank row below the selection">Below</button>
          <button class="calc-btn compact" data-action="duplicate" aria-label="Duplicate selected rows" title="Copy the selected row or rows">Duplicate</button>
          <button class="calc-btn compact danger" data-action="delete" aria-label="Delete selected rows" title="Delete the selected row or rows">Delete</button>
        </div>
        <div class="toolbar-group toolbar-group-edit" aria-label="Editing tools">
          <span class="toolbar-group-label">Tools</span>
          <button class="calc-btn compact" data-action="undo" ${undoDisabled} title="Undo the latest calculator edit">Undo</button>
          <button class="calc-btn compact" data-action="redo" ${redoDisabled} title="Redo the latest undone edit">Redo</button>
          <button class="calc-btn compact" data-action="fill-down" aria-label="Fill down" title="Copy the first selected cell down through the selection">Fill down</button>
          <button class="calc-btn compact" data-action="fill-right" aria-label="Fill right" title="Copy the first selected cell across the selection">Fill right</button>
          <button class="calc-btn compact" data-action="find-replace" title="Find or replace text in calculator cells">Find / replace</button>
        </div>
        <div class="toolbar-group toolbar-group-view" aria-label="View tools">
          <span class="toolbar-group-label">View</span>
          <button class="calc-btn compact" data-action="version-history" title="Restore browser recovery snapshots">Versions (${(state.recoverySnapshots || []).length})</button>
          <label class="advanced-toggle" title="Show additional financial and formula columns"><input type="checkbox" data-action="toggle-advanced" aria-label="Advanced columns" ${state.showAdvanced ? 'checked' : ''}> More columns</label>
          <button class="calc-btn compact" data-action="toggle-fullscreen" title="Use the full browser window">${calculatorFullscreen ? 'Exit full screen' : 'Full screen'}</button>
        </div>
      </div>
    </div>
    <div class="calculator-status-row">
      <span>${escapeHtml(libraryText)}</span>
      ${excelReady ? '<span id="calculator-excel-ready-status" class="excel-ready-status">Excel ready</span>' : ''}
      <span id="calculator-sync-status" class="sync-status ${state.dirty ? 'dirty' : 'saved'}">${escapeHtml(state.syncStatus || (state.dirty ? 'Unsaved changes' : 'Saved'))}</span>
      ${state.recoveryWarning ? `<span id="calculator-recovery-warning" class="calculator-recovery-warning">${escapeHtml(state.recoveryWarning)}</span>` : ''}
    </div>`;
}


function refreshRecoveryWarningOnly() {
  const statusRow = document.querySelector('.calculator-status-row');
  if (!statusRow || !calculatorState) return;
  let warning = document.getElementById('calculator-recovery-warning');
  const message = calculatorState.recoveryWarning || '';
  if (!message) {
    if (warning) warning.remove();
    return;
  }
  if (!warning) {
    warning = document.createElement('span');
    warning.id = 'calculator-recovery-warning';
    warning.className = 'calculator-recovery-warning';
    statusRow.appendChild(warning);
  }
  warning.textContent = message;
}

function refreshVersionHistoryCount() {
  const button = document.querySelector('[data-action="version-history"]');
  if (button) button.textContent = `Versions (${(calculatorState?.recoverySnapshots || []).length})`;
}

function buildFormulaBarHtml(state) {
  const column = activeCell ? columnByKey(activeCell.key) : null;
  const row = activeCell ? state.rows[activeCell.rowIndex] : null;
  const reference = column && row ? `${column.label} · row ${escapeHtml(row.row_id || activeCell.rowIndex + 1)}` : 'Select a cell';
  return `
    <div class="calculator-formula-bar">
      <span class="formula-reference">${reference}</span>
      <input data-action="formula-bar" aria-label="Active cell value" value="${escapeHtml(activeCellRawValue())}" ${activeCell ? '' : 'disabled'}>
    </div>`;
}

function buildSalesPriceToolsHtml(state) {
  const visible = Boolean(activeCell && activeCell.key === 'sales_price_per_unit');
  return `
    <div id="sales-price-tools" class="sales-price-tools${visible ? '' : ' hidden'}" aria-label="Sales price margin shortcuts">
      <span>Sales margin from gross</span>
      <button class="margin-shortcut" data-action="sales-margin" data-margin="0.10">10%</button>
      <button class="margin-shortcut" data-action="sales-margin" data-margin="0.15">15%</button>
      <button class="margin-shortcut" data-action="sales-margin" data-margin="0.20">20%</button>
      <button class="margin-shortcut reset" data-action="sales-price-use-gross">Use gross</button>
    </div>`;
}

function buildFindReplaceHtml(state) {
  if (!state.showFindReplace) return '';
  return `
    <div class="calculator-find-replace">
      <input data-action="find-query" aria-label="Find" placeholder="Find" value="${escapeHtml(state.findQuery || '')}">
      <input data-action="replace-query" aria-label="Replace with" placeholder="Replace with" value="${escapeHtml(state.replaceQuery || '')}">
      <button class="calc-btn" data-action="find-next">Find next</button>
      <button class="calc-btn" data-action="replace-current">Replace</button>
      <button class="calc-btn" data-action="replace-all">Replace all</button>
      <button class="calc-btn" data-action="close-find" aria-label="Close search panel">Close</button>
    </div>`;
}


function buildVersionHistoryHtml(state) {
  if (!state.showVersionHistory) return '';
  const snapshots = state.recoverySnapshots || [];
  const storageText = formatCalculatorStorageBytes(state.recoveryStorageBytes || calculatorRecoveryStorageUsage().totalBytes);
  const items = snapshots.length
    ? snapshots.map((snapshot) => `
      <button class="calculator-version-item" data-version-id="${escapeHtml(snapshot.id)}">
        <strong>${escapeHtml(new Date(snapshot.savedAt).toLocaleString())}</strong>
        <span>${escapeHtml(snapshot.reason || 'edit')} · ${snapshot.rows.length} row(s)</span>
      </button>`).join('')
    : '<div class="calculator-version-empty">No recovery versions yet.</div>';
  return `
    <div class="calculator-version-panel" role="dialog" aria-label="Calculator version history">
      <div class="calculator-version-heading"><strong>Local recovery versions</strong><span>Newest first · ${escapeHtml(storageText)} stored in this browser</span></div>
      <div class="calculator-version-list">${items}</div>
      <div class="calculator-version-actions">
        <button class="calc-btn danger" data-action="clear-versions" ${snapshots.length ? '' : 'disabled'}>Clear versions</button>
        <button class="calc-btn" data-action="close-versions">Close</button>
      </div>
    </div>`;
}

function dashboardTotalsHtml(state) {
  const totals = calculateDashboard(state);
  const costPerPax = totals.cost_per_pax === null ? '—' : formatNumber(totals.cost_per_pax, 2);
  const salesPerPax = totals.sales_per_pax === null ? '—' : formatNumber(totals.sales_per_pax, 2);
  const paxValue = state.numberOfPax === null || state.numberOfPax === undefined ? '' : String(state.numberOfPax);
  return `
    <div class="calculator-dashboard">
      <label class="pax-control">No. of pax<input type="number" min="1" step="1" data-action="set-pax" value="${escapeHtml(paxValue)}" placeholder="Optional"></label>
      <span>Total cost NOK <strong>${formatNumber(totals.net_price_nok, 2)}</strong></span>
      <span>Cost per pax <strong>${costPerPax}</strong></span>
      <span>Total sales NOK <strong>${formatNumber(totals.sales_price_nok_total, 2)}</strong></span>
      <span>Sales per pax <strong>${salesPerPax}</strong></span>
      <span>Profit / GP NOK <strong>${formatNumber(totals.gp_nok, 2)}</strong></span>
      <span>Margin <strong>${(totals.gp_percent * 100).toFixed(1)}%</strong></span>
    </div>
    <div class="calculator-vat-summary">
      <span>VAT25 <strong>${formatNumber(totals.vat25, 2)}</strong></span>
      <span>VAT15 <strong>${formatNumber(totals.vat15, 2)}</strong></span>
      <span>VAT12 <strong>${formatNumber(totals.vat12, 2)}</strong></span>
      <span>VAT0-D <strong>${formatNumber(totals.vat0_domestic, 2)}</strong></span>
      <span>VAT0-I <strong>${formatNumber(totals.vat0_international, 2)}</strong></span>
    </div>
    ${currencyExposureHtml(totals.currency_exposure)}`;
}

function currencyExposureHtml(exposure) {
  const supplier = (exposure?.supplier || []).map(([currency, value]) => `<span>${escapeHtml(currency)} ${formatNumber(value, 2)}</span>`).join('');
  const sales = (exposure?.sales || []).map(([currency, value]) => `<span>${escapeHtml(currency)} ${formatNumber(value, 2)}</span>`).join('');
  if (!supplier && !sales) return '';
  return `
    <div class="calculator-currency-exposure">
      <div><strong>Supplier exposure</strong>${supplier || '<span>—</span>'}</div>
      <div><strong>Sales exposure</strong>${sales || '<span>—</span>'}</div>
    </div>`;
}


function buildTableHtml(state) {
  const columns = visibleColumns(state.showAdvanced).map((column) => ({
    ...column,
    renderedWidth: dynamicColumnWidth(column, state.rows)
  }));
  const colgroup = columns.map((column) => `<col data-column-key="${column.key}" style="width:${column.renderedWidth}px; min-width:${column.renderedWidth}px; max-width:${column.renderedWidth}px">`).join('');
  const headers = columns.map((column, index) => `<th data-column-key="${column.key}" class="${stickyColumnClass(index)}" style="width:${column.renderedWidth}px; min-width:${column.renderedWidth}px; max-width:${column.renderedWidth}px" title="${escapeHtml(column.label)}"><span>${escapeHtml(column.label)}</span><span class="column-resize-handle" data-column-key="${column.key}" aria-hidden="true"></span></th>`).join('');
  const body = state.rows.map((row, rowIndex) => {
    const selectedClass = rowIndex === state.selectedRowIndex ? ' selected-row' : '';
    const cells = columns.map((column, colIndex) => cellHtml(row, rowIndex, column, colIndex)).join('');
    return `<tr class="calc-row${selectedClass}" data-row-index="${rowIndex}">${cells}</tr>`;
  }).join('');
  return `
    <div class="calculator-grid-scroll">
      <table class="calculator-grid-table" aria-label="Itinerary calculation spreadsheet" style="min-width:max(100%, ${tableWidth(columns)}px)">
        <colgroup>${colgroup}</colgroup>
        <thead><tr>${headers}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

function tableWidth(columns) {
  return columns.reduce((total, column) => total + Number(column.renderedWidth || column.width || 100), 0);
}

function dynamicColumnWidth(column, rows) {
  const customWidth = Number(calculatorState?.columnWidths?.[column.key]);
  if (Number.isFinite(customWidth) && customWidth > 0) return customWidth;
  const headerWidth = Math.ceil(String(column.label || '').length * 6.4 + 30);
  const cellWidth = Math.ceil(maxVisibleCellChars(column, rows) * 6.9 + 28);
  const minimum = Number(column.minWidth || column.width || headerWidth);
  const maximum = Number(column.maxWidth || column.width || minimum);
  return Math.max(minimum, Math.min(maximum, Math.max(headerWidth, cellWidth)));
}

function maxVisibleCellChars(column, rows) {
  const cap = Number(column.fitChars || 10);
  let longest = 0;
  for (const row of rows || []) {
    const text = cellTitle(row[column.key], column);
    if (!text) continue;
    longest = Math.max(longest, Math.min(cap, String(text).length));
  }
  return longest;
}

function stickyColumnClass(index) {
  if (index === 0) return 'sticky-col sticky-col-0';
  if (index === 1) return 'sticky-col sticky-col-1';
  return '';
}

function cellHtml(row, rowIndex, column, colIndex) {
  const raw = row[column.key];
  const ariaLabel = `${column.label}, row ${row.row_id || rowIndex + 1}`;
  const common = `data-row-index="${rowIndex}" data-key="${column.key}" aria-label="${escapeHtml(ariaLabel)}"`;
  const width = column.renderedWidth || column.width;
  const widthStyle = `style="width:${width}px; min-width:${width}px; max-width:${width}px"`;
  const error = validationErrorForCell(rowIndex, column.key);
  const hasOverride = Boolean(column.formula && row[formulaOverrideKey(column.key)] !== null && row[formulaOverrideKey(column.key)] !== undefined);
  const classes = [stickyColumnClass(colIndex), error ? 'invalid-cell' : '', hasOverride ? 'override-cell' : '', cellIsSelected(rowIndex, column.key) ? 'selected-cell' : ''].filter(Boolean).join(' ');
  const titleText = error ? error.message : hasOverride ? `Manual override active · ${cellTitle(raw, column)}` : cellTitle(raw, column);
  const title = `title="${escapeHtml(titleText)}" aria-invalid="${error ? 'true' : 'false'}"`;
  if (column.formula) {
    const override = row[formulaOverrideKey(column.key)];
    const display = formatFormula(raw, column.kind);
    const fillHandle = cellIsFillHandleCorner(rowIndex, column.key) ? '<span class="fill-handle" contenteditable="false" aria-hidden="true"></span>' : '';
    return `<td class="cell editable formula-cell ${classes}" contenteditable="true" spellcheck="false" ${common} ${widthStyle} ${title}>${escapeHtml(display)}${fillHandle}</td>`;
  }
  if (column.kind === 'checkbox') {
    return `<td class="cell checkbox-cell ${classes}" ${common} ${widthStyle}><input type="checkbox" ${raw ? 'checked' : ''} ${common}></td>`;
  }
  const value = editableCellDisplayValue(row, column);
  const autocompleteClass = column.autocomplete ? ' autocomplete-cell' : '';
  const fillHandle = cellIsFillHandleCorner(rowIndex, column.key) ? '<span class="fill-handle" contenteditable="false" aria-hidden="true"></span>' : '';
  return `<td class="cell editable${autocompleteClass} ${classes}" contenteditable="true" spellcheck="false" ${common} ${widthStyle} ${title}>${escapeHtml(value)}${fillHandle}</td>`;
}

function editableCellDisplayValue(row, column) {
  const value = row[column.key];
  if (value === null || value === undefined || value === '') return '';
  if (column.key === 'sales_price_per_unit') {
    const parsed = parseNumericInput(value);
    return parsed === null ? String(value) : formatNumber(parsed, 2);
  }
  return String(value);
}

function cellTitle(value, column) {
  if (column.formula) return formatFormula(value, column.kind);
  return value === null || value === undefined ? '' : String(value);
}

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

function renderShell(state) {
  validateCalculatorState(state);
  const root = document.getElementById('root');
  root.innerHTML = `
    <div class="calculator-grid-shell${calculatorFullscreen ? ' fullscreen' : ''}" style="--sticky-col-1-left:${dynamicColumnWidth(columnByKey('row_id'), state.rows)}px">
      ${buildToolbarHtml(state)}
      ${buildFormulaBarHtml(state)}
      ${buildSalesPriceToolsHtml(state)}
      ${buildFindReplaceHtml(state)}
      ${buildVersionHistoryHtml(state)}
      <div id="calculator-dashboard-container">${dashboardTotalsHtml(state)}</div>
      <div id="calculator-validation-container">${validationSummaryHtml(state)}</div>
      ${buildTableHtml(state)}
      ${buildSuggestionHtml(state)}
    </div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}

function refreshTotalsOnly() {
  const container = document.getElementById('calculator-dashboard-container');
  if (container) container.innerHTML = dashboardTotalsHtml(calculatorState);
}

function refreshDownloadStateOnly() {
  const ready = Boolean(calculatorState?.pendingDownload?.content_base64);
  const button = document.querySelector('[data-action="download"]');
  if (button) {
    button.classList.toggle('ready', ready);
    button.title = ready ? 'Excel ready — click to download' : 'Prepare the latest Excel workbook';
  }
  if (!ready) document.getElementById('calculator-excel-ready-status')?.remove();
}

function refreshSyncStatusOnly() {
  const element = document.getElementById('calculator-sync-status');
  if (!element) return;
  element.textContent = calculatorState.syncStatus || (calculatorState.dirty ? 'Unsaved changes' : 'Saved');
  element.classList.toggle('dirty', Boolean(calculatorState.dirty));
  element.classList.toggle('saved', !calculatorState.dirty);
}

function refreshValidationAndStatus(runValidation = true) {
  if (runValidation) validateCalculatorState(calculatorState);
  const container = document.getElementById('calculator-validation-container');
  if (container) container.innerHTML = validationSummaryHtml(calculatorState);
  document.querySelectorAll('td.invalid-cell').forEach((cell) => cell.classList.remove('invalid-cell'));
  for (const error of calculatorState.validationErrors) {
    if (error.rowIndex < 0) continue;
    document.querySelector(`td[data-row-index="${error.rowIndex}"][data-key="${error.key}"]`)?.classList.add('invalid-cell');
  }
  refreshSyncStatusOnly();
}

function refreshFormulaBarOnly() {
  const input = document.querySelector('[data-action="formula-bar"]');
  const label = document.querySelector('.formula-reference');
  if (input) {
    input.disabled = !activeCell;
    if (document.activeElement !== input) input.value = activeCellRawValue();
  }
  if (label) {
    const column = activeCell ? columnByKey(activeCell.key) : null;
    const row = activeCell ? calculatorState.rows[activeCell.rowIndex] : null;
    label.textContent = column && row ? `${column.label} · row ${row.row_id || activeCell.rowIndex + 1}` : 'Select a cell';
  }
  refreshSalesPriceToolsOnly();
}

function refreshSalesPriceToolsOnly() {
  const tools = document.getElementById('sales-price-tools');
  if (!tools) return;
  tools.classList.toggle('hidden', !(activeCell && activeCell.key === 'sales_price_per_unit'));
}
