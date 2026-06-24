function imageToolbarOptionsHtml(image) {
  const options = Array.isArray(image?.options) ? image.options : [];
  return options.map((opt, idx) => `<option value="${escAttr(opt.path || '')}" title="${escAttr(opt.reason || '')}" ${opt.path === image?.path ? 'selected' : ''}>${esc(opt.name || opt.path || `Option ${idx + 1}`)}</option>`).join('');
}

function imageFocusOptionsHtml(focus) {
  const selected = String(focus || 'top');
  return `<option value="top" ${selected === 'top' ? 'selected' : ''}>Upper crop</option><option value="center" ${selected === 'center' ? 'selected' : ''}>Center crop</option><option value="bottom" ${selected === 'bottom' ? 'selected' : ''}>Lower crop</option>`;
}

function dayImageToolbarHtml(image, dayIndex) {
  const options = imageToolbarOptionsHtml(image);
  const hasOptions = !!options;
  const pending = image?.pending_preview ? '<span class="image-pending-chip">Save to refresh</span>' : '';
  return `<div class="image-actions canvas-image-tools" aria-label="Image editing toolbar">
    <span class="image-crop-chip">${esc(imageFocusLabel(image?.crop_focus))}</span>
    ${pending}
    <select data-img-focus="${dayIndex}" aria-label="Image crop position">${imageFocusOptionsHtml(image?.crop_focus)}</select>
    <select data-img-bank="${dayIndex}" ${hasOptions ? '' : 'disabled'} aria-label="Replacement image"><option value="">Choose image…</option>${options}</select>
    <button type="button" class="ghost" data-day-index="${dayIndex}" data-img-action="auto">Automatic</button>
    <button type="button" class="ghost" data-day-index="${dayIndex}" data-img-action="manual" ${hasOptions ? '' : 'disabled'}>Use selected</button>
    <label class="upload-label">Upload<input type="file" accept="image/png,image/jpeg,image/webp" data-img-upload="${dayIndex}"></label>
    <button type="button" class="danger" data-day-index="${dayIndex}" data-img-action="none">Remove</button>
    <button type="button" class="ghost compact-details" data-select-image-field="days.${dayIndex}.image">Details</button>
  </div>`;
}

function imageHtml(day, dayIndex) {
  const pageId = typeof pageIdForDay === 'function' ? pageIdForDay(day || {}, dayIndex) : `day-${editorSlug(day?.day || day?.label || `Day ${dayIndex + 1}`)}`;
  const blockAttrs = ` data-editor-page-id="${escAttr(pageId)}" data-editor-block-id="${escAttr(pageId)}__image" data-editor-block-type="image" data-editor-field-key="days.${dayIndex}.image" data-editor-field-label="Day image"`;
  if (!picturesAdded() || day.image?.pictures_pending) {
    return `<div class="image-stage text-mode" aria-hidden="true"${blockAttrs}></div>`;
  }
  const img = day.image || {};
  const hasImage = !!img.data_uri;
  const warnings = Array.isArray(img.warnings) ? img.warnings : [];
  const warningHtml = warnings.length ? `<div class="image-warning-badge">Review: ${esc(warnings[0].message || warnings[0].code || 'picture warning')}</div>` : '';
  const src = hasImage ? `<img src="${esc(img.data_uri)}" style="object-position:${focusPos(img.crop_focus)}" alt="${esc(img.name || '')}">` : `<span>${img.pending_preview ? 'Replacement selected — save to update preview' : 'No picture selected'}</span>`;
  return `<div class="image-stage ${hasImage ? '' : 'empty'}" data-day-index="${dayIndex}"${blockAttrs}>
      ${src}${warningHtml}
      ${dayImageToolbarHtml(img, dayIndex)}
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
