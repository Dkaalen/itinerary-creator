function attachImageDetailsHandler(root = document) {
  root.querySelectorAll('[data-select-image-field]').forEach(btn => {
    btn.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      selectEditorFieldByKey(btn.getAttribute('data-select-image-field') || '');
    });
  });
}

function cssEscapeValue(value) {
  return typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(String(value || '')) : String(value || '').replace(/"/g, '\\"');
}

function refreshImageNodeHandlers(node) {
  if (!node) return;
  attachImageEventHandlers(node);
  attachImageDetailsHandler(node);
}

function replaceDayImageStage(dayIndex) {
  const idx = Number(dayIndex);
  const day = model?.days?.[idx];
  if (!day || typeof imageHtml !== 'function') return false;
  const oldStage = document.querySelector(`.image-stage[data-day-index="${idx}"]`);
  if (!oldStage) return false;
  const wrapper = document.createElement('div');
  wrapper.innerHTML = imageHtml(day, idx).trim();
  const nextStage = wrapper.firstElementChild;
  if (!nextStage) return false;
  oldStage.replaceWith(nextStage);
  refreshImageNodeHandlers(nextStage);
  requestAnimationFrame(() => { adjustDayImages(); updateEditorStats(); syncEditorFrameHeight(); });
  return true;
}

function coverImageBackgroundData(key) {
  const image = model?.cover?.[key] || {};
  const fallback = key === 'summary_image' ? model?.cover?.cover_background_data_uri : '';
  return image.data_uri || fallback || '';
}

function updateCoverPageBackground(key) {
  const focus = model?.cover?.[key]?.crop_focus || 'top';
  const dataUri = coverImageBackgroundData(key);
  if (key === 'summary_image') {
    const summaryPageEl = document.querySelector('.summary-page');
    if (!summaryPageEl) return;
    const isBooknordics = model?.brand?.output_brand === 'booknordics_customer';
    const overlay = isBooknordics ? 'rgba(250,250,251,.58)' : 'rgba(244,239,232,.40)';
    summaryPageEl.style.backgroundImage = dataUri ? `linear-gradient(${overlay}, ${overlay}), url('${escAttr(dataUri)}')` : '';
    summaryPageEl.style.backgroundPosition = dataUri ? `center center, ${focusPos(focus)}` : '';
    summaryPageEl.style.backgroundSize = dataUri ? 'cover, cover' : '';
    summaryPageEl.style.backgroundRepeat = dataUri ? 'no-repeat, no-repeat' : '';
    return;
  }
  const coverPage = document.querySelector('.cover-page');
  if (!coverPage) return;
  coverPage.style.backgroundImage = dataUri ? `url('${escAttr(dataUri)}')` : '';
  coverPage.style.backgroundPosition = dataUri ? focusPos(focus) : '';
  coverPage.style.backgroundSize = dataUri ? 'cover' : '';
  coverPage.style.backgroundRepeat = dataUri ? 'no-repeat' : '';
}

function replaceCoverImagePanel(key) {
  const image = model?.cover?.[key] || {};
  const oldPanel = document.querySelector(`.cover-image-panel[data-cover-image-key="${cssEscapeValue(key)}"]`);
  if (!oldPanel || typeof coverImageControls !== 'function') return false;
  const label = key === 'summary_image' ? 'Page 2 background image' : 'Front cover image';
  const wrapper = document.createElement('div');
  wrapper.innerHTML = coverImageControls(key, label, image).trim();
  const nextPanel = wrapper.firstElementChild;
  if (!nextPanel) return false;
  oldPanel.replaceWith(nextPanel);
  refreshImageNodeHandlers(nextPanel);
  updateCoverPageBackground(key);
  requestAnimationFrame(() => { updateEditorStats(); syncEditorFrameHeight(); });
  return true;
}

function refreshImageEditSurface(scope, keyOrIndex) {
  captureEditorScrollState(scope === 'cover' ? `cover-image-${keyOrIndex}` : `day-image-${keyOrIndex}`);
  const refreshed = scope === 'cover' ? replaceCoverImagePanel(keyOrIndex) : replaceDayImageStage(keyOrIndex);
  if (!refreshed) draw();
}

function selectedOptionForSelect(options, selectElement) {
  if (!selectElement || !selectElement.value) return null;
  return (options || []).find(opt => opt.path === selectElement.value) || null;
}

function dataUriForSelectedOption(selected) {
  if (!selected) return '';
  return selected.preview_data_uri || selected.data_uri || '';
}

function compressUploadedImage(file, callback) {
  const reader = new FileReader();
  reader.onload = () => {
    const originalDataUri = String(reader.result || '');
    if (!/^image\//i.test(file.type || '')) {
      callback(originalDataUri);
      return;
    }
    const img = new Image();
    img.onload = () => {
      try {
        const maxSide = 1800;
        const scale = Math.min(1, maxSide / Math.max(img.naturalWidth || img.width || 1, img.naturalHeight || img.height || 1));
        const width = Math.max(1, Math.round((img.naturalWidth || img.width || 1) * scale));
        const height = Math.max(1, Math.round((img.naturalHeight || img.height || 1) * scale));
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          callback(originalDataUri);
          return;
        }
        ctx.drawImage(img, 0, 0, width, height);
        const mime = /png/i.test(file.type || '') ? 'image/png' : 'image/jpeg';
        callback(canvas.toDataURL(mime, mime === 'image/jpeg' ? 0.82 : undefined));
      } catch (err) {
        callback(originalDataUri);
      }
    };
    img.onerror = () => callback(originalDataUri);
    img.src = originalDataUri;
  };
  reader.onerror = () => callback('');
  reader.readAsDataURL(file);
}

function touchImageField(key) {
  // Image edits must stay local and non-blocking.  Sending a Streamlit
  // component value here mutes the parent page and interrupts picture review.
  // Manual Save / Apply Changes / PDF export are the server-sync boundaries.
  markTouched(key, {serverAutosave: false});
}

function attachImageEventHandlers(root = document) {
  root.querySelectorAll('[data-cover-img-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-cover-img-key');
      const action = btn.getAttribute('data-cover-img-action');
      if (!model.cover) model.cover = {};
      const image = model.cover[key] || (model.cover[key] = {mode: 'auto', path: '', crop_focus: 'top', options: []});
      if (action === 'auto') {
        image.mode = 'auto';
        image.path = '';
        image.data_uri = image.auto_data_uri || image.data_uri || '';
        image.name = image.auto_name || image.name || '';
        image.pending_preview = false;
        image.pending_save = true;
      }
      if (action === 'none') {
        image.mode = 'none';
        image.path = '';
        image.data_uri = '';
        image.name = '';
        image.pending_preview = false;
        image.pending_save = true;
      }
      activeFieldKey = `cover.${key}`;
      activePageId = key === 'summary_image' ? 'summary' : 'cover';
      if (action === 'manual') {
        const sel = document.querySelector(`[data-cover-img-bank="${cssEscapeValue(key)}"]`);
        const selected = selectedOptionForSelect(image.options, sel);
        if (selected) {
          const previewDataUri = dataUriForSelectedOption(selected);
          image.mode = 'manual';
          image.path = selected.path || sel.value;
          image.data_uri = previewDataUri;
          image.name = selected.name || sel.options[sel.selectedIndex]?.text || '';
          image.pending_preview = !previewDataUri;
          image.pending_save = true;
        }
      }
      touchImageField(`cover.${key}`);
      refreshImageEditSurface('cover', key);
    });
  });
  root.querySelectorAll('[data-cover-img-focus]').forEach(sel => {
    sel.addEventListener('change', () => {
      const key = sel.getAttribute('data-cover-img-focus');
      if (!model.cover) model.cover = {};
      const image = model.cover[key] || (model.cover[key] = {mode: 'auto', path: '', crop_focus: 'top', options: []});
      image.crop_focus = sel.value;
      image.pending_save = true;
      activeFieldKey = `cover.${key}`;
      activePageId = key === 'summary_image' ? 'summary' : 'cover';
      touchImageField(`cover.${key}`);
      updateCoverPageBackground(key);
      const chip = sel.closest('.cover-image-panel')?.querySelector('.image-crop-chip');
      if (chip) chip.textContent = imageFocusLabel(sel.value);
    });
  });
  root.querySelectorAll('[data-img-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.getAttribute('data-day-index'));
      const action = btn.getAttribute('data-img-action');
      const day = model.days[idx];
      if (!day || !day.image) return;
      if (action === 'auto') {
        day.image.mode = 'auto';
        day.image.path = '';
        day.image.data_uri = day.image.auto_data_uri || day.image.data_uri || '';
        day.image.name = day.image.auto_name || day.image.name || '';
        day.image.pending_preview = false;
        day.image.pending_save = true;
      }
      if (action === 'none') {
        day.image.mode = 'none';
        day.image.path = '';
        day.image.data_uri = '';
        day.image.name = '';
        day.image.pending_preview = false;
        day.image.pending_save = true;
      }
      activeFieldKey = `days.${idx}.image`;
      activePageId = typeof pageIdForDay === 'function' ? pageIdForDay(day, idx) : activePageId;
      if (action === 'manual') {
        const sel = document.querySelector(`[data-img-bank="${idx}"]`);
        const selected = selectedOptionForSelect(day.image.options, sel);
        if (selected) {
          const previewDataUri = dataUriForSelectedOption(selected);
          day.image.mode = 'manual';
          day.image.path = selected.path || sel.value;
          day.image.data_uri = previewDataUri;
          day.image.name = selected.name || sel.options[sel.selectedIndex]?.text || '';
          day.image.pending_preview = !previewDataUri;
          day.image.pending_save = true;
        }
      }
      touchImageField(`days.${idx}.image`);
      refreshImageEditSurface('day', idx);
    });
  });
  root.querySelectorAll('[data-img-focus]').forEach(sel => {
    sel.addEventListener('change', () => {
      const idx = Number(sel.getAttribute('data-img-focus'));
      if (model.days[idx] && model.days[idx].image) {
        model.days[idx].image.crop_focus = sel.value;
        model.days[idx].image.pending_save = true;
      }
      activeFieldKey = `days.${idx}.image`;
      activePageId = typeof pageIdForDay === 'function' ? pageIdForDay(model.days[idx] || {}, idx) : activePageId;
      touchImageField(`days.${idx}.image`);
      const img = sel.closest('.image-stage')?.querySelector('img');
      if (img) img.style.objectPosition = focusPos(sel.value);
      const chip = sel.closest('.image-stage')?.querySelector('.image-crop-chip');
      if (chip) chip.textContent = imageFocusLabel(sel.value);
    });
  });
  root.querySelectorAll('[data-img-upload]').forEach(input => {
    input.addEventListener('change', () => {
      const idx = Number(input.getAttribute('data-img-upload'));
      const file = input.files && input.files[0];
      if (!file) return;
      compressUploadedImage(file, dataUri => {
        if (!dataUri) return;
        uploadedImages[idx] = {filename: file.name, data_uri: dataUri, season: 'Summer', label: file.name.replace(/\.[^.]+$/, '')};
        activeFieldKey = `days.${idx}.image`;
        activePageId = typeof pageIdForDay === 'function' ? pageIdForDay(model.days[idx] || {}, idx) : activePageId;
        if (model.days[idx] && model.days[idx].image) {
          model.days[idx].image.mode = 'manual';
          model.days[idx].image.path = '';
          model.days[idx].image.data_uri = dataUri;
          model.days[idx].image.name = file.name;
          model.days[idx].image.pending_preview = false;
          model.days[idx].image.pending_save = true;
        }
        touchImageField(`days.${idx}.image`);
        refreshImageEditSurface('day', idx);
      });
    });
  });
}
