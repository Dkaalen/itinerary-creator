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

function showEditorError(err) {
  const root = document.getElementById('root');
  const message = err && err.message ? err.message : String(err || 'Unknown rendering error');
  root.innerHTML = `<div class="editor-shell"><div class="editor-error"><strong>The editable preview could not render safely.</strong><div>${esc(message)}</div><div style="margin-top:8px">Your itinerary data is still in the app. Refresh the preview or generate the itinerary again after saving.</div></div></div>`;
  Streamlit.setFrameHeight(360);
}
function safeRender(payload, commitNonce = null) {
  try {
    render(payload, commitNonce);
  } catch (err) {
    console.error(err);
    showEditorError(err);
  }
}
window.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'streamlit:render') {
    const args = event.data.args || {};
    safeRender(args.payload, args.commit_nonce);
  }
});
Streamlit.setComponentReady();
Streamlit.setFrameHeight(1200);
