/** Responsibility split from state.js. */
function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]));
}

function escAttr(s) {
  return esc(s).replace(/'/g, '&#39;');
}
