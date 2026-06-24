/** Responsibility split from editor_document_model.js. */
function ensurePageOverrides(page) {
  if (!page.page_overrides || typeof page.page_overrides !== 'object') page.page_overrides = {};
  return page.page_overrides;
}

function ensureBlockStyleOverrides(block) {
  if (!block.style_overrides || typeof block.style_overrides !== 'object') block.style_overrides = {};
  return block.style_overrides;
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
