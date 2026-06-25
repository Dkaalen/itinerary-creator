/** Clean editor shell helpers split from render.js. */
function editorShellOpenHtml(brand = {}) {
  const outputBrand = String(brand?.output_brand || 'agent');
  const colors = brand?.colors || {};
  const style = outputBrand === 'booknordics_customer'
    ? [
        `--paper:${escAttr(colors.page_bg || '#FAFAFB')}`,
        `--ink:${escAttr(colors.ink || '#00193C')}`,
        `--body:${escAttr(colors.body || '#202738')}`,
        `--muted:${escAttr(colors.muted || '#667085')}`,
        `--accent:${escAttr(colors.accent || '#FF0041')}`,
        `--border:${escAttr(colors.line || '#D7DDE5')}`,
        '--focus:#FF0041',
        brand.logo_data_uri ? `--brand-logo:url('${escAttr(brand.logo_data_uri)}')` : ''
      ].filter(Boolean).join(';')
    : '';
  const fontStyle = outputBrand === 'booknordics_customer' && brand.font_face_css
    ? `<style data-editor-brand-fonts>${brand.font_face_css}</style>`
    : '';
  return `${fontStyle}<div class="editor-shell" data-output-brand="${escAttr(outputBrand)}"${style ? ` style="${style}"` : ''}>`;
}
function editorWorkspaceOpenHtml() {
  return `<div class="editor-workspace"><div class="page-stack">`;
}
function editorWorkspaceCloseHtml() {
  return `</div>${renderRightInspector()}</div><div class="help-strip">The PDF preview/export remains the final rendering check after saving your edits.</div></div>`;
}
