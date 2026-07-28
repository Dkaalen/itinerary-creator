let projectExplorerHasReceivedRender = false;

function handleProjectExplorerRender(event) {
  if (!event.data || event.data.type !== 'streamlit:render') return;
  projectExplorerHasReceivedRender = true;
  markProjectExplorerRenderReceived();
  initializeProjectExplorerState((event.data.args || {}).payload || {});
  renderProjectExplorer();
}

function startProjectExplorerComponent() {
  window.addEventListener('message', handleProjectExplorerRender);
  Streamlit.setComponentReady();
  requestAnimationFrame(setProjectExplorerFrameHeight);
  window.setTimeout(() => {
    if (!projectExplorerHasReceivedRender) {
      const root = document.getElementById('root');
      if (root) root.innerHTML = '<div class="project-explorer-loading">Loading saved projects…</div>';
      requestAnimationFrame(setProjectExplorerFrameHeight);
    }
  }, 1500);
}

startProjectExplorerComponent();
