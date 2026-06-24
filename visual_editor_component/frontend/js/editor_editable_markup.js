/** Responsibility split from state.js. */
function editableText(value, key, cls='', label='') {
  return `<div class="${cls} editable-inline" contenteditable="true" data-edit-key="${esc(key)}" data-empty-label="${escAttr(label || 'Edit text')}"${editorBlockAttrs(key, label)}>${esc(value)}</div>`;
}

function editableSpan(value, key, cls='', label='') {
  return `<span class="${cls} editable-inline" contenteditable="true" data-edit-key="${esc(key)}" data-empty-label="${escAttr(label || 'Edit text')}"${editorBlockAttrs(key, label)}>${esc(value)}</span>`;
}

function editableHtml(value, key, cls='', label='') {
  return `<div class="${cls}" contenteditable="true" data-edit-key="${esc(key)}" data-empty-label="${escAttr(label || 'Edit text')}"${editorBlockAttrs(key, label)}>${value || ''}</div>`;
}

function splitRouteParts(value) {
  return String(value || '').replace(/\s*\n+\s*/g, ' · ').split('·').map(p => p.trim()).filter(Boolean);
}

function routeHtml(value) {
  const parts = splitRouteParts(value);
  if (parts.length < 5) return esc(parts.join(' · '));
  const first = parts.slice(0, -2).map(esc).join(' · ');
  const pair = `<span class="cover-destination-pair">${esc(parts[parts.length - 2])}&nbsp;·&nbsp;${esc(parts[parts.length - 1])}</span>`;
  return `<span class="cover-route-line">${first}</span><span class="cover-route-line">${pair}</span>`;
}

function editableRoute(value, key, cls='', label='Route') {
  return `<div class="${cls} editable-inline" contenteditable="true" data-edit-key="${esc(key)}" data-empty-label="${escAttr(label || 'Edit text')}"${editorBlockAttrs(key, label)}>${routeHtml(value)}</div>`;
}
