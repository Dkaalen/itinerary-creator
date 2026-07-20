let streamlitBridgeRenderReceived = false;
let streamlitBridgeDisposed = false;
let pendingStreamlitFrameHeight = null;

function postStreamlitBridgeMessage(message, {requiresRender = true} = {}) {
  if (streamlitBridgeDisposed) return false;
  if (requiresRender && !streamlitBridgeRenderReceived) {
    if (message.type === 'streamlit:setFrameHeight') pendingStreamlitFrameHeight = message.height;
    return false;
  }
  window.parent.postMessage({isStreamlitMessage: true, ...message}, '*');
  return true;
}

function markStreamlitRenderReceived() {
  if (streamlitBridgeDisposed) return;
  streamlitBridgeRenderReceived = true;
  if (pendingStreamlitFrameHeight !== null) {
    const height = pendingStreamlitFrameHeight;
    pendingStreamlitFrameHeight = null;
    postStreamlitBridgeMessage({type: 'streamlit:setFrameHeight', height});
  }
}

const Streamlit = {
  setComponentReady: function() {
    return postStreamlitBridgeMessage(
      {type: 'streamlit:componentReady', apiVersion: 1},
      {requiresRender: false}
    );
  },
  setFrameHeight: function(height) {
    return postStreamlitBridgeMessage({type: 'streamlit:setFrameHeight', height});
  },
  setComponentValue: function(value) {
    return postStreamlitBridgeMessage({type: 'streamlit:setComponentValue', value});
  }
};

function disposeStreamlitBridge() {
  streamlitBridgeDisposed = true;
  pendingStreamlitFrameHeight = null;
}

window.addEventListener('pagehide', disposeStreamlitBridge, {once: true});
window.addEventListener('beforeunload', disposeStreamlitBridge, {once: true});

function syncEditorFrameHeight() {
  if (!streamlitBridgeRenderReceived) return;
  const shell = document.querySelector('.editor-shell');
  const measured = Math.ceil((shell?.getBoundingClientRect?.().height || document.body.scrollHeight || 900) + 24);
  const bounded = Math.max(780, Math.min(1080, measured));
  Streamlit.setFrameHeight(bounded);
}

function showEditorError(err) {
  const root = document.getElementById('root');
  const message = err && err.message ? err.message : String(err || 'Unknown rendering error');
  root.innerHTML = `<div class="editor-shell"><div class="editor-error"><strong>The editable preview could not render safely.</strong><div>${esc(message)}</div><div style="margin-top:8px">Your itinerary data is still in the app. Refresh the preview or generate the itinerary again after saving.</div></div></div>`;
  syncEditorFrameHeight();
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
    markStreamlitRenderReceived();
    const args = event.data.args || {};
    safeRender(args.payload, args.commit_nonce);
  }
});
Streamlit.setComponentReady();

window.addEventListener('resize', () => requestAnimationFrame(syncEditorFrameHeight));
