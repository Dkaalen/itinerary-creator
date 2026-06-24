/** Clean editor shell helpers split from render.js. */
function editorShellOpenHtml() {
  return `<div class="editor-shell">`;
}
function editorWorkspaceOpenHtml() {
  return `<div class="editor-workspace"><div class="page-stack">`;
}
function editorWorkspaceCloseHtml() {
  return `</div>${renderRightInspector()}</div><div class="help-strip">The PDF preview/export remains the final rendering check after saving your edits.</div></div>`;
}
