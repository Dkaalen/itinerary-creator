// Right-inspector orchestration only. Panel responsibilities live in editor_inspector_* modules.
function renderRightInspector() {
  const {fieldKey, meta, page, block} = selectedInspectorMeta();
  const hasBlock = !!(fieldKey || activeBlockId);
  const hasImage = fieldKindForKey(fieldKey) === 'image';
  const emptyState = hasBlock
    ? ''
    : `<div class="inspector-card empty inspector-empty-state"><strong>Select text on the itinerary</strong><p>Use the canvas for text editing. Use these controls only for font, size, color, spacing, and selected-item properties.</p></div>`;
  const selectionCard = hasBlock ? renderInspectorSelectionCard(fieldKey, page, block, meta) : '';
  return `<aside class="right-inspector" aria-label="Formatting and selected-item properties">
    <div class="inspector-title"><strong>Formatting</strong><span>${hasImage ? 'Image' : (canUsePdfSafeTextTools() ? 'Text' : 'Ready')}</span></div>
    ${emptyState}
    ${selectionCard}
    ${renderInspectorTextTools(hasBlock)}
  </aside>`;
}

function updateRightInspector() {
  const inspector = document.querySelector('.right-inspector');
  if (!inspector) return;
  inspector.outerHTML = renderRightInspector();
  attachInspectorHandlers();
  requestAnimationFrame(() => syncEditorFrameHeight());
}
function attachInspectorHandlers() {
  document.querySelectorAll('.text-tools-card select, .text-tools-card button').forEach(control => {
    control.addEventListener('mousedown', rememberCanvasSelection, {capture: true});
    control.addEventListener('focus', rememberCanvasSelection, {capture: true});
  });
  document.getElementById('inspectorFontFamilyPreset')?.addEventListener('change', event => {
    if (event.target.value) applyFontFamilyPreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorFontSizePreset')?.addEventListener('change', event => {
    if (event.target.value) applyFontSizePreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorTextStylePreset')?.addEventListener('change', event => {
    if (event.target.value) applyTextStylePreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorColorPreset')?.addEventListener('change', event => {
    if (event.target.value) applyColorPreset(event.target.value);
    event.target.value = '';
    updateRightInspector();
  });
  document.getElementById('inspectorCompactSpacingBtn')?.addEventListener('click', () => { applySpacingPreset('compact'); updateRightInspector(); });
  document.getElementById('inspectorNormalSpacingBtn')?.addEventListener('click', () => { applySpacingPreset('normal'); updateRightInspector(); });
  document.getElementById('inspectorClearFormattingBtn')?.addEventListener('click', clearSelectedFormatting);
  document.getElementById('inspectorPageSpacing')?.addEventListener('change', event => {
    setSelectedPageOverride('spacing_density', event.target.value === 'standard' ? '' : event.target.value);
  });
  document.getElementById('inspectorKeepPageTogether')?.addEventListener('change', event => {
    setSelectedPageOverride('keep_page_together', !!event.target.checked);
  });
  document.getElementById('inspectorBlockSpacing')?.addEventListener('change', event => {
    setSelectedBlockOverride('spacing_density', event.target.value === 'inherit' ? '' : event.target.value);
  });
  document.getElementById('inspectorKeepBlockTogether')?.addEventListener('change', event => {
    setSelectedBlockOverride('keep_block_together', !!event.target.checked);
  });
  document.getElementById('inspectorHidePageBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) hideDocumentPage(page.page_id); });
  document.getElementById('inspectorRestorePageBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) restoreDocumentPage(page.page_id); });
  document.getElementById('inspectorResetPageLayoutBtn')?.addEventListener('click', resetSelectedPageLayout);
  document.getElementById('inspectorMovePageUpBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) moveDocumentPage(page.page_id, -1); });
  document.getElementById('inspectorMovePageDownBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) moveDocumentPage(page.page_id, 1); });
  document.getElementById('inspectorDuplicatePageBtn')?.addEventListener('click', () => { const page = selectedPageContract(); if (page) duplicateManualPage(page.page_id); });
  document.getElementById('inspectorAddManualBlockBtn')?.addEventListener('click', addManualTextBlockToSelectedPage);
  document.getElementById('inspectorAddTemplatePageBtn')?.addEventListener('click', () => {
    addManualPage(document.getElementById('inspectorManualPageTemplate')?.value || 'blank');
  });
  document.getElementById('inspectorInsertManualBlockBtn')?.addEventListener('click', () => {
    addManualBlockToSelectedPage(document.getElementById('inspectorManualBlockTemplate')?.value || 'text');
  });
  document.getElementById('inspectorMoveBlockUpBtn')?.addEventListener('click', () => moveSelectedManualBlock(-1));
  document.getElementById('inspectorMoveBlockDownBtn')?.addEventListener('click', () => moveSelectedManualBlock(1));
  document.getElementById('inspectorDuplicateBlockBtn')?.addEventListener('click', duplicateSelectedManualBlock);
  document.getElementById('inspectorDeleteBlockBtn')?.addEventListener('click', deleteSelectedManualBlock);
  document.querySelectorAll('[data-inspector-field-key]').forEach(btn => {
    btn.addEventListener('click', () => selectInspectorField(btn.getAttribute('data-inspector-field-key')));
  });
  document.querySelectorAll('[data-inspector-reset-field-key]').forEach(btn => {
    btn.addEventListener('click', event => {
      event.stopPropagation();
      resetFieldByKey(btn.getAttribute('data-inspector-reset-field-key'));
    });
  });
  document.getElementById('inspectorFieldEditor')?.addEventListener('input', event => {
    applyInspectorFieldEdit(event.target.getAttribute('data-inspector-edit-key'), event.target.value);
  });
  document.getElementById('inspectorFieldEditor')?.addEventListener('blur', event => {
    applyInspectorFieldEdit(event.target.getAttribute('data-inspector-edit-key'), event.target.value, {refreshInspector: false});
  });
  document.getElementById('inspectorApplyFieldBtn')?.addEventListener('click', () => {
    const editor = document.getElementById('inspectorFieldEditor');
    if (editor) {
      applyInspectorFieldEdit(editor.getAttribute('data-inspector-edit-key'), editor.value, {refreshInspector: false});
      draw();
    }
  });
  document.getElementById('inspectorRestoreCurrentGeneratedBtn')?.addEventListener('click', resetSelectedInspectorField);
  document.getElementById('inspectorRestoreSelectionGeneratedBtn')?.addEventListener('click', resetSelectionFieldsToGenerated);
  document.getElementById('inspectorRevealSelectionBtn')?.addEventListener('click', revealSelectedInspectorTarget);
  document.getElementById('inspectorResetSingleFieldBtn')?.addEventListener('click', resetSelectedInspectorField);
  document.getElementById('inspectorResetFieldBtn')?.addEventListener('click', resetSelectedInspectorField);
  document.getElementById('inspectorFlagIssueBtn')?.addEventListener('click', flagSelectedIssue);
  document.getElementById('inspectorClearSelectionBtn')?.addEventListener('click', () => {
    activeBlockId = null;
    activeFieldKey = null;
    updateSelectionUi();
    updateRightInspector();
  });
}
