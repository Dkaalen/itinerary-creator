// Controlled visual-editor style preset registry.
// Keep this file aligned with visual_editor_component/style_presets.json.
window.CONTROLLED_EDITOR_STYLE_REGISTRY = {
  "schema_version": 1,
  "text_styles": [
    {
      "id": "normal",
      "label": "Normal text",
      "class_name": "",
      "pdf_base_style": null
    },
    {
      "id": "small_note",
      "label": "Small note",
      "class_name": "ve-text-small-note",
      "pdf_base_style": "editor_small_note"
    },
    {
      "id": "large_text",
      "label": "Large text",
      "class_name": "ve-text-large",
      "pdf_base_style": "editor_large"
    },
    {
      "id": "heading",
      "label": "Heading",
      "class_name": "ve-text-heading",
      "pdf_base_style": "editor_heading"
    },
    {
      "id": "subheading",
      "label": "Subheading",
      "class_name": "ve-text-subheading",
      "pdf_base_style": "editor_subheading"
    },
    {
      "id": "muted_text",
      "label": "Muted text",
      "class_name": "ve-text-muted",
      "pdf_text_color": "muted",
      "pdf_suffix": "muted"
    },
    {
      "id": "accent_text",
      "label": "Accent text",
      "class_name": "ve-text-accent",
      "pdf_text_color": "accent",
      "pdf_suffix": "accent"
    }
  ],
  "colors": [
    {
      "id": "default",
      "label": "Default",
      "class_name": ""
    },
    {
      "id": "muted_grey",
      "label": "Muted grey",
      "class_name": "ve-color-muted",
      "pdf_text_color": "muted",
      "pdf_suffix": "muted"
    },
    {
      "id": "accent_gold",
      "label": "Accent gold",
      "class_name": "ve-color-accent",
      "pdf_text_color": "#9a6a16",
      "pdf_suffix": "gold"
    },
    {
      "id": "warning",
      "label": "Warning / important",
      "class_name": "ve-color-warning",
      "pdf_text_color": "#7a1c1c",
      "pdf_suffix": "warning"
    },
    {
      "id": "soft_highlight",
      "label": "Soft highlight",
      "class_name": "ve-color-highlight",
      "pdf_back_color": "#eadfcf",
      "pdf_suffix": "highlight"
    }
  ],
  "spacing": [
    {
      "id": "compact",
      "label": "Compact spacing",
      "class_name": "ve-spacing-compact",
      "pdf_space_after": 1.5,
      "pdf_suffix": "compact"
    },
    {
      "id": "normal",
      "label": "Normal spacing",
      "class_name": "ve-spacing-normal",
      "pdf_space_after": 6,
      "pdf_suffix": "normal"
    }
  ],
  "blocks": [
    {
      "id": "note",
      "label": "Add note block",
      "class_name": "ve-note-block",
      "html": "<div class=\"content-block ve-note-block\"><div class=\"body-text ve-text-small-note ve-color-muted\">Note: Add your note here.</div></div>"
    },
    {
      "id": "divider",
      "label": "Add divider",
      "class_name": "ve-divider-block",
      "html": "<div class=\"content-block ve-divider-block\"><div class=\"ve-divider\">&nbsp;</div></div>"
    }
  ],
  "extra_allowed_classes": [
    "ve-divider"
  ]
};

function controlledPresetGroup(groupName) {
  const registry = window.CONTROLLED_EDITOR_STYLE_REGISTRY || {};
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
  const registry = window.CONTROLLED_EDITOR_STYLE_REGISTRY || {};
  const extra = Array.isArray(registry.extra_allowed_classes) ? registry.extra_allowed_classes : [];
  return [
    ...controlledPresetClassNames('text_styles'),
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

function controlledBlockTemplate(blockId) {
  const item = controlledPresetGroup('blocks').find(block => block.id === blockId);
  return item?.html || '';
}
