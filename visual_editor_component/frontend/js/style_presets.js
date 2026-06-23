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
    },
    {
      "id": "premium_callout",
      "label": "Premium callout",
      "class_name": "ve-text-premium-callout",
      "pdf_base_style": "editor_large",
      "pdf_text_color": "accent",
      "pdf_suffix": "premiumcallout"
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
    },
    {
      "id": "deep_teal",
      "label": "Deep teal",
      "class_name": "ve-color-deep-teal",
      "pdf_text_color": "#005f5b",
      "pdf_suffix": "deepteal"
    },
    {
      "id": "soft_teal_highlight",
      "label": "Soft teal highlight",
      "class_name": "ve-color-soft-teal-highlight",
      "pdf_back_color": "#dcefed",
      "pdf_suffix": "tealhighlight"
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
    "ve-divider",
    "premium-travel-card",
    "featured-journey-block",
    "coastal-cruise-card",
    "premium-travel-kicker",
    "premium-travel-title",
    "premium-travel-description",
    "premium-travel-badges",
    "premium-travel-badge",
    "premium-route-ribbon",
    "premium-travel-timeline",
    "premium-travel-timeline-item",
    "premium-travel-timeline-label",
    "premium-travel-timeline-detail",
    "premium-travel-chips",
    "premium-travel-chip",
    "premium-travel-chip-muted",
    "premium-linked-transfers",
    "premium-notes-page",
    "premium-notes-grid",
    "premium-note-card",
    "premium-note-card-title"
  ],
  "font_families": [
    {
      "id": "default",
      "label": "Default font",
      "class_name": ""
    },
    {
      "id": "georgia",
      "label": "Georgia",
      "class_name": "ve-font-georgia",
      "pdf_font_name": "Times-Roman",
      "pdf_suffix": "georgia"
    },
    {
      "id": "arial",
      "label": "Arial",
      "class_name": "ve-font-arial",
      "pdf_font_name": "Helvetica",
      "pdf_suffix": "arial"
    },
    {
      "id": "times",
      "label": "Times New Roman",
      "class_name": "ve-font-times",
      "pdf_font_name": "Times-Roman",
      "pdf_suffix": "times"
    },
    {
      "id": "courier",
      "label": "Courier New",
      "class_name": "ve-font-courier",
      "pdf_font_name": "Courier",
      "pdf_suffix": "courier"
    }
  ],
  "font_sizes": [
    {
      "id": "default",
      "label": "Default size",
      "class_name": ""
    },
    {
      "id": "size_9",
      "label": "9 pt",
      "class_name": "ve-size-9",
      "pdf_font_size": 9,
      "pdf_leading": 12,
      "pdf_suffix": "size9"
    },
    {
      "id": "size_10",
      "label": "10 pt",
      "class_name": "ve-size-10",
      "pdf_font_size": 10,
      "pdf_leading": 13.5,
      "pdf_suffix": "size10"
    },
    {
      "id": "size_11",
      "label": "11 pt",
      "class_name": "ve-size-11",
      "pdf_font_size": 11,
      "pdf_leading": 14.8,
      "pdf_suffix": "size11"
    },
    {
      "id": "size_12",
      "label": "12 pt",
      "class_name": "ve-size-12",
      "pdf_font_size": 12,
      "pdf_leading": 16,
      "pdf_suffix": "size12"
    },
    {
      "id": "size_14",
      "label": "14 pt",
      "class_name": "ve-size-14",
      "pdf_font_size": 14,
      "pdf_leading": 18.5,
      "pdf_suffix": "size14"
    },
    {
      "id": "size_16",
      "label": "16 pt",
      "class_name": "ve-size-16",
      "pdf_font_size": 16,
      "pdf_leading": 21,
      "pdf_suffix": "size16"
    },
    {
      "id": "size_18",
      "label": "18 pt",
      "class_name": "ve-size-18",
      "pdf_font_size": 18,
      "pdf_leading": 23.5,
      "pdf_suffix": "size18"
    }
  ],
  "themes": [
    {
      "id": "nordic_luxury",
      "label": "Nordic luxury",
      "description": "Warm paper, deep ink, teal accents, and gold emphasis.",
      "accent_color": "#006f6b",
      "highlight_color": "#c58a24",
      "default_font": "Georgia"
    },
    {
      "id": "clean_proposal",
      "label": "Clean proposal",
      "description": "High-readability proposal styling for dense itineraries.",
      "accent_color": "#1f3446",
      "highlight_color": "#8a6d3b",
      "default_font": "Arial"
    }
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

function controlledBlockTemplate(blockId) {
  const item = controlledPresetGroup('blocks').find(block => block.id === blockId);
  return item?.html || '';
}
