function attachImageEventHandlers() {
  document.querySelectorAll('[data-cover-img-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      collect();
      const key = btn.getAttribute('data-cover-img-key');
      const action = btn.getAttribute('data-cover-img-action');
      if (!model.cover) model.cover = {};
      const image = model.cover[key] || (model.cover[key] = {mode: 'auto', path: '', crop_focus: 'top', options: []});
      markTouched(`cover.${key}`);
      if (action === 'auto') {
        image.mode = 'auto';
        image.path = '';
        image.data_uri = image.auto_data_uri || image.data_uri || '';
        image.name = image.auto_name || image.name || '';
      }
      if (action === 'none') {
        image.mode = 'none';
        image.path = '';
        image.data_uri = '';
        image.name = '';
      }
      activeFieldKey = `cover.${key}`;
      activePageId = key === 'summary_image' ? 'summary' : 'cover';
      if (action === 'manual') {
        const sel = document.querySelector(`[data-cover-img-bank="${CSS.escape(key)}"]`);
        if (sel && sel.value) {
          const selected = (image.options || []).find(opt => opt.path === sel.value) || {};
          const previewDataUri = selected.preview_data_uri || selected.data_uri || '';
          image.mode = 'manual';
          image.path = sel.value;
          image.data_uri = previewDataUri;
          image.name = selected.name || sel.options[sel.selectedIndex]?.text || '';
          image.pending_preview = !previewDataUri;
          image.pending_save = true;
        }
      }
      captureEditorScrollState(`cover-image-${action}`);
      draw();
    });
  });
  document.querySelectorAll('[data-cover-img-focus]').forEach(sel => {
    sel.addEventListener('change', () => {
      const key = sel.getAttribute('data-cover-img-focus');
      if (!model.cover) model.cover = {};
      const image = model.cover[key] || (model.cover[key] = {mode: 'auto', path: '', crop_focus: 'top', options: []});
      image.crop_focus = sel.value;
      markTouched(`cover.${key}`);
      const page = sel.closest('.a4-page');
      if (page) page.style.backgroundPosition = key === 'summary_image' ? `center center, ${focusPos(sel.value)}` : focusPos(sel.value);
      const chip = sel.closest('.cover-image-panel')?.querySelector('.image-crop-chip');
      if (chip) chip.textContent = imageFocusLabel(sel.value);
    });
  });
  document.querySelectorAll('[data-img-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      collect();
      const idx = Number(btn.getAttribute('data-day-index'));
      const action = btn.getAttribute('data-img-action');
      const day = model.days[idx];
      if (!day || !day.image) return;
      markTouched(`days.${idx}.image`);
      if (action === 'auto') {
        day.image.mode = 'auto';
        day.image.path = '';
        day.image.data_uri = day.image.auto_data_uri || day.image.data_uri || '';
        day.image.name = day.image.auto_name || day.image.name || '';
      }
      if (action === 'none') {
        day.image.mode = 'none';
        day.image.path = '';
        day.image.data_uri = '';
        day.image.name = '';
      }
      activeFieldKey = `days.${idx}.image`;
      activePageId = typeof pageIdForDay === 'function' ? pageIdForDay(day, idx) : activePageId;
      if (action === 'manual') {
        const sel = document.querySelector(`[data-img-bank="${idx}"]`);
        if (sel && sel.value) {
          const selected = (day.image.options || []).find(opt => opt.path === sel.value) || {};
          const previewDataUri = selected.preview_data_uri || selected.data_uri || '';
          day.image.mode = 'manual';
          day.image.path = sel.value;
          day.image.data_uri = previewDataUri;
          day.image.name = selected.name || sel.options[sel.selectedIndex]?.text || '';
          day.image.pending_preview = !previewDataUri;
          day.image.pending_save = true;
        }
      }
      captureEditorScrollState(`day-image-${idx}-${action}`);
      draw();
      
    });
  });
  document.querySelectorAll('[data-img-focus]').forEach(sel => {
    sel.addEventListener('change', () => {
      const idx = Number(sel.getAttribute('data-img-focus'));
      if (model.days[idx] && model.days[idx].image) model.days[idx].image.crop_focus = sel.value;
      markTouched(`days.${idx}.image`);
      
      const img = sel.closest('.image-stage')?.querySelector('img');
      if (img) img.style.objectPosition = focusPos(sel.value);
      const chip = sel.closest('.image-stage')?.querySelector('.image-crop-chip');
      if (chip) chip.textContent = imageFocusLabel(sel.value);
    });
  });
  document.querySelectorAll('[data-img-upload]').forEach(input => {
    input.addEventListener('change', () => {
      const idx = Number(input.getAttribute('data-img-upload'));
      const file = input.files && input.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        uploadedImages[idx] = {filename: file.name, data_uri: reader.result, season: 'Summer', label: file.name.replace(/\.[^.]+$/, '')};
        activeFieldKey = `days.${idx}.image`;
        markTouched(`days.${idx}.image`);
        if (model.days[idx] && model.days[idx].image) {
          model.days[idx].image.mode = 'manual';
          model.days[idx].image.path = '';
          model.days[idx].image.data_uri = reader.result;
        }
        const stage = input.closest('.image-stage');
        if (stage) {
          stage.classList.remove('empty');
          const existing = stage.querySelector('img');
          if (existing) existing.src = reader.result;
          else stage.insertAdjacentHTML('afterbegin', `<img src="${reader.result}" style="object-position:${focusPos(model.days[idx].image.crop_focus)}" alt="Uploaded picture">`);
          requestAnimationFrame(adjustDayImages);
        }
        
      };
      reader.readAsDataURL(file);
    });
  });
}
