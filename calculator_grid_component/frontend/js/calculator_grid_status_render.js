// Dedicated Calculator rendering owner.

function refreshRecoveryStatusOnly() {
  const statusRow = document.querySelector('.calculator-status-row');
  if (!statusRow || !calculatorState) return;
  let status = document.getElementById('calculator-recovery-status');
  const recoveryStatus = calculatorState.recoveryStatus || window.ItineraryCalculator.storage.statusPayload();
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
  const euroValue = (value) => value === null ? '—' : `€${formatNumber(value, 2)}`;
  const costPerPax = euroValue(totals.cost_per_pax_eur);
  const salesPerPax = euroValue(totals.sales_per_pax_eur);
  const paxValue = state.numberOfPax === null || state.numberOfPax === undefined ? '' : String(state.numberOfPax);
  return `
    <div class="calculator-dashboard">
      <label class="trip-start-control">Trip start<input type="date" data-action="set-trip-start" value="${escapeHtml(state.tripStartDate || '')}"></label>
      <label class="pax-control">No. of pax<input type="number" min="1" step="1" data-action="set-pax" value="${escapeHtml(paxValue)}" placeholder="Optional"></label>
      <span>Total cost EUR <strong>${euroValue(totals.total_cost_eur)}</strong><small>NOK ${formatNumber(totals.net_price_nok, 2)}</small></span>
      <span>Cost per pax EUR <strong>${costPerPax}</strong>${totals.cost_per_pax === null ? '' : `<small>NOK ${formatNumber(totals.cost_per_pax, 2)}</small>`}</span>
      <span>Total sales EUR <strong>${euroValue(totals.total_sales_eur)}</strong><small>NOK ${formatNumber(totals.sales_price_nok_total, 2)}</small></span>
      <span>Sales per pax EUR <strong>${salesPerPax}</strong>${totals.sales_per_pax === null ? '' : `<small>NOK ${formatNumber(totals.sales_per_pax, 2)}</small>`}</span>
      <span>Profit / GP EUR <strong>${euroValue(totals.profit_eur)}</strong><small>NOK ${formatNumber(totals.gp_nok, 2)}</small></span>
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


function showCalculatorGenerationLoading(action) {
  const shell = document.querySelector('.calculator-grid-shell');
  if (!shell) return;
  hideCalculatorGenerationLoading();
  const customer = action === 'generate_customer';
  const overlay = document.createElement('div');
  overlay.id = 'calculator-generation-loading';
  overlay.className = 'calculator-generation-loading';
  overlay.setAttribute('role', 'status');
  overlay.setAttribute('aria-live', 'assertive');
  overlay.setAttribute('aria-busy', 'true');
  overlay.innerHTML = `
    <div class="calculator-generation-loading-card">
      <span class="calculator-generation-spinner" aria-hidden="true"></span>
      <div>
        <strong>Generating ${customer ? 'customer' : 'agent'} itinerary…</strong>
        <span>The latest Calculator rows are being prepared and written into the itinerary. Keep this page open.</span>
      </div>
    </div>`;
  shell.appendChild(overlay);
}

function hideCalculatorGenerationLoading() {
  document.getElementById('calculator-generation-loading')?.remove();
}

function refreshSyncStatusOnly() {
  const element = document.getElementById('calculator-sync-status');
  if (!element) return;
  element.textContent = calculatorState.syncStatus || (calculatorState.dirty ? 'Local changes' : 'Workspace synced');
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
