function pageObjectAt(index) {
  const pages = Array.isArray(model.final_pages?.whats_included_pages_html) ? model.final_pages.whats_included_pages_html : [];
  if (index < 0 || index >= pages.length) return {pages, page: null};
  const page = typeof pages[index] === 'string' ? {html: pages[index]} : (pages[index] || {html: ''});
  pages[index] = page;
  return {pages, page};
}
function htmlTextContent(html) {
  const box = document.createElement('div');
  box.innerHTML = html || '';
  return (box.textContent || '').replace(/\s+/g, ' ').trim();
}
function stripEditorArtifactsFromHtml(html) {
  const box = document.createElement('div');
  box.innerHTML = html || '';
  box.querySelectorAll('*').forEach(node => {
    node.removeAttribute('style');
    node.removeAttribute('contenteditable');
    node.removeAttribute('data-edit-key');
    node.classList.remove('warning-hit');
  });
  return box.innerHTML;
}

function editorSlug(value) {
  const slug = String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return slug || 'page';
}
function documentPages() {
  if (!Array.isArray(model.document_pages)) model.document_pages = [];
  return model.document_pages;
}
function sortedDocumentPages() {
  return documentPages().slice().sort((a, b) => Number(a?.sort_order || 0) - Number(b?.sort_order || 0));
}
function renumberDocumentPageOrders(orderedPages = null) {
  const ordered = orderedPages || sortedDocumentPages();
  ordered.forEach((page, index) => {
    if (page) page.sort_order = index + 1;
  });
  return ordered;
}
function documentPageCanMove(page) {
  return !!page && page.is_hidden !== true;
}
function documentPageCanDuplicate(page) {
  return !!page && page.page_type === 'manual' && page.is_hidden !== true;
}
function documentPageById(pageId) {
  return documentPages().find(page => String(page?.page_id || '') === String(pageId || '')) || null;
}
function pageIndexById(pageId) {
  return documentPages().findIndex(page => String(page?.page_id || '') === String(pageId || ''));
}
function pageIsHidden(pageId) {
  return !!documentPageById(pageId)?.is_hidden;
}
function ensureDocumentPage(pageId, pageType, title, sortOrder, extras = {}) {
  const pages = documentPages();
  let page = documentPageById(pageId);
  if (!page) {
    page = Object.assign({
      page_id: pageId,
      page_type: pageType,
      title,
      sort_order: sortOrder,
      is_hidden: false,
      generated_blocks: [],
      manual_blocks: [],
      editable_fields: {},
      style_overrides: {},
      page_overrides: {},
      page_actions: {hide: true, restore: true, move: true, duplicate: pageType === 'manual', reset: pageType !== 'manual'}
    }, extras || {});
    pages.push(page);
  } else {
    if (!page.title && title) page.title = title;
    if (!page.page_type && pageType) page.page_type = pageType;
    if (!page.sort_order) page.sort_order = sortOrder;
    if (!page.page_actions) page.page_actions = {hide: true, restore: true, move: true, duplicate: pageType === 'manual', reset: pageType !== 'manual'};
  }
  return page;
}
function pageIdForDay(day, index) {
  const identity = String(day?.day || day?.day_id || day?.label || '').trim();
  const page = documentPages().find(page => {
    if (page?.page_type !== 'generated_day') return false;
    if (identity && String(page?.source_day_id || '') === identity) return true;
    if (identity && String(page?.title || '') === identity) return true;
    return Number(page?.sort_order || 0) === index + 3;
  });
  return page?.page_id || `day-${editorSlug(identity || `Day ${index + 1}`)}`;
}
function finalPageId(sectionId) {
  if (sectionId === 'whats_included') return 'final-whats-included';
  if (sectionId === 'whats_not_included') return 'final-whats-not-included';
  if (sectionId === 'important_travel_notes') return 'final-important-travel-notes';
  return `final-${editorSlug(sectionId)}`;
}

function humanizeEditorToken(value) {
  return String(value || '')
    .replace(/[_\-.]+/g, ' ')
    .replace(/\b\w/g, ch => ch.toUpperCase())
    .trim();
}
function contractPage(pageId) {
  return documentPages().find(page => String(page?.page_id || '') === String(pageId || '')) || null;
}
function contractBlock(page, blockId) {
  if (!page || !blockId) return null;
  const blocks = [...(page.generated_blocks || []), ...(page.manual_blocks || [])];
  return blocks.find(block => String(block?.block_id || '') === String(blockId || '')) || null;
}
function safeDayPageId(dayIndex) {
  const index = Number(dayIndex || 0);
  const day = Array.isArray(model?.days) ? model.days[index] : null;
  if (typeof pageIdForDay === 'function') return pageIdForDay(day || {}, index);
  return `day-${editorSlug(day?.day || day?.label || `Day ${index + 1}`)}`;
}
function finalPageIdForEditKey(key) {
  if (key.includes('whats_included')) return finalPageId('whats_included');
  if (key.includes('whats_not_included')) return finalPageId('whats_not_included');
  if (key.includes('important_travel_notes')) return finalPageId('important_travel_notes');
  return finalPageId('final');
}
function editorFieldLabel(key, explicitLabel = '') {
  if (explicitLabel) return explicitLabel;
  const tail = String(key || '').split('.').pop() || 'field';
  return humanizeEditorToken(tail);
}
function inferEditorBlockMetaForKey(key, label = '') {
  const editKey = String(key || '');
  const meta = {
    page_id: '',
    page_title: '',
    block_id: '',
    block_type: 'text',
    field_key: editKey,
    field_label: editorFieldLabel(editKey, label),
    source_row_ids: [],
    validation_status: 'unknown',
  };
  let match = editKey.match(/^document_pages\.(\d+)\.manual_blocks\.(\d+)\.editable_fields\.(.+)$/);
  if (match) {
    const page = documentPages()[Number(match[1])] || {};
    const block = (page.manual_blocks || [])[Number(match[2])] || {};
    meta.page_id = page.page_id || '';
    meta.page_title = page.title || 'Manual page';
    meta.block_id = block.block_id || `${meta.page_id}__manual-${Number(match[2]) + 1}`;
    meta.block_type = block.block_type || 'manual_text';
    meta.source_row_ids = block.source_row_ids || [];
    meta.validation_status = block.validation_status || page.validation_status || 'unknown';
    return meta;
  }
  match = editKey.match(/^document_pages\.(\d+)\.title$/);
  if (match) {
    const page = documentPages()[Number(match[1])] || {};
    meta.page_id = page.page_id || '';
    meta.page_title = page.title || 'Manual page';
    meta.block_id = `${meta.page_id || 'manual'}__title`;
    meta.block_type = 'page_title';
    meta.source_row_ids = page.source_row_ids || [];
    meta.validation_status = page.validation_status || 'unknown';
    return meta;
  }
  match = editKey.match(/^days\.(\d+)\.(.+)$/);
  if (match) {
    const dayIndex = Number(match[1]);
    const field = match[2];
    const pageId = safeDayPageId(dayIndex);
    const page = contractPage(pageId) || {};
    const blockId = field === 'blocks_html' ? `${pageId}__main` : `${pageId}__${editorSlug(field)}`;
    const block = contractBlock(page, blockId) || contractBlock(page, `${pageId}__main`) || {};
    meta.page_id = pageId;
    meta.page_title = page.title || model?.days?.[dayIndex]?.day || `Day ${dayIndex + 1}`;
    meta.block_id = blockId;
    meta.block_type = field === 'blocks_html' ? (block.block_type || 'day_content') : 'day_field';
    meta.source_row_ids = block.source_row_ids || page.source_row_ids || [];
    meta.validation_status = block.validation_status || page.validation_status || 'unknown';
    return meta;
  }
  if (editKey.startsWith('cover.')) {
    const field = editKey.slice('cover.'.length);
    const page = contractPage('cover') || {};
    meta.page_id = 'cover';
    meta.page_title = page.title || 'Cover';
    meta.block_id = `cover__${editorSlug(field)}`;
    meta.block_type = field.includes('image') ? 'image' : 'cover_field';
    meta.source_row_ids = page.source_row_ids || [];
    meta.validation_status = page.validation_status || 'unknown';
    return meta;
  }
  if (editKey.startsWith('summary.')) {
    const page = contractPage('summary') || {};
    const field = editKey.slice('summary.'.length);
    meta.page_id = 'summary';
    meta.page_title = page.title || 'Trip summary';
    meta.block_id = `summary__${editorSlug(field)}`;
    meta.block_type = 'summary_field';
    meta.source_row_ids = page.source_row_ids || [];
    meta.validation_status = page.validation_status || 'unknown';
    return meta;
  }
  if (editKey.startsWith('final_pages.')) {
    const pageId = finalPageIdForEditKey(editKey);
    const page = contractPage(pageId) || {};
    const block = contractBlock(page, `${pageId}__main`) || {};
    meta.page_id = pageId;
    meta.page_title = page.title || 'Final section';
    meta.block_id = `${pageId}__main`;
    meta.block_type = block.block_type || 'final_section';
    meta.source_row_ids = block.source_row_ids || page.source_row_ids || [];
    meta.validation_status = block.validation_status || page.validation_status || 'unknown';
    return meta;
  }
  return meta;
}
function editorBlockAttrs(key, label = '') {
  const meta = inferEditorBlockMetaForKey(key, label);
  return ` data-editor-page-id="${escAttr(meta.page_id)}" data-editor-block-id="${escAttr(meta.block_id)}" data-editor-block-type="${escAttr(meta.block_type)}" data-editor-field-key="${escAttr(meta.field_key)}" data-editor-field-label="${escAttr(meta.field_label)}"`;
}
function selectEditorPage(pageId) {
  const nextPageId = pageId;
  const changed = activePageId !== nextPageId || activeBlockId !== null || activeFieldKey !== null;
  activePageId = nextPageId;
  activeBlockId = null;
  activeFieldKey = null;
  updateSelectionUi();
  if (changed) updateRightInspector();
}
function selectEditorFieldByKey(fieldKey) {
  const key = String(fieldKey || '');
  if (!key) return;
  const target = document.querySelector(`[data-editor-field-key="${CSS.escape(key)}"]`) || document.querySelector(`[data-edit-key="${CSS.escape(key)}"]`);
  if (target) {
    selectEditorBlockFromElement(target);
    return;
  }
  const meta = inferEditorBlockMetaForKey(key, '');
  activePageId = meta.page_id || activePageId;
  activeBlockId = meta.block_id || activeBlockId;
  activeFieldKey = key;
  updateSelectionUi();
  updateRightInspector();
}
function selectEditorBlockFromElement(el) {
  const target = el?.closest?.('[data-editor-block-id]') || el?.closest?.('[data-edit-key]');
  if (!target) return;
  const meta = inferEditorBlockMetaForKey(target.getAttribute('data-editor-field-key') || target.getAttribute('data-edit-key') || '', target.getAttribute('data-editor-field-label') || '');
  const nextPageId = target.getAttribute('data-editor-page-id') || meta.page_id || target.closest('[data-page-id]')?.getAttribute('data-page-id') || activePageId;
  const nextBlockId = target.getAttribute('data-editor-block-id') || meta.block_id || '';
  const nextFieldKey = target.getAttribute('data-editor-field-key') || target.getAttribute('data-edit-key') || '';
  const changed = activePageId !== nextPageId || activeBlockId !== nextBlockId || activeFieldKey !== nextFieldKey;
  activePageId = nextPageId;
  activeBlockId = nextBlockId;
  activeFieldKey = nextFieldKey;
  updateSelectionUi();
  if (changed) updateRightInspector();
}
function selectedEditorElement() {
  if (activeFieldKey) {
    const byField = document.querySelector(`[data-editor-field-key="${CSS.escape(activeFieldKey)}"]`) || document.querySelector(`[data-edit-key="${CSS.escape(activeFieldKey)}"]`);
    if (byField) return byField;
  }
  if (activeBlockId) return document.querySelector(`[data-editor-block-id="${CSS.escape(activeBlockId)}"]`);
  return selectedEditable();
}
function updateSelectionUi() {
  document.querySelectorAll('[data-page-id]').forEach(el => el.classList.toggle('selected-page', el.getAttribute('data-page-id') === activePageId));
  document.querySelectorAll('[data-outline-page-id]').forEach(el => el.classList.toggle('active', el.getAttribute('data-outline-page-id') === activePageId));
  document.querySelectorAll('[data-editor-block-id]').forEach(el => {
    const blockMatch = activeBlockId && el.getAttribute('data-editor-block-id') === activeBlockId;
    const fieldMatch = activeFieldKey && (el.getAttribute('data-editor-field-key') === activeFieldKey || el.getAttribute('data-edit-key') === activeFieldKey);
    el.classList.toggle('selected-editor-block', !!(blockMatch && (!activeFieldKey || fieldMatch)));
  });
}
function pageInspectorRows(page) {
  const fields = Object.keys(page?.editable_fields || {});
  const rows = fields.slice(0, 10).map(field => `<li>${esc(humanizeEditorToken(field))}</li>`).join('');
  return rows || '<li>No direct editable fields exposed yet</li>';
}
function ensurePageOverrides(page) {
  if (!page.page_overrides || typeof page.page_overrides !== 'object') page.page_overrides = {};
  return page.page_overrides;
}
function ensureBlockStyleOverrides(block) {
  if (!block.style_overrides || typeof block.style_overrides !== 'object') block.style_overrides = {};
  return block.style_overrides;
}
function selectedPageContract() {
  const {meta} = selectedInspectorMeta();
  return contractPage(activePageId || meta.page_id) || null;
}
function selectedBlockContract() {
  const {meta, page} = selectedInspectorMeta();
  return contractBlock(page, activeBlockId || meta.block_id) || null;
}
function manualBlockContextFromSelection() {
  const {fieldKey} = selectedInspectorMeta();
  const match = String(fieldKey || '').match(/^document_pages\.(\d+)\.manual_blocks\.(\d+)\./);
  if (!match) return null;
  const pageIndex = Number(match[1]);
  const blockIndex = Number(match[2]);
  const page = documentPages()[pageIndex];
  if (!page || page.page_type !== 'manual') return null;
  const block = Array.isArray(page.manual_blocks) ? page.manual_blocks[blockIndex] : null;
  if (!block) return null;
  return {page, pageIndex, block, blockIndex};
}

function manualPageTemplateCatalog() {
  return {
    blank: {
      label: 'Blank page',
      title: 'Blank page',
      blocks: [{type: 'manual_text', title: 'Manual text', html: '<div class="body-text">New page text</div>'}]
    },
    text: {
      label: 'Text page',
      title: 'Custom text page',
      blocks: [
        {type: 'manual_heading', title: 'Heading', html: '<div class="section-title">Add a heading</div>'},
        {type: 'manual_text', title: 'Body text', html: '<div class="body-text">Write your custom itinerary text here.</div>'}
      ]
    },
    image: {
      label: 'Image page',
      title: 'Custom image page',
      blocks: [
        {type: 'manual_heading', title: 'Image heading', html: '<div class="section-title">Image page</div>'},
        {type: 'manual_image', title: 'Image placeholder', html: '<div class="content-block"><div class="body-text"><strong>Image placeholder:</strong> Replace this text with image notes, a caption, or destination context.</div></div>'},
        {type: 'manual_text', title: 'Caption', html: '<div class="body-text">Add caption or supporting text.</div>'}
      ]
    },
    notes: {
      label: 'Notes page',
      title: 'Notes',
      blocks: [
        {type: 'manual_heading', title: 'Notes heading', html: '<div class="section-title">Notes</div>'},
        {type: 'manual_note', title: 'Notes list', html: '<ul class="final-list"><li>Add note one</li><li>Add note two</li></ul>'}
      ]
    },
    divider: {
      label: 'Divider page',
      title: 'Section divider',
      blocks: [
        {type: 'manual_heading', title: 'Divider heading', html: '<div class="section-title">Section title</div>'},
        {type: 'manual_text', title: 'Divider subtitle', html: '<div class="body-text">Add a short divider subtitle or introduction.</div>'}
      ]
    },
    info: {
      label: 'Info page',
      title: 'Practical information',
      blocks: [
        {type: 'manual_heading', title: 'Info heading', html: '<div class="section-title">Practical information</div>'},
        {type: 'manual_info', title: 'Information list', html: '<ul class="final-list"><li>Meeting point:</li><li>What to bring:</li><li>Important contact:</li></ul>'}
      ]
    }
  };
}
function manualPageTemplateOptionsHtml(selected = 'blank') {
  const catalog = manualPageTemplateCatalog();
  return Object.keys(catalog).map(templateId => `<option value="${escAttr(templateId)}" ${templateId === selected ? 'selected' : ''}>${esc(catalog[templateId].label)}</option>`).join('');
}
function manualBlockTemplateOptionsHtml(selected = 'text') {
  const catalog = manualPageTemplateCatalog();
  const blockOptions = [
    ['text', 'Text block'],
    ['heading', 'Heading block'],
    ['note', 'Note/list block'],
    ['divider', 'Divider text block'],
    ['image', 'Image placeholder block'],
    ['info', 'Info list block'],
  ];
  return blockOptions.map(([templateId, label]) => `<option value="${escAttr(templateId)}" ${templateId === selected ? 'selected' : ''}>${esc(label)}</option>`).join('');
}
function manualBlockTemplate(templateId) {
  const templates = {
    text: {type: 'manual_text', title: 'Text block', html: '<div class="body-text">New text block</div>'},
    heading: {type: 'manual_heading', title: 'Heading block', html: '<div class="section-title">New heading</div>'},
    note: {type: 'manual_note', title: 'Note/list block', html: '<ul class="final-list"><li>Add note</li></ul>'},
    divider: {type: 'manual_text', title: 'Divider text block', html: '<div class="body-text">Add divider text</div>'},
    image: {type: 'manual_image', title: 'Image placeholder', html: '<div class="content-block"><div class="body-text"><strong>Image placeholder:</strong> Add image notes or caption text.</div></div>'},
    info: {type: 'manual_info', title: 'Info list block', html: '<ul class="final-list"><li>Important detail:</li></ul>'},
  };
  return templates[templateId] || templates.text;
}
function createManualBlock(pageId, blockTemplate, blockIndex) {
  const template = blockTemplate || manualBlockTemplate('text');
  return {
    block_id: `${pageId}__${template.type || 'manual'}-${Date.now()}-${blockIndex + 1}`,
    block_type: template.type || 'manual_text',
    title: template.title || `Manual block ${blockIndex + 1}`,
    editable_fields: {content_html: template.html || '<div class="body-text">New content</div>'},
    style_overrides: {},
    image_binding: {},
    source_row_ids: [],
    dirty_state: 'dirty',
    validation_status: 'unknown'
  };
}
function manualPageFromTemplate(templateId = 'blank') {
  const catalog = manualPageTemplateCatalog();
  const template = catalog[templateId] || catalog.blank;
  const pageId = `manual-${templateId}-${Date.now()}`;
  const manualBlocks = (template.blocks || catalog.blank.blocks).map((blockTemplate, blockIndex) => createManualBlock(pageId, blockTemplate, blockIndex));
  return {
    page_id: pageId,
    page_type: 'manual',
    title: template.title || 'Custom page',
    sort_order: maxDocumentPageOrder() + 1,
    is_hidden: false,
    source_day_id: '',
    source_section_id: '',
    source_row_ids: [],
    editable_fields: {title: template.title || 'Custom page', template_id: templateId},
    generated_blocks: [],
    manual_blocks: manualBlocks,
    style_overrides: {},
    page_overrides: {template_id: templateId},
    page_actions: {hide: true, restore: true, move: true, duplicate: true, reset: false},
    validation_status: 'unknown'
  };
}
function pageLayoutClasses(page) {
  const overrides = page?.page_overrides || {};
  const density = String(overrides.spacing_density || 'standard').replace(/[^a-z0-9_-]/gi, '') || 'standard';
  const classes = [`layout-density-${density}`];
  if (overrides.keep_page_together) classes.push('layout-keep-page-together');
  return classes.join(' ');
}
function blockLayoutClasses(block) {
  const overrides = block?.style_overrides || {};
  const density = String(overrides.spacing_density || '').replace(/[^a-z0-9_-]/gi, '');
  const classes = [];
  if (density) classes.push(`layout-density-${density}`);
  if (overrides.keep_block_together) classes.push('layout-keep-block-together');
  return classes.join(' ');
}
function setSelectedPageOverride(name, value) {
  const page = selectedPageContract();
  if (!page) { notifyEditor('Select a page first.'); return; }
  collect();
  const overrides = ensurePageOverrides(page);
  if (value === '' || value === null || value === undefined || value === false) delete overrides[name];
  else overrides[name] = value;
  markDocumentPagesTouched('Page layout updated');
  draw();
  scrollToPage(page.page_id);
}
function resetSelectedPageLayout() {
  const page = selectedPageContract();
  if (!page) { notifyEditor('Select a page first.'); return; }
  collect();
  page.page_overrides = {};
  markDocumentPagesTouched('Page layout reset');
  draw();
  scrollToPage(page.page_id);
}
function setSelectedBlockOverride(name, value) {
  const page = selectedPageContract();
  const block = selectedBlockContract();
  if (!page || !block) { notifyEditor('Select a block first.'); return; }
  collect();
  const overrides = ensureBlockStyleOverrides(block);
  if (value === '' || value === null || value === undefined || value === false) delete overrides[name];
  else overrides[name] = value;
  markDocumentPagesTouched('Block layout updated');
  draw();
  scrollToPage(page.page_id);
}
function addManualBlockToSelectedPage(templateId = 'text') {
  const page = selectedPageContract();
  if (!page || page.page_type !== 'manual') { notifyEditor('Select a manual page first.'); return; }
  collect();
  if (!Array.isArray(page.manual_blocks)) page.manual_blocks = [];
  const blockIndex = page.manual_blocks.length;
  const block = createManualBlock(page.page_id, manualBlockTemplate(templateId), blockIndex);
  page.manual_blocks.push(block);
  activePageId = page.page_id;
  activeBlockId = block.block_id;
  activeFieldKey = `document_pages.${pageIndexById(page.page_id)}.manual_blocks.${blockIndex}.editable_fields.content_html`;
  markDocumentPagesTouched(`${manualBlockTemplate(templateId).title || 'Manual block'} added`);
  draw();
  scrollToPage(page.page_id);
}
function addManualTextBlockToSelectedPage() {
  addManualBlockToSelectedPage('text');
}
function duplicateSelectedManualBlock() {
  const ctx = manualBlockContextFromSelection();
  if (!ctx) { notifyEditor('Select a manual text block first.'); return; }
  collect();
  const clone = JSON.parse(JSON.stringify(ctx.block));
  clone.block_id = `${ctx.page.page_id}__manual-${Date.now()}`;
  clone.title = `${ctx.block.title || 'Manual text'} copy`;
  ctx.page.manual_blocks.splice(ctx.blockIndex + 1, 0, clone);
  activeBlockId = clone.block_id;
  activeFieldKey = `document_pages.${ctx.pageIndex}.manual_blocks.${ctx.blockIndex + 1}.editable_fields.content_html`;
  markDocumentPagesTouched('Manual text block duplicated');
  draw();
  scrollToPage(ctx.page.page_id);
}
function moveSelectedManualBlock(direction) {
  const ctx = manualBlockContextFromSelection();
  if (!ctx) { notifyEditor('Select a manual text block first.'); return; }
  collect();
  const targetIndex = ctx.blockIndex + direction;
  if (targetIndex < 0 || targetIndex >= ctx.page.manual_blocks.length) return;
  const blocks = ctx.page.manual_blocks;
  [blocks[ctx.blockIndex], blocks[targetIndex]] = [blocks[targetIndex], blocks[ctx.blockIndex]];
  activeBlockId = blocks[targetIndex].block_id;
  activeFieldKey = `document_pages.${ctx.pageIndex}.manual_blocks.${targetIndex}.editable_fields.content_html`;
  markDocumentPagesTouched('Manual text block moved');
  draw();
  scrollToPage(ctx.page.page_id);
}
function moveManualBlockToIndex(pageId, fromIndex, targetIndex) {
  collect();
  const page = documentPageById(pageId);
  if (!page || page.page_type !== 'manual' || !Array.isArray(page.manual_blocks)) return;
  const from = Number(fromIndex);
  const to = Math.max(0, Math.min(Number(targetIndex), page.manual_blocks.length - 1));
  if (!Number.isFinite(from) || from < 0 || from >= page.manual_blocks.length || from === to) return;
  const [block] = page.manual_blocks.splice(from, 1);
  page.manual_blocks.splice(to, 0, block);
  activePageId = page.page_id;
  activeBlockId = block.block_id || '';
  const pageIndex = pageIndexById(page.page_id);
  activeFieldKey = `document_pages.${pageIndex}.manual_blocks.${to}.editable_fields.content_html`;
  markDocumentPagesTouched('Manual block order updated');
  draw();
  scrollToPage(page.page_id);
}

function deleteSelectedManualBlock() {
  const ctx = manualBlockContextFromSelection();
  if (!ctx) { notifyEditor('Select a manual text block first.'); return; }
  collect();
  if (ctx.page.manual_blocks.length <= 1) {
    ctx.block.editable_fields = {content_html: ''};
    notifyEditor('Last manual text block cleared');
  } else {
    ctx.page.manual_blocks.splice(ctx.blockIndex, 1);
    notifyEditor('Manual text block removed');
  }
  activeBlockId = null;
  activeFieldKey = null;
  activePageId = ctx.page.page_id;
  markTouched('document_pages');
  draw();
  scrollToPage(ctx.page.page_id);
}
