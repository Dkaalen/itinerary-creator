/** Style preset lookup helpers. */
function controlledPresetGroup(groupName) {
  const registry = CONTROLLED_EDITOR_STYLE_REGISTRY || {};
  const group = registry[groupName];
  return Array.isArray(group) ? group : [];
}

function controlledPresetClassMap(groupName) {
  return Object.fromEntries(controlledPresetGroup(groupName).map(item => [item.id, item.class_name || '']));
}

function controlledPresetClassNames(groupName) {
  return controlledPresetGroup(groupName).map(item => item.class_name || '').filter(Boolean);
}

function controlledEditorAllowedClasses() {
  const registry = CONTROLLED_EDITOR_STYLE_REGISTRY || {};
  const extra = Array.isArray(registry.extra_allowed_classes) ? registry.extra_allowed_classes : [];
  return [
    ...controlledPresetClassNames('text_styles'),
    ...controlledPresetClassNames('font_families'),
    ...controlledPresetClassNames('font_sizes'),
    ...controlledPresetClassNames('colors'),
    ...controlledPresetClassNames('spacing'),
    ...controlledPresetClassNames('blocks'),
    ...extra,
  ];
}

function controlledPresetOptionsHtml(groupName, placeholderLabel) {
  const options = [`<option value="">${esc(placeholderLabel)}</option>`];
  controlledPresetGroup(groupName).forEach(item => {
    options.push(`<option value="${escAttr(item.id)}">${esc(item.label || item.id)}</option>`);
  });
  return options.join('');
}
