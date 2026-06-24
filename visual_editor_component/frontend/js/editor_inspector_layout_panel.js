// Right-inspector page/block layout controls.
function renderInspectorLayoutTools(hasBlock, page, block) {
  const hasPage = !!(page && page.page_id);
  if (!hasPage && !hasBlock) return '';
  const pageOverrides = page?.page_overrides || {};
  const blockOverrides = block?.style_overrides || {};
  const isManualPage = page?.page_type === 'manual';
  const selectedManualBlock = !!manualBlockContextFromSelection();
  const pageHidden = !!page?.is_hidden;
  const spacing = String(pageOverrides.spacing_density || 'standard');
  const blockSpacing = String(blockOverrides.spacing_density || 'inherit');
  const pageDisabled = hasPage ? '' : 'disabled';
  const manualDisabled = isManualPage ? '' : 'disabled';
  const blockDisabled = hasBlock ? '' : 'disabled';
  const manualBlockDisabled = selectedManualBlock ? '' : 'disabled';
  const blockTools = hasBlock ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorBlockSpacing">Selected block spacing</label>
    <select id="inspectorBlockSpacing" ${blockDisabled} aria-label="Selected block spacing">
      <option value="inherit" ${blockSpacing === 'inherit' ? 'selected' : ''}>Inherit page spacing</option>
      <option value="compact" ${blockSpacing === 'compact' ? 'selected' : ''}>Compact</option>
      <option value="standard" ${blockSpacing === 'standard' ? 'selected' : ''}>Standard</option>
      <option value="comfortable" ${blockSpacing === 'comfortable' ? 'selected' : ''}>Comfortable</option>
    </select>
    <label class="inspector-checkbox"><input type="checkbox" id="inspectorKeepBlockTogether" ${blockOverrides.keep_block_together ? 'checked' : ''} ${blockDisabled}> Keep selected block together</label>
  </div>` : '';
  const manualBlockTools = selectedManualBlock ? `<div class="inspector-layout-section">
    <div class="inspector-button-grid two">
      <button type="button" class="ghost" id="inspectorMoveBlockUpBtn" ${manualBlockDisabled}>Move block up</button>
      <button type="button" class="ghost" id="inspectorMoveBlockDownBtn" ${manualBlockDisabled}>Move block down</button>
      <button type="button" class="ghost" id="inspectorDuplicateBlockBtn" ${manualBlockDisabled}>Duplicate block</button>
      <button type="button" class="danger" id="inspectorDeleteBlockBtn" ${manualBlockDisabled}>Delete block</button>
    </div>
  </div>` : '';
  const manualPageTools = isManualPage ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorManualBlockTemplate">Insert block on manual page</label>
    <select id="inspectorManualBlockTemplate" ${manualDisabled} aria-label="Manual block template">${manualBlockTemplateOptionsHtml('text')}</select>
    <button type="button" class="ghost full-width" id="inspectorInsertManualBlockBtn" ${manualDisabled}>Insert selected block</button>
    <div class="inspector-button-grid two">
      <button type="button" class="ghost" id="inspectorDuplicatePageBtn" ${manualDisabled}>Duplicate page</button>
      <button type="button" class="ghost" id="inspectorAddManualBlockBtn" ${manualDisabled}>Add text block</button>
    </div>
  </div>` : '';
  const pageTools = hasPage ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorPageSpacing">Page spacing</label>
    <select id="inspectorPageSpacing" ${pageDisabled} aria-label="Page spacing">
      <option value="standard" ${spacing === 'standard' ? 'selected' : ''}>Standard</option>
      <option value="compact" ${spacing === 'compact' ? 'selected' : ''}>Compact</option>
      <option value="comfortable" ${spacing === 'comfortable' ? 'selected' : ''}>Comfortable</option>
    </select>
    <label class="inspector-checkbox"><input type="checkbox" id="inspectorKeepPageTogether" ${pageOverrides.keep_page_together ? 'checked' : ''} ${pageDisabled}> Keep page together</label>
    <div class="inspector-button-grid">
      <button type="button" class="ghost" id="inspectorHidePageBtn" ${hasPage && !pageHidden ? '' : 'disabled'}>Delete page</button>
      <button type="button" class="ghost" id="inspectorRestorePageBtn" ${hasPage && pageHidden ? '' : 'disabled'}>Restore page</button>
      <button type="button" class="ghost" id="inspectorResetPageLayoutBtn" ${pageDisabled}>Reset layout</button>
    </div>
  </div>` : '';
  const manualTemplateTools = hasPage ? `<div class="inspector-layout-section">
    <label class="inspector-control-label" for="inspectorManualPageTemplate">Manual page template</label>
    <select id="inspectorManualPageTemplate" aria-label="Manual page template">${manualPageTemplateOptionsHtml('blank')}</select>
    <button type="button" class="ghost full-width" id="inspectorAddTemplatePageBtn">Add template page</button>
  </div>` : '';
  return `<details class="inspector-card layout-tools-card"><summary><span>More page options</span><em>Layout tools</em></summary>
    ${pageTools}
    ${manualPageTools}
    ${blockTools}
    ${manualBlockTools}
    ${manualTemplateTools}
    <p class="inspector-mini-note">Page move and delete shortcuts are also available above each itinerary page.</p>
  </details>`;
}

