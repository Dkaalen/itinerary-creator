/** Responsibility split from editor_text_tools.js. */
function rememberCanvasSelection() {
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount) return false;
  const range = selection.getRangeAt(0);
  const editable = editableFromSelectionNode(range.commonAncestorContainer) || editableFromSelectionNode(selection.anchorNode);
  if (!editable) return false;
  savedCanvasSelectionRange = range.cloneRange();
  activeEditKey = editable.getAttribute('data-edit-key') || activeEditKey;
  activeFieldKey = activeEditKey || activeFieldKey;
  return true;
}

function restoreCanvasSelection(editable = null) {
  const target = editable || selectedTextToolEditable();
  if (!target || !savedCanvasSelectionRange) return false;
  try {
    if (!target.contains(savedCanvasSelectionRange.startContainer) || !target.contains(savedCanvasSelectionRange.endContainer)) return false;
    target.focus({preventScroll: true});
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(savedCanvasSelectionRange.cloneRange());
    return true;
  } catch (err) {
    return false;
  }
}

function selectionRangeInside(editable) {
  const selection = window.getSelection();
  if (!editable || !selection || !selection.rangeCount) return null;
  const range = selection.getRangeAt(0);
  if (!editable.contains(range.commonAncestorContainer)) return null;
  return range;
}

function selectedNodeInside(editable) {
  const selection = window.getSelection();
  let node = selection?.anchorNode || document.activeElement;
  if (node && node.nodeType === Node.TEXT_NODE) node = node.parentElement;
  if (node && editable.contains(node)) return node;
  return null;
}

function selectedStyleTarget(editable) {
  if (!editable) return null;
  let node = selectedNodeInside(editable);
  let candidate = node?.closest?.('li,.body-text,.section-title,.row-type,.meta-line,p,span');
  if (candidate && candidate !== editable && editable.contains(candidate) && !candidate.classList.contains('source-row-marker')) return candidate;

  candidate = editable.querySelector('li,.body-text,.section-title,.row-type,.meta-line,p,span');
  if (candidate && !candidate.classList.contains('source-row-marker')) return candidate;

  // Plain title/cover/summary fields are already editable on the canvas.
  // Do not wrap or rewrite their DOM just to apply formatting; that caused
  // selection jitter and made typing unreliable. Apply the class to the
  // editable element itself so the current text and future typing inherit it.
  return editable;
}

function selectedTextToolEditable() {
  const focused = selectedEditable();
  if (focused?.matches?.('[data-edit-key]')) return focused;
  const el = selectedEditorElement();
  if (el?.matches?.('[data-edit-key]')) return el;
  const nested = el?.querySelector?.('[data-edit-key]');
  if (nested?.matches?.('[data-edit-key]')) return nested;
  return null;
}

function selectedTextToolTarget() {
  const editable = selectedTextToolEditable();
  if (!editable) return null;
  return selectedStyleTarget(editable);
}
