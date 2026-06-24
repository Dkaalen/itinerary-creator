/** Responsibility split from state.js. */
function pageStackElement() {
  return document.querySelector('.page-stack');
}

function captureEditorScrollState(reason = '') {
  const stack = pageStackElement();
  if (!stack) return editorScrollSnapshot;
  editorScrollSnapshot = {
    top: stack.scrollTop || 0,
    left: stack.scrollLeft || 0,
    pageId: activePageId || '',
    blockId: activeBlockId || '',
    editKey: activeEditKey || '',
    reason: String(reason || ''),
    capturedAt: Date.now(),
  };
  return editorScrollSnapshot;
}

function restoreEditorScrollState(options = {}) {
  if (suppressNextScrollRestore && !options.force) {
    suppressNextScrollRestore = false;
    return;
  }
  const stack = pageStackElement();
  if (!stack || !editorScrollSnapshot) return;
  const snapshot = editorScrollSnapshot;
  requestAnimationFrame(() => {
    const currentStack = pageStackElement();
    if (!currentStack) return;
    currentStack.scrollTop = Number(snapshot.top || 0);
    currentStack.scrollLeft = Number(snapshot.left || 0);
    if (snapshot.pageId) {
      activePageId = snapshot.pageId;
      const page = document.querySelector(`[data-page-id="${CSS.escape(snapshot.pageId)}"]`);
      if (page) page.classList.add('selected-page');
    }
    if (snapshot.blockId) {
      activeBlockId = snapshot.blockId;
      const block = document.querySelector(`[data-editor-block-id="${CSS.escape(snapshot.blockId)}"]`);
      if (block) block.classList.add('selected-editor-block');
    }
  });
}

function allowNextDrawToResetScroll() {
  suppressNextScrollRestore = true;
  editorScrollSnapshot = {top: 0, left: 0, pageId: '', blockId: '', editKey: '', capturedAt: Date.now(), reason: 'intentional-reset'};
}
