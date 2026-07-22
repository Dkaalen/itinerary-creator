// Excel import/export command ownership.

function calculatorHasReplaceableWork() {
  if (!calculatorState) return false;
  if (calculatorState.dirty || positiveIntegerOrNull(calculatorState.numberOfPax)) return true;
  return (calculatorState.rows || []).some((row) => {
    if (rowHasUserContent(row)) return true;
    return [...FORMULA_OVERRIDE_KEYS].some((key) => {
      const value = row?.[key];
      return value !== null && value !== undefined && String(value).trim() !== '';
    });
  });
}

async function handleExcelFileSelection(event) {
  const input = event.currentTarget;
  const file = input?.files?.[0];
  if (!file) return;
  try {
    if (file.size > 12 * 1024 * 1024) {
      calculatorState.syncStatus = 'Excel file exceeds the 12 MB limit';
      refreshSyncStatusOnly();
      return;
    }
    const hasCurrentWork = calculatorHasReplaceableWork();
    if (hasCurrentWork && !window.confirm('Open this Excel file as a new Calculator project and replace the current rows? The current cloud project will not be overwritten.')) return;
    calculatorState.syncStatus = 'Opening Excel…';
    refreshSyncStatusOnly();
    const encoded = arrayBufferToBase64(await file.arrayBuffer());
    submitExcelUpload(file.name, encoded);
  } catch (error) {
    calculatorState.syncStatus = `Could not read Excel: ${error?.message || error || 'unknown error'}`;
    refreshSyncStatusOnly();
  } finally {
    input.value = '';
  }
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return window.btoa(binary);
}

function submitExcelUpload(filename, contentBase64) {
  commitCellEdit();
  flushLocalDraftSave();
  flushRecoverySnapshot('before Excel import');
  saveCalculatorDraft(calculatorState, activeBackendRevision);
  const requestId = beginCalculatorRequest('open_excel');
  if (!requestId) return;
  const sent = Streamlit.setComponentValue(JSON.stringify({
    action: 'open_excel',
    request_id: requestId,
    rows: normalizeRowsForPython(calculatorState.rows),
    number_of_pax: calculatorState.numberOfPax ?? null,
    show_advanced: calculatorState.showAdvanced,
    client_state_revision: activeBackendRevision,
    upload_filename: String(filename || 'calculation.xlsx'),
    upload_content_base64: String(contentBase64 || '')
  }));
  if (!sent) {
    cancelCalculatorRequest(requestId);
    calculatorState.syncStatus = 'Calculator session is reconnecting';
    refreshSyncStatusOnly();
  }
}

function maybeAutoDownloadPreparedExcel() {
  const download = calculatorState?.pendingDownload;
  const signature = String(download?.download_signature || '');
  if (!download?.content_base64 || !signature) return;
  const storageKey = `itineraryCalculatorDownloaded.${signature}`;
  try {
    if (window.sessionStorage.getItem(storageKey) === '1') return;
  } catch (_error) {
    // A disabled sessionStorage must not block the download.
  }
  if (!downloadPreparedExcel(download)) return;
  try {
    window.sessionStorage.setItem(storageKey, '1');
  } catch (_error) {
    // The download succeeded even when sessionStorage is disabled.
  }
}

function downloadPreparedExcel(download) {
  const encoded = String(download?.content_base64 || '');
  if (!encoded) return false;
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
  return true;
}
