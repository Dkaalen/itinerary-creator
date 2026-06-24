// Canvas-first image toolbar helpers.
// Keep image editing controls colocated with the page/image surface rather than the sidebar.

function coverImageControls(key, label, image) {
  if (!picturesAdded()) return '';
  const img = image || {};
  const imagePageId = key === 'summary_image' ? 'summary' : 'cover';
  const fieldKey = `cover.${key}`;
  const imageBlockAttrs = ` data-editor-page-id="${escAttr(imagePageId)}" data-editor-block-id="${escAttr(imagePageId)}__${escAttr(editorSlug(key))}" data-editor-block-type="image" data-editor-field-key="${escAttr(fieldKey)}" data-editor-field-label="${escAttr(label)}"`;
  const options = typeof imageToolbarOptionsHtml === 'function' ? imageToolbarOptionsHtml(img) : '';
  const hasOptions = !!options;
  const focusOptions = typeof imageFocusOptionsHtml === 'function' ? imageFocusOptionsHtml(img.crop_focus) : '';
  const pending = img.pending_preview ? '<span class="image-pending-chip">Unsaved image</span>' : '';
  return `<div class="cover-image-panel canvas-image-tools" data-cover-image-key="${esc(key)}"${imageBlockAttrs}>
    <strong>${esc(label)}</strong>
    <span class="image-crop-chip">${esc(imageFocusLabel(img.crop_focus))}</span>
    ${pending}
    <select data-cover-img-focus="${escAttr(key)}" aria-label="${escAttr(label)} crop position">${focusOptions}</select>
    <select data-cover-img-bank="${escAttr(key)}" ${hasOptions ? '' : 'disabled'} aria-label="${escAttr(label)} replacement image"><option value="">Choose image…</option>${options}</select>
    <button type="button" class="ghost" data-cover-img-key="${escAttr(key)}" data-cover-img-action="auto">Automatic</button>
    <button type="button" class="ghost" data-cover-img-key="${escAttr(key)}" data-cover-img-action="manual" ${hasOptions ? '' : 'disabled'}>Use selected</button>
    <button type="button" class="danger" data-cover-img-key="${escAttr(key)}" data-cover-img-action="none">Remove</button>
    <button type="button" class="ghost compact-details" data-select-image-field="${escAttr(fieldKey)}">Details</button>
  </div>`;
}
