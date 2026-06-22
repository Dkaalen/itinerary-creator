function imageHtml(day, dayIndex) {
  const pageId = typeof pageIdForDay === 'function' ? pageIdForDay(day || {}, dayIndex) : `day-${editorSlug(day?.day || day?.label || `Day ${dayIndex + 1}`)}`;
  const blockAttrs = ` data-editor-page-id="${escAttr(pageId)}" data-editor-block-id="${escAttr(pageId)}__image" data-editor-block-type="image" data-editor-field-key="days.${dayIndex}.image" data-editor-field-label="Day image"`;
  if (!picturesAdded() || day.image?.pictures_pending) {
    return `<div class="image-stage text-mode" aria-hidden="true"${blockAttrs}></div>`;
  }
  const img = day.image || {};
  const options = img.options || [];
  const optionHtml = options.map((opt, idx) => `<option value="${esc(opt.path)}" data-option-index="${idx}" title="${esc(opt.reason || '')}" ${opt.path === img.path ? 'selected' : ''}>${esc(opt.name)}</option>`).join('');
  const hasImage = !!img.data_uri;
  const warnings = Array.isArray(img.warnings) ? img.warnings : [];
  const warningHtml = warnings.length ? `<div class="image-warning-badge">Needs review: ${esc(warnings[0].message || warnings[0].code || 'picture warning')}</div>` : '';
  const src = hasImage ? `<img src="${esc(img.data_uri)}" style="object-position:${focusPos(img.crop_focus)}" alt="${esc(img.name || '')}">` : `<span>${img.pending_preview ? 'Replacement selected — save to update preview' : 'No picture selected'}</span>`;
  return `<div class="image-stage ${hasImage ? '' : 'empty'}" data-day-index="${dayIndex}"${blockAttrs}>
      ${src}${warningHtml}
      <div class="image-actions">
        <button type="button" data-img-action="auto" data-day-index="${dayIndex}">Automatic</button>
        <button type="button" class="danger" data-img-action="none" data-day-index="${dayIndex}">Remove</button>
        <select data-img-focus="${dayIndex}">
          <option value="top" ${img.crop_focus === 'top' ? 'selected' : ''}>Sky / upper crop</option>
          <option value="center" ${img.crop_focus === 'center' ? 'selected' : ''}>Center crop</option>
          <option value="bottom" ${img.crop_focus === 'bottom' ? 'selected' : ''}>Lower crop</option>
        </select>
        <select data-img-bank="${dayIndex}"><option value="">Choose replacement…</option>${optionHtml}</select>
        <button type="button" data-img-action="manual" data-day-index="${dayIndex}">Use selected</button>
        <label class="upload-label">Upload<input type="file" accept="image/png,image/jpeg,image/webp" data-img-upload="${dayIndex}"></label>
      </div>
    </div>`;
}

function adjustDayImages() {
  const pageHeight = 1123;
  const minImageHeight = 185;
  document.querySelectorAll('.day-page').forEach(page => {
    const content = page.querySelector('.page-content');
    const stage = page.querySelector('.image-stage');
    if (!content || !stage || stage.classList.contains('empty')) return;
    const contentBottom = content.offsetTop + content.scrollHeight;
    const imageTop = Math.max(contentBottom + 20, (pageHeight / 2) + 20);
    const imageHeight = pageHeight - imageTop;
    if (imageHeight < minImageHeight) {
      stage.classList.add('skipped');
      return;
    }
    stage.classList.remove('skipped');
    stage.style.top = `${imageTop}px`;
    stage.style.height = `${imageHeight}px`;
  });
}
