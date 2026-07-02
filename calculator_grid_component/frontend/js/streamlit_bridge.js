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
  const measured = Math.ceil((shell?.getBoundingClientRect?.().height || document.body.scrollHeight || 760) + 24);
  Streamlit.setFrameHeight(Math.max(680, Math.min(1120, measured)));
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

Streamlit.setComponentReady();
window.addEventListener('resize', () => requestAnimationFrame(setCalculatorFrameHeight));
