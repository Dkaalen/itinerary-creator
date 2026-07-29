// Dedicated Calculator rendering owner.

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
  const dateMode = dateCellMode(row, column.key);
  const classes = [stickyColumnClass(colIndex), error ? 'invalid-cell' : '', hasOverride ? 'override-cell' : '', dateMode ? `date-${dateMode}` : '', cellIsSelected(rowIndex, column.key) ? 'selected-cell' : ''].filter(Boolean).join(' ');
  const dateTitle = dateMode ? `${dateMode === DATE_MODE_LINKED ? 'Linked to trip start' : 'Locked date'} · ` : '';
  const titleText = error ? error.message : hasOverride ? `Manual override active · ${cellTitle(raw, column)}` : `${dateTitle}${cellTitle(raw, column)}`;
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
