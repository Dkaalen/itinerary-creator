// Single initialization owner for the visual editor frontend.
(() => {
  const editor = window.ItineraryVisualEditor;
  if (!editor) throw new Error('ItineraryVisualEditor namespace was not loaded.');

  const EDITOR_SCRIPT_GROUPS = Object.freeze({
    state_and_payload: Object.freeze([
      'js/state.js',
      'js/editor_html_utils.js',
      'js/editor_save_state.js',
      'js/editor_scroll_state.js',
      'js/editor_local_draft.js',
      'js/editor_editable_markup.js',
      'js/editor_dirty_state.js',
      'js/serialization.js',
    ]),
    document_and_page_model: Object.freeze([
      'js/editor_image_labels.js',
      'js/style_preset_data.js',
      'js/style_preset_lookup.js',
      'js/editor_block_templates.js',
      'js/editor_document_model.js',
      'js/editor_pages_model.js',
      'js/editor_blocks_model.js',
      'js/editor_selection_model.js',
      'js/editor_layout_overrides.js',
      'js/editor_manual_pages.js',
    ]),
    rendering: Object.freeze([
      'js/editor_warning_model.js',
      'js/editor_debug_readiness.js',
      'js/editor_shell.js',
      'js/editor_render_summary.js',
      'js/editor_render_final_pages.js',
      'js/editor_document_outline.js',
      'js/editor_render_manual_pages.js',
      'js/images.js',
      'js/editor_image_tools.js',
      'js/editor_debug_shell.js',
      'js/render.js',
    ]),
    editing_and_page_operations: Object.freeze([
      'js/editor_text_dom.js',
      'js/editor_text_history.js',
      'js/editor_text_selection.js',
      'js/editor_text_formatting.js',
      'js/editor_insert_blocks.js',
      'js/editor_paste_sanitizer.js',
      'js/editor_text_tools.js',
      'js/editor_inspector_selection.js',
      'js/editor_inspector_fields.js',
      'js/editor_inspector_text_panel.js',
      'js/editor_inspector_layout_panel.js',
      'js/editor_inspector.js',
      'js/editor_page_actions.js',
      'js/editor_warnings.js',
      'js/editor_page_event_handlers.js',
      'js/editor_image_event_handlers.js',
      'js/editing.js',
    ]),
    messaging: Object.freeze([
      'js/streamlit_bridge.js',
    ]),
  });

  function showBootstrapError(error) {
    const root = document.getElementById('root');
    const message = error?.message || String(error || 'Unknown initialization error');
    if (root) {
      root.textContent = `The editable preview could not start safely. ${message}`;
      root.className = 'editor-bootstrap-error';
    }
    console.error('Visual editor initialization failed', error);
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = false;
      script.dataset.editorAsset = src;
      script.addEventListener('load', resolve, {once: true});
      script.addEventListener('error', () => reject(new Error(`Could not load visual editor asset: ${src}`)), {once: true});
      document.head.appendChild(script);
    });
  }

  async function loadGroup(groupName, scripts) {
    for (const src of scripts) await loadScript(src);
    document.documentElement.dataset[`editor${groupName.replace(/(^|_)([a-z])/g, (_match, _prefix, letter) => letter.toUpperCase())}`] = 'loaded';
  }

  async function initializeEditor() {
    for (const [groupName, scripts] of Object.entries(EDITOR_SCRIPT_GROUPS)) {
      await loadGroup(groupName, scripts);
    }

    const requiredModules = Object.freeze([
      'state',
      'payload',
      'drafts',
      'pages',
      'renderer',
      'autosave',
      'bridge',
    ]);
    requiredModules.forEach((name) => editor.require(name));

    editor.require('autosave').initialize();
    editor.require('bridge').initialize();
    editor.markReady();
  }

  initializeEditor().catch(showBootstrapError);
})();
