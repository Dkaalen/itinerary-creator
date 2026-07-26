let pendingCalculatorRequest = null;
let calculatorRequestSequence = 0;
let calculatorEditSequence = 0;

function noteCalculatorLocalEdit() {
  calculatorEditSequence += 1;
}

function beginCalculatorRequest(action) {
  if (pendingCalculatorRequest) {
    calculatorState.syncStatus = 'Waiting for the previous Calculator action';
    refreshSyncStatusOnly();
    return null;
  }
  calculatorRequestSequence += 1;
  const requestId = [
    Date.now().toString(36),
    calculatorRequestSequence.toString(36),
    Math.random().toString(36).slice(2, 8)
  ].join('-');
  pendingCalculatorRequest = {
    requestId,
    action: String(action || 'sync'),
    backendRevision: String(activeBackendRevision || ''),
    editSequence: calculatorEditSequence
  };
  return requestId;
}

function cancelCalculatorRequest(requestId) {
  if (pendingCalculatorRequest?.requestId === requestId) pendingCalculatorRequest = null;
}

function consumeCalculatorComponentAck(rawAck, incomingRevision) {
  const ack = rawAck && typeof rawAck === 'object' ? rawAck : null;
  if (!ack || !pendingCalculatorRequest) return {matched: false};
  if (String(ack.request_id || '') !== pendingCalculatorRequest.requestId) return {matched: false};

  const request = pendingCalculatorRequest;
  pendingCalculatorRequest = null;
  const status = String(ack.status || '');
  const accepted = status === 'accepted';
  const hasNewerEdits = calculatorEditSequence > request.editSequence;
  const serverRevision = String(ack.server_state_revision || '');
  const canRebaseNewerEdits = Boolean(
    accepted
    && hasNewerEdits
    && serverRevision
    && serverRevision === String(incomingRevision || '')
  );

  if (accepted && !hasNewerEdits) {
    window.ItineraryCalculator.storage.clearDraft();
    hasLocalDraft = false;
  }

  return {
    matched: true,
    accepted,
    canRebaseNewerEdits,
    message: String(ack.message || ''),
    action: String(ack.action || request.action),
    status,
    serverRevision
  };
}
