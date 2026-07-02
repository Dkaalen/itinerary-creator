function installCalculatorDiagnostics() {
  window.addEventListener('error', (event) => {
    renderCalculatorFrontendError(event.error || event.message || 'Unknown script error');
  });
  window.addEventListener('unhandledrejection', (event) => {
    renderCalculatorFrontendError(event.reason || 'Unhandled calculator promise rejection');
  });
}

installCalculatorDiagnostics();
