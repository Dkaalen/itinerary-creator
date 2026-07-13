const CALCULATOR_HISTORY_LIMIT = 60;
let pendingCellEditSnapshot = null;

function pushUndoSnapshot(snapshot) {
  if (!snapshot) return;
  calculatorState.undoStack.push(snapshot);
  if (calculatorState.undoStack.length > CALCULATOR_HISTORY_LIMIT) calculatorState.undoStack.shift();
  calculatorState.redoStack = [];
}

function recordHistory() {
  pushUndoSnapshot(currentStateSnapshot());
}

function beginCellEdit() {
  if (!pendingCellEditSnapshot) pendingCellEditSnapshot = currentStateSnapshot();
}

function commitCellEdit() {
  if (!pendingCellEditSnapshot) return;
  const before = JSON.stringify(pendingCellEditSnapshot);
  const after = JSON.stringify(currentStateSnapshot());
  if (before !== after) {
    pushUndoSnapshot(pendingCellEditSnapshot);
    if (calculatorState) {
      scheduleRecoverySnapshot();
    }
  }
  pendingCellEditSnapshot = null;
}


function cancelCellEdit() {
  if (!pendingCellEditSnapshot) return false;
  const snapshot = pendingCellEditSnapshot;
  pendingCellEditSnapshot = null;
  restoreStateSnapshot(snapshot);
  return true;
}

function undoCalculatorChange() {
  commitCellEdit();
  const snapshot = calculatorState.undoStack.pop();
  if (!snapshot) return;
  calculatorState.redoStack.push(currentStateSnapshot());
  restoreStateSnapshot(snapshot);
  markLocalDraft();
  rerender();
}

function redoCalculatorChange() {
  commitCellEdit();
  const snapshot = calculatorState.redoStack.pop();
  if (!snapshot) return;
  calculatorState.undoStack.push(currentStateSnapshot());
  restoreStateSnapshot(snapshot);
  markLocalDraft();
  rerender();
}
