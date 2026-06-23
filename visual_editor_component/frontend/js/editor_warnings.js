function highlightWarnings() {
  let count = 0;
  document.querySelectorAll('[data-edit-key]').forEach(el => {
    const text = el.innerText || '';
    const hit = WARNING_PATTERNS.some(pattern => pattern.test(text));
    el.classList.toggle('warning-hit', hit);
    if (hit) count += 1;
  });
  const serverWarnings = typeof editorClientWarnings === 'function' ? editorClientWarnings().length : (Array.isArray(model.client_output_warnings) ? model.client_output_warnings.length : 0);
  const warningCount = document.getElementById('warningCount');
  if (warningCount) warningCount.textContent = `${Math.max(count, serverWarnings)} warnings`;
}
function updateEditorStats() {
  const editCount = document.getElementById('editCount');
  if (editCount) editCount.textContent = `${touchedKeys.size} manual edits pending`;
  const studioEdits = document.getElementById('studioEditsMetric');
  if (studioEdits) studioEdits.textContent = String(touchedKeys.size);
  const studioDirtyPages = document.getElementById('studioDirtyPagesMetric');
  if (studioDirtyPages) {
    const pages = typeof sortedDocumentPages === 'function' ? sortedDocumentPages() : [];
    studioDirtyPages.textContent = String(pages.filter(page => pageHasDirtyEdits(page?.page_id)).length);
  }
  const studioSelection = document.getElementById('studioSelectionMetric');
  if (studioSelection) studioSelection.textContent = activeBlockId ? 'Block selected' : (activePageId ? 'Page selected' : 'No selection');
  const readinessBadge = document.getElementById('pdfReadinessBadge');
  if (readinessBadge) {
    const status = pdfReadinessStatus();
    readinessBadge.textContent = status.label;
    readinessBadge.className = `stat-pill pdf-readiness ${status.level}`;
  }
  updateSaveStatusUi();
  highlightWarnings();
}
