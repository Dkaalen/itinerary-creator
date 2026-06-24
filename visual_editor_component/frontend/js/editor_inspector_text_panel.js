// Right-inspector PDF-safe text formatting controls.
function renderInspectorTextTools(hasBlock) {
  const canStyle = !!canUsePdfSafeTextTools();
  const disabled = canStyle ? '' : 'disabled';
  const hint = canStyle
    ? 'Formatting applies to the selected canvas text and to what you type next in that selection.'
    : 'Select text on the canvas to enable formatting.';
  return `<div class="inspector-card text-tools-card"><div class="inspector-kicker">Formatting</div>
    <label class="inspector-control-label" for="inspectorFontFamilyPreset">Font</label>
    <select id="inspectorFontFamilyPreset" ${disabled} aria-label="Font family">${controlledPresetOptionsHtml('font_families', 'Choose font')}</select>
    <label class="inspector-control-label" for="inspectorFontSizePreset">Size</label>
    <select id="inspectorFontSizePreset" ${disabled} aria-label="Font size">${controlledPresetOptionsHtml('font_sizes', 'Choose size')}</select>
    <label class="inspector-control-label" for="inspectorTextStylePreset">Paragraph style</label>
    <select id="inspectorTextStylePreset" ${disabled} aria-label="Paragraph style">${controlledPresetOptionsHtml('text_styles', 'Choose style')}</select>
    <label class="inspector-control-label" for="inspectorColorPreset">Text color / highlight</label>
    <select id="inspectorColorPreset" ${disabled} aria-label="Text color and highlight">${controlledPresetOptionsHtml('colors', 'Choose color')}</select>
    <div class="inspector-button-grid">
      <button type="button" class="ghost" id="inspectorCompactSpacingBtn" ${disabled}>Compact</button>
      <button type="button" class="ghost" id="inspectorNormalSpacingBtn" ${disabled}>Normal spacing</button>
      <button type="button" class="ghost" id="inspectorClearFormattingBtn" ${disabled}>Clear formatting</button>
    </div>
    <p>${esc(hint)}</p>
  </div>`;
}


