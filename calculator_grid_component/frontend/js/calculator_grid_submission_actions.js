// Backend submission and persistence lifecycle ownership.

function submitAction(action) {
  commitCellEdit();
  flushLocalDraftSave();
  flushRecoverySnapshot();
  calculateRows(calculatorState.rows, calculatorState.currencyRates);
  const clientHasValidationErrors = calculatorValidationErrors(calculatorState, CALCULATOR_VALIDATION_SCOPE.DISPLAY).length > 0;
  const errors = validateCalculatorState(calculatorState, validationScopeForAction(action));
  if (errors.length) {
    calculatorState.syncStatus = action.startsWith('generate_') ? 'Complete the highlighted itinerary fields' : 'Fix validation errors for this action';
    refreshValidationAndStatus(false);
    return;
  }
  if (calculatorState.dirty) window.ItineraryCalculator.storage.saveDraft(calculatorState, activeBackendRevision);
  const requestId = beginCalculatorRequest(action);
  if (!requestId) return;
  const rows = normalizeRowsForPython(calculatorState.rows);
  calculatorState.syncStatus = action === 'sync' ? 'Syncing…' : 'Preparing latest grid…';
  refreshSyncStatusOnly();
  const sent = Streamlit.setComponentValue(JSON.stringify({
    action,
    request_id: requestId,
    rows,
    number_of_pax: calculatorState.numberOfPax ?? null,
    show_advanced: calculatorState.showAdvanced,
    client_state_revision: activeBackendRevision,
    project_identity: activeProjectIdentity,
    client_has_validation_errors: clientHasValidationErrors
  }));
  if (!sent) {
    cancelCalculatorRequest(requestId);
    calculatorState.syncStatus = 'Calculator session is reconnecting';
    refreshSyncStatusOnly();
  }
}

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

