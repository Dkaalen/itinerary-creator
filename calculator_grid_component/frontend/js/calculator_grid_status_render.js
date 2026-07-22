// Dedicated Calculator rendering owner.

function refreshRecoveryStatusOnly() {
  const statusRow = document.querySelector('.calculator-status-row');
  if (!statusRow || !calculatorState) return;
  let status = document.getElementById('calculator-recovery-status');
  const recoveryStatus = calculatorState.recoveryStatus || calculatorStorageStatusPayload();
  if (recoveryStatus.state === 'available') {
    if (status) status.remove();
    return;
  }
  if (!status) {
    status = document.createElement('button');
    status.id = 'calculator-recovery-status';
    status.className = 'calculator-recovery-status';
    status.dataset.action = 'local-recovery-details';
    status.title = 'Open local recovery details';
    status.addEventListener('click', openCalculatorRecoveryDetails);
    statusRow.appendChild(status);
  }
  status.dataset.state = recoveryStatus.state;
  status.textContent = recoveryStatus.summary;
}

function refreshRecoveryWarningOnly() {
  refreshRecoveryStatusOnly();
}


function refreshVersionHistoryCount() {
  const button = document.querySelector('[data-action="version-history"]');
  if (button) button.textContent = `Versions (${(calculatorState?.recoverySnapshots || []).length})`;
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
