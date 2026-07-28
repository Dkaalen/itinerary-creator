let projectExplorerRenderReceived = false;
let projectExplorerPendingHeight = null;

function postProjectExplorerMessage(message, {requiresRender = true} = {}) {
  if (requiresRender && !projectExplorerRenderReceived) {
    if (message.type === 'streamlit:setFrameHeight') projectExplorerPendingHeight = message.height;
    return false;
  }
  window.parent.postMessage({isStreamlitMessage: true, ...message}, '*');
  return true;
}

function markProjectExplorerRenderReceived() {
  projectExplorerRenderReceived = true;
  if (projectExplorerPendingHeight !== null) {
    const height = projectExplorerPendingHeight;
    projectExplorerPendingHeight = null;
    postProjectExplorerMessage({type: 'streamlit:setFrameHeight', height});
  }
}

const Streamlit = {
  setComponentReady() {
    return postProjectExplorerMessage(
      {type: 'streamlit:componentReady', apiVersion: 1},
      {requiresRender: false}
    );
  },
  setFrameHeight(height) {
    return postProjectExplorerMessage({type: 'streamlit:setFrameHeight', height});
  },
  setComponentValue(value) {
    return postProjectExplorerMessage({type: 'streamlit:setComponentValue', value});
  }
};

function setProjectExplorerFrameHeight() {
  const height = Math.ceil((document.documentElement.scrollHeight || document.body.scrollHeight || 360) + 4);
  Streamlit.setFrameHeight(Math.max(220, Math.min(720, height)));
}

function escapeProjectExplorerHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

window.addEventListener('resize', () => requestAnimationFrame(setProjectExplorerFrameHeight));
