// Dedicated Calculator rendering owner.

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
      <span>Target GP margin</span>
      <button class="margin-shortcut" data-action="sales-margin" data-margin="0.10">10%</button>
      <button class="margin-shortcut" data-action="sales-margin" data-margin="0.15">15%</button>
      <button class="margin-shortcut" data-action="sales-margin" data-margin="0.20">20%</button>
      <button class="margin-shortcut reset" data-action="sales-price-use-gross">Use automatic</button>
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
