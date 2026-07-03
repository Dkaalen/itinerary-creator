function rerender() {
  calculateRows(calculatorState.rows, calculatorState.currencyRates);
  renderShell(calculatorState);
  bindEvents();
}

function renderError(error) {
  document.getElementById('root').innerHTML = `<div class="calculator-grid-shell"><div class="component-error"><strong>Calculator grid failed to render.</strong><br>${escapeHtml(error && error.message ? error.message : error)}</div></div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}

let componentHasReceivedRender = false;

function handleStreamlitRender(event) {
  if (!event.data || event.data.type !== 'streamlit:render') return;
  componentHasReceivedRender = true;
  try {
    initializeState((event.data.args || {}).payload || {});
    rerender();
  } catch (error) {
    console.error(error);
    renderError(error);
  }
}

function startCalculatorGridComponent() {
  renderComponentBootMessage('Loading calculator grid…');
  window.addEventListener('message', handleStreamlitRender);
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  Streamlit.setComponentReady();
  requestAnimationFrame(setCalculatorFrameHeight);
  window.setTimeout(() => {
    if (!componentHasReceivedRender) {
      renderComponentBootMessage('Waiting for calculator data from Streamlit…');
    }
  }, 2000);
}

startCalculatorGridComponent();
