/** Responsibility split from editor_text_tools.js. */
const CONTROLLED_TEXT_STYLE_CLASSES = controlledPresetClassNames('text_styles');
const CONTROLLED_FONT_FAMILY_CLASSES = controlledPresetClassNames('font_families');
const CONTROLLED_FONT_SIZE_CLASSES = controlledPresetClassNames('font_sizes');
const CONTROLLED_COLOR_CLASSES = controlledPresetClassNames('colors');
const CONTROLLED_SPACING_CLASSES = controlledPresetClassNames('spacing');

function removeClassGroupDeep(root, classGroup) {
  if (!root || !classGroup?.length) return;
  if (root.classList) removeClassGroup(root, classGroup);
  root.querySelectorAll?.('[class]')?.forEach(node => removeClassGroup(node, classGroup));
}

function styleSelectedRange(editable, className, classGroup) {
  if (!isRichEditable(editable) || !className) return false;
  restoreCanvasSelection(editable);
  const selection = window.getSelection();
  const range = selectionRangeInside(editable);
  if (!range || range.collapsed) return false;
  const wrapper = document.createElement('span');
  wrapper.className = className;
  const fragment = range.extractContents();
  removeClassGroupDeep(fragment, classGroup);
  wrapper.appendChild(fragment);
  range.insertNode(wrapper);
  const nextRange = document.createRange();
  nextRange.selectNodeContents(wrapper);
  selection.removeAllRanges();
  selection.addRange(nextRange);
  rememberCanvasSelection();
  return true;
}

function removeClassGroup(node, classGroup) {
  classGroup.forEach(cls => node.classList?.remove(cls));
}

function applyClassPreset(className, classGroup) {
  const editable = selectedTextToolEditable();
  if (!editable) {
    notifyEditor('Select text on the canvas first.');
    return;
  }
  restoreCanvasSelection(editable);
  pushUndo(editable, editableValue(editable));
  if (!styleSelectedRange(editable, className, classGroup)) {
    const target = selectedStyleTarget(editable);
    if (!target) {
      notifyEditor('Place the cursor in text first.');
      return;
    }
    removeClassGroup(target, classGroup);
    if (className) target.classList.add(className);
  }
  commitEditableDomChange(editable);
  rememberCanvasSelection();
}

function applyTextStylePreset(preset) {
  const mapping = controlledPresetClassMap('text_styles');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_TEXT_STYLE_CLASSES);
}

function applyFontFamilyPreset(preset) {
  const mapping = controlledPresetClassMap('font_families');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_FONT_FAMILY_CLASSES);
}

function applyFontSizePreset(preset) {
  const mapping = controlledPresetClassMap('font_sizes');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_FONT_SIZE_CLASSES);
}

function applyColorPreset(preset) {
  const mapping = controlledPresetClassMap('colors');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_COLOR_CLASSES);
}

function applySpacingPreset(preset) {
  const mapping = controlledPresetClassMap('spacing');
  applyClassPreset(mapping[preset] ?? '', CONTROLLED_SPACING_CLASSES);
}

function canUsePdfSafeTextTools() {
  return !!selectedTextToolEditable();
}

function clearSelectedFormatting() {
  const editable = selectedTextToolEditable();
  if (!editable) {
    notifyEditor('Select text on the canvas first.');
    return;
  }
  restoreCanvasSelection(editable);
  const target = selectedStyleTarget(editable);
  if (!target) {
    notifyEditor('Place the cursor in text first.');
    return;
  }
  pushUndo(editable, editableValue(editable));
  removeClassGroupDeep(target, CONTROLLED_TEXT_STYLE_CLASSES);
  removeClassGroupDeep(target, CONTROLLED_FONT_FAMILY_CLASSES);
  removeClassGroupDeep(target, CONTROLLED_FONT_SIZE_CLASSES);
  removeClassGroupDeep(target, CONTROLLED_COLOR_CLASSES);
  removeClassGroupDeep(target, CONTROLLED_SPACING_CLASSES);
  commitEditableDomChange(editable);
  rememberCanvasSelection();
  updateRightInspector();
}
