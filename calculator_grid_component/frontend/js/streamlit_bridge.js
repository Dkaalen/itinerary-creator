const Streamlit = {
  setComponentReady: function() {
    window.parent.postMessage({isStreamlitMessage: true, type: 'streamlit:componentReady', apiVersion: 1}, '*');
  },
  setFrameHeight: function(height) {
    window.parent.postMessage({isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: height}, '*');
  },
  setComponentValue: function(value) {
    window.parent.postMessage({isStreamlitMessage: true, type: 'streamlit:setComponentValue', value: value}, '*');
  }
};

function setCalculatorFrameHeight() {
  const shell = document.querySelector('.calculator-grid-shell');
  if (shell?.classList?.contains('fullscreen')) {
    Streamlit.setFrameHeight(Math.max(760, window.innerHeight || 760));
    return;
  }
  const measured = Math.ceil((shell?.getBoundingClientRect?.().height || document.body.scrollHeight || 760) + 24);
  Streamlit.setFrameHeight(Math.max(680, Math.min(1120, measured)));
}

function setCalculatorHostFullscreen(active) {
  const frame = window.frameElement;
  if (!frame || !frame.style) return;
  if (active) {
    if (!frame.dataset.calculatorOriginalStyle) {
      frame.dataset.calculatorOriginalStyle = frame.getAttribute('style') || '';
    }
    frame.style.position = 'fixed';
    frame.style.inset = '0';
    frame.style.width = '100vw';
    frame.style.height = '100vh';
    frame.style.maxWidth = '100vw';
    frame.style.maxHeight = '100vh';
    frame.style.zIndex = '2147483000';
    frame.style.border = '0';
    frame.style.background = '#0f1117';
    frame.style.display = 'block';
    return;
  }
  if (frame.dataset.calculatorOriginalStyle !== undefined) {
    frame.setAttribute('style', frame.dataset.calculatorOriginalStyle);
    delete frame.dataset.calculatorOriginalStyle;
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function renderComponentBootMessage(message) {
  const root = document.getElementById('root');
  if (!root) return;
  root.innerHTML = `
    <div class="calculator-grid-shell">
      <div class="component-loading">
        <strong>${escapeHtml(message)}</strong><br>
        If this stays visible, the calculator component loaded but did not receive data from Streamlit.
      </div>
    </div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}

window.addEventListener('resize', () => requestAnimationFrame(setCalculatorFrameHeight));


function renderCalculatorFrontendError(error) {
  const root = document.getElementById('root');
  const message = error && error.message ? error.message : error;
  const stack = error && error.stack ? error.stack : '';
  const details = stack || message || 'Unknown frontend error';
  if (!root) return;
  root.innerHTML = `
    <div class="calculator-grid-shell">
      <div class="component-error">
        <strong>Calculator grid frontend error.</strong><br>
        ${escapeCalculatorErrorHtml(details)}
      </div>
    </div>`;
  requestAnimationFrame(setCalculatorFrameHeight);
}

function escapeCalculatorErrorHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('\"', '&quot;')
    .replaceAll("'", '&#039;');
}
