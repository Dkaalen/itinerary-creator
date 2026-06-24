/** Responsibility split from editor_document_model.js. */
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
