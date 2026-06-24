/** Responsibility split from editor_document_model.js. */
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
