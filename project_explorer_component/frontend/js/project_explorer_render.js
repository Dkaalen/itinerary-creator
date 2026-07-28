function renderProjectExplorer() {
  const root = document.getElementById('root');
  if (!root) return;
  const payload = projectExplorerState.payload || {};
  const rows = Array.isArray(payload.rows) ? payload.rows.map(normalizeProjectRecord).filter(Boolean) : [];
  const selectedCount = projectExplorerState.selectedIds.size;
  const dirtySelection = selectionChangedSinceCommit();
  const totalLabel = payload.total_count === null || payload.total_count === undefined
    ? `Page ${Number(payload.page_number || 1)} · ${rows.length} projects shown`
    : `${Number(payload.first_item_number || 0)}–${Number(payload.last_item_number || 0)} of ${Number(payload.total_count || 0)} projects · Page ${Number(payload.page_number || 1)} of ${Number(payload.total_pages || 1)}`;

  const rowHtml = rows.map((row) => {
    const checked = projectExplorerState.selectedIds.has(row.id) ? ' checked' : '';
    const openBadge = row.is_open ? '<span class="project-open-badge">Open</span>' : '';
    return `
      <tr data-project-id="${escapeProjectExplorerHtml(row.id)}">
        <td class="project-select-cell"><input type="checkbox" aria-label="Select ${escapeProjectExplorerHtml(row.name)}" data-project-select="${escapeProjectExplorerHtml(row.id)}"${checked}></td>
        <td class="project-name-cell"><strong>${escapeProjectExplorerHtml(row.name)}</strong>${openBadge}</td>
        <td>${escapeProjectExplorerHtml(row.owner)}</td>
        <td>${escapeProjectExplorerHtml(row.folder)}</td>
        <td>${escapeProjectExplorerHtml(row.last_saved)}</td>
      </tr>`;
  }).join('');

  root.innerHTML = `
    <div class="project-explorer-shell">
      <div class="project-table-scroll">
        <table class="project-table">
          <thead><tr><th class="project-select-cell"><span class="sr-only">Select</span></th><th>Name</th><th>Owner</th><th>Folder/reference</th><th>Last saved</th></tr></thead>
          <tbody>${rowHtml}</tbody>
        </table>
      </div>
      <div class="project-selection-bar">
        <div class="project-selection-copy">
          <strong data-selection-count>${selectedCount} project${selectedCount === 1 ? '' : 's'} selected</strong>
          <span>${dirtySelection ? 'Selection changed. Review it to update the project actions.' : 'Choose projects freely, then review the selection once.'}</span>
        </div>
        <div class="project-selection-actions">
          <button type="button" data-action="clear" ${selectedCount ? '' : 'disabled'}>Clear</button>
          <button type="button" class="primary" data-action="commit" ${dirtySelection ? '' : 'disabled'}>Review selection</button>
        </div>
      </div>
      <div class="project-pagination">
        <button type="button" data-action="previous" ${payload.has_previous ? '' : 'disabled'}>Previous</button>
        <span>${escapeProjectExplorerHtml(totalLabel)}</span>
        <button type="button" data-action="next" ${payload.has_next ? '' : 'disabled'}>Next</button>
      </div>
    </div>`;

  bindProjectExplorerEvents();
  requestAnimationFrame(setProjectExplorerFrameHeight);
}

function bindProjectExplorerEvents() {
  document.querySelectorAll('[data-project-select]').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      const id = cleanProjectId(checkbox.dataset.projectSelect);
      if (!id) return;
      if (checkbox.checked) projectExplorerState.selectedIds.add(id);
      else projectExplorerState.selectedIds.delete(id);
      persistProjectSelection();
      renderProjectExplorer();
    });
  });

  document.querySelector('[data-action="clear"]')?.addEventListener('click', () => {
    projectExplorerState.selectedIds.clear();
    persistProjectSelection();
    emitProjectExplorerAction('clear_selection');
  });
  document.querySelector('[data-action="commit"]')?.addEventListener('click', () => {
    emitProjectExplorerAction('commit_selection');
  });
  document.querySelector('[data-action="previous"]')?.addEventListener('click', () => {
    emitProjectExplorerAction('page', {page_delta: -1});
  });
  document.querySelector('[data-action="next"]')?.addEventListener('click', () => {
    emitProjectExplorerAction('page', {page_delta: 1});
  });
}
