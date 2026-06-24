/** Responsibility split from state.js. */
function focusPos(focus) {
  if (focus === 'bottom') return 'center 78%';
  if (focus === 'center') return 'center center';
  return 'center 22%';
}

function imageFocusLabel(focus) {
  if (focus === 'bottom') return 'Lower crop';
  if (focus === 'center') return 'Center crop';
  return 'Upper crop';
}

function picturesAdded() {
  return !!model?.workflow?.pictures_added;
}
