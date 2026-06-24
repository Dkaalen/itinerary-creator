/** Responsibility split from editor_text_tools.js. */
function plainTextToCleanPasteHtml(text) {
  const lines = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const chunks = [];
  let list = [];
  function flushList() {
    if (list.length) {
      chunks.push('<ul>' + list.map(item => `<li>${esc(item)}</li>`).join('') + '</ul>');
      list = [];
    }
  }
  lines.forEach(raw => {
    const line = raw.trim();
    if (!line) { flushList(); return; }
    const bullet = line.match(/^(?:[•\-*]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      list.push(bullet[1].trim());
    } else {
      flushList();
      chunks.push(`<div>${esc(line)}</div>`);
    }
  });
  flushList();
  return chunks.join('') || esc(text || '');
}

function sanitizeClipboardHtml(html, fallbackText) {
  if (!html || !String(html).trim()) return plainTextToCleanPasteHtml(fallbackText || '');
  const box = document.createElement('div');
  box.innerHTML = html;
  const allowedTags = new Set(['DIV','P','BR','UL','OL','LI','STRONG','B','EM','I','SPAN']);
  const allowedClasses = new Set([
    'section-title','row-type','strong-line','body-text','detail-list','final-list','inclusion-entry',
    'inclusion-entry-title','inclusion-entry-detail','inclusion-entry-spacer','meta-line','meta-label',
    'small-section','content-block','muted-note','inclusion-category-block','inclusion-category-list',
    'inclusion-multiline-list',
    ...controlledEditorAllowedClasses(),
  ]);
  box.querySelectorAll('*').forEach(node => {
    const tag = node.tagName;
    if (!allowedTags.has(tag)) {
      const parent = node.parentNode;
      while (node.firstChild) parent.insertBefore(node.firstChild, node);
      parent.removeChild(node);
      return;
    }
    const classes = node.classList ? Array.from(node.classList).filter(cls => allowedClasses.has(cls)) : [];
    Array.from(node.attributes).forEach(attr => node.removeAttribute(attr.name));
    if (classes.length) node.setAttribute('class', classes.join(' '));
  });
  const cleaned = box.innerHTML.trim();
  return cleaned || plainTextToCleanPasteHtml(fallbackText || '');
}

function insertCleanClipboardHtml(event) {
  event.preventDefault();
  const data = event.clipboardData || window.clipboardData;
  const html = sanitizeClipboardHtml(data?.getData('text/html') || '', data?.getData('text/plain') || '');
  document.execCommand('insertHTML', false, html);
}
